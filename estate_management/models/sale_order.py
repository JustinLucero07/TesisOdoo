# -*- coding: utf-8 -*-
from odoo import models, fields, api
from markupsafe import Markup


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    property_id = fields.Many2one('estate.property', string='Propiedad Vinculada')
    estate_transaction_type = fields.Selection([
        ('sale', 'Venta'),
    ], string='Tipo de Contrato Inmobiliario', default='sale')
    property_sold_by = fields.Selection(
        related='property_id.sold_by', string='Cerrado por',
        store=True, index=True,
        help='Quién cerró la venta de la propiedad vinculada: la agencia, el '
             'propietario o un externo. Se toma de la propiedad para poder '
             'filtrar las cotizaciones por ese criterio.')
    # --- Resumen de la venta (mismas columnas que la hoja de Excel de ventas) ---
    estate_buyer_id = fields.Many2one(
        related='property_id.buyer_id', string='Comprador', store=True, index=True)
    estate_date_sold = fields.Date(
        related='property_id.date_sold', string='Fecha de venta', store=True)
    estate_sale_price = fields.Float(
        related='property_id.price', string='Valor de venta', store=True)
    estate_buyer_phone = fields.Char(
        string='Tel. comprador', compute='_compute_estate_phones')
    estate_buyer_phone2 = fields.Char(
        string='Tel. comprador 2', compute='_compute_estate_phones')
    estate_owner_phone = fields.Char(
        string='Tel. propietario', compute='_compute_estate_phones')
    estate_owner_phone2 = fields.Char(
        string='Tel. propietario 2', compute='_compute_estate_phones')
    estate_source = fields.Char(
        string='Difusión', compute='_compute_estate_source', store=True,
        help='Canal por el que llegó el cliente (fuente del lead).')
    estate_advisor_roles = fields.Char(
        string='Asesores', compute='_compute_estate_advisor_roles',
        help='Iniciales de los asesores que comisionaron por cada paso: '
             'Capt. (captación), Rec. (recepción), Vis. (visita), Cie. (cierre).')
    lead_id = fields.Many2one('crm.lead', string='Lead de Origen', tracking=True,
                              help='Lead CRM que originó esta orden de venta.')
    customer_signature = fields.Binary(
        string='Firma del Cliente', copy=False, attachment=True,
        help='Firma digital del cliente para aprobar la orden.')
    signature_date = fields.Datetime(
        string='Fecha de Firma', readonly=True, copy=False)

    @staticmethod
    def _estate_partner_phones(partner):
        phones = []
        if partner:
            candidates = [partner.phone, partner.mobile] + partner.extra_phone_ids.mapped('phone')
            for phone in candidates:
                if phone and phone not in phones:
                    phones.append(phone)
        return phones + [False, False]

    @api.depends('partner_id.phone', 'partner_id.mobile', 'partner_id.extra_phone_ids.phone',
                 'estate_buyer_id.phone', 'estate_buyer_id.mobile',
                 'estate_buyer_id.extra_phone_ids.phone')
    def _compute_estate_phones(self):
        for order in self:
            buyer = self._estate_partner_phones(order.estate_buyer_id)
            owner = self._estate_partner_phones(order.partner_id)
            order.estate_buyer_phone, order.estate_buyer_phone2 = buyer[0], buyer[1]
            order.estate_owner_phone, order.estate_owner_phone2 = owner[0], owner[1]

    @api.depends('property_id.deal_lead_origin')
    def _compute_estate_source(self):
        # estate_crm lo amplía para usar la fuente del lead de origen.
        for order in self:
            order.estate_source = order.property_id.deal_lead_origin or False

    _ESTATE_ROLE_SHORT = {'capture': 'Capt.', 'reception': 'Rec.', 'visit': 'Vis.',
                          'closing': 'Cie.', 'all': 'Todo', 'other': 'Otro'}

    @staticmethod
    def _estate_initials(name):
        return ''.join(word[0] for word in (name or '').split()[:2]).upper()

    def _compute_estate_advisor_roles(self):
        properties = self.property_id
        commissions = self.env['estate.commission'].sudo().search([
            ('property_id', 'in', properties.ids),
            ('state', '!=', 'cancelled'),
            ('child_commission_ids', '=', False),
        ]) if properties else self.env['estate.commission']
        for order in self:
            lines = commissions.filtered(
                lambda c: c.property_id == order.property_id
            ).sorted(lambda c: (c.role_sequence, c.id))
            parts = []
            for c in lines:
                initials = self._estate_initials(c.user_id.name)
                part = f"{self._ESTATE_ROLE_SHORT[c.role]} {initials}" if c.role else initials
                if part not in parts:
                    parts.append(part)
            order.estate_advisor_roles = ' · '.join(parts) or False

    @api.onchange('customer_signature')
    def _onchange_customer_signature(self):
        if self.customer_signature and not self.signature_date:
            self.signature_date = fields.Datetime.now()

    @api.onchange('partner_id', 'property_id')
    def _onchange_find_lead_id(self):
        """Si ya se conoce cliente y/o propiedad, busca el lead del CRM que
        originó esta operación en vez de dejarlo vacío para llenar a mano."""
        for order in self:
            if order.lead_id or not order.property_id:
                continue
            domain = [('target_property_id', '=', order.property_id.id), ('type', '=', 'opportunity')]
            if order.partner_id:
                domain.append(('partner_id', '=', order.partner_id.id))
            lead = self.env['crm.lead'].search(domain, limit=1)
            if lead:
                order.lead_id = lead

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('lead_id') and not vals.get('opportunity_id'):
                vals['opportunity_id'] = vals['lead_id']
            elif vals.get('opportunity_id') and not vals.get('lead_id'):
                vals['lead_id'] = vals['opportunity_id']
        return super().create(vals_list)

    def write(self, vals):
        if 'lead_id' in vals and 'opportunity_id' not in vals:
            vals['opportunity_id'] = vals['lead_id']
        elif 'opportunity_id' in vals and 'lead_id' not in vals:
            vals['lead_id'] = vals['opportunity_id']
        return super().write(vals)

    def action_confirm(self):
        result = super().action_confirm()
        for order in self:
            if order.property_id:
                # Notificar en el chatter de la propiedad
                order.property_id.message_post(
                    body=Markup(f'Orden de venta <b>{order.name}</b> CONFIRMADA para '
                                f'<b>{order.partner_id.name}</b> por ${order.amount_total:,.2f}.'))
            if order.lead_id:
                # Notificar en el chatter del lead CRM
                order.lead_id.message_post(
                    body=Markup(f'Orden de venta <b>{order.name}</b> confirmada para la propiedad '
                                f'<b>{order.property_id.title if order.property_id else "N/A"}</b> '
                                f'por ${order.amount_total:,.2f}.'))
            # Enviar email de confirmación al cliente si tiene correo
            if order.partner_id and order.partner_id.email:
                order.message_post(
                    body=Markup(f'<p>Estimado/a <strong>{order.partner_id.name}</strong>,</p>'
                                f'<p>Su orden de venta <strong>{order.name}</strong> ha sido confirmada.</p>'
                                f'<p><strong>Propiedad:</strong> {order.property_id.title if order.property_id else "N/A"}<br/>'
                                f'<strong>Monto total:</strong> ${order.amount_total:,.2f}</p>'
                                f'<p>Nuestro equipo le contactará para coordinar los siguientes pasos.</p>'),
                    partner_ids=[order.partner_id.id],
                    subtype_xmlid='mail.mt_comment',
                )
        return result
