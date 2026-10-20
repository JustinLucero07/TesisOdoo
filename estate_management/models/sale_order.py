# -*- coding: utf-8 -*-
import re

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
    estate_buyer_phones = fields.Char(
        string='Teléfonos comprador', compute='_compute_estate_phones',
        help='Todos los números del comprador, separados por " / ".')
    estate_owner_phones = fields.Char(
        string='Teléfonos propietario', compute='_compute_estate_phones',
        help='Todos los números del propietario, separados por " / ".')
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
    estate_capture_initials = fields.Char(
        string='Captación', compute='_compute_estate_advisor_roles')
    estate_reception_initials = fields.Char(
        string='Recepción', compute='_compute_estate_advisor_roles')
    estate_visit_initials = fields.Char(
        string='Visita', compute='_compute_estate_advisor_roles')
    estate_closing_initials = fields.Char(
        string='Cierre', compute='_compute_estate_advisor_roles')

    # --- Cobro de la comisión al propietario ---
    estate_collected_manual = fields.Boolean(
        string='Cobro marcado a mano', copy=False, tracking=True,
        help='Marca la comisión como cobrada aunque no se haya registrado el '
             'pago en la factura (por ejemplo, si se cobró en efectivo).')
    estate_collected_manual_date = fields.Date(
        string='Fecha de cobro (manual)', copy=False)
    estate_commission_collected = fields.Boolean(
        string='Comisión cobrada', compute='_compute_estate_collected', store=True,
        help='Se marca sola cuando la factura de la comisión queda pagada, o '
             'cuando se marca a mano con "Marcar como cobrada".')
    estate_collected_date = fields.Date(
        string='Fecha de cobro', compute='_compute_estate_collected', store=True)
    estate_collection_state = fields.Selection([
        ('pending', 'Por cobrar'),
        ('collected', 'Cobrada'),
    ], string='Cobro', compute='_compute_estate_collected', store=True)
    # --- Proceso ordenado de la venta: seña → venta → cobro → asesores ---
    estate_earnest_amount = fields.Float(
        related='property_id.deal_earnest_amount', string='Seña / Arras')
    estate_earnest_received_by = fields.Char(
        string='Seña recibida por', compute='_compute_estate_earnest')
    estate_earnest_method = fields.Char(
        string='Forma de pago de la seña', compute='_compute_estate_earnest')
    estate_deal_stage = fields.Selection([
        ('sold', '1. Vendida · comisión por cobrar'),
        ('collected', '2. Cobrada · asesores por pagar'),
        ('paid', '3. Asesores pagados'),
    ], string='Etapa del negocio', compute='_compute_estate_deal_stage')
    estate_advisors_state = fields.Selection([
        ('none', 'Sin comisión'),
        ('pending', 'Por pagar'),
        ('paid', 'Pagados'),
    ], string='Pago a asesores', compute='_compute_estate_advisors_state',
        help='Si ya se pagó la comisión a los asesores de esta venta.')
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
            for value in candidates:
                # A veces se escriben dos números en el mismo campo.
                for phone in re.split(r'[,;/\n]+', value or ''):
                    phone = phone.strip()
                    key = re.sub(r'\D', '', phone)[-9:]
                    if phone and key not in [re.sub(r'\D', '', p)[-9:] for p in phones]:
                        phones.append(phone)
        return phones

    @api.depends('partner_id.phone', 'partner_id.mobile', 'partner_id.extra_phone_ids.phone',
                 'estate_buyer_id.phone', 'estate_buyer_id.mobile',
                 'estate_buyer_id.extra_phone_ids.phone')
    def _compute_estate_phones(self):
        for order in self:
            buyer = self._estate_partner_phones(order.estate_buyer_id)
            owner = self._estate_partner_phones(order.partner_id)
            order.estate_buyer_phones = ' / '.join(buyer) or False
            order.estate_owner_phones = ' / '.join(owner) or False
            buyer, owner = buyer + [False, False], owner + [False, False]
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
        role_fields = {'capture': 'estate_capture_initials',
                       'reception': 'estate_reception_initials',
                       'visit': 'estate_visit_initials',
                       'closing': 'estate_closing_initials'}
        for order in self:
            by_role = {fname: [] for fname in role_fields.values()}
            lines = commissions.filtered(
                lambda c: c.property_id == order.property_id
            ).sorted(lambda c: (c.role_sequence, c.id))
            parts = []
            for c in lines:
                initials = self._estate_initials(c.user_id.name)
                part = f"{self._ESTATE_ROLE_SHORT[c.role]} {initials}" if c.role else initials
                if part not in parts:
                    parts.append(part)
                roles = role_fields.values() if c.role == 'all' else [role_fields.get(c.role)]
                for fname in roles:
                    if fname and initials not in by_role[fname]:
                        by_role[fname].append(initials)
            order.estate_advisor_roles = ' · '.join(parts) or False
            for fname, initials in by_role.items():
                order[fname] = ' y '.join(initials) or False

    @api.depends('estate_collected_manual', 'estate_collected_manual_date',
                 'order_line.invoice_lines.move_id.payment_state',
                 'order_line.invoice_lines.move_id.state')
    def _compute_estate_collected(self):
        for order in self:
            invoices = order.order_line.invoice_lines.move_id.filtered(
                lambda m: m.move_type == 'out_invoice' and m.state == 'posted')
            paid = bool(invoices) and all(
                m.payment_state in ('paid', 'in_payment') for m in invoices)
            date = False
            if paid:
                receivable = invoices.line_ids.filtered(
                    lambda l: l.account_id.account_type == 'asset_receivable')
                dates = receivable.matched_credit_ids.mapped('max_date')
                date = max(dates) if dates else max(invoices.mapped('invoice_date'))
            order.estate_commission_collected = paid or order.estate_collected_manual
            order.estate_collection_state = ('collected' if order.estate_commission_collected
                                             else 'pending')
            order.estate_collected_date = (order.estate_collected_manual_date
                                           if order.estate_collected_manual else date)

    @api.depends('property_id.deal_earnest_received_by_agency',
                 'property_id.deal_earnest_received_by_owner',
                 'property_id.deal_earnest_received_by_proxy',
                 'property_id.deal_earnest_payment_cash',
                 'property_id.deal_earnest_payment_transfer',
                 'property_id.deal_earnest_payment_deposit',
                 'property_id.deal_earnest_payment_other')
    def _compute_estate_earnest(self):
        for order in self:
            prop = order.property_id
            quien = [label for flag, label in (
                (prop.deal_earnest_received_by_agency, 'Inmobiliaria'),
                (prop.deal_earnest_received_by_owner, 'Propietario'),
                (prop.deal_earnest_received_by_proxy, 'Apoderado'),
            ) if flag]
            como = [label for flag, label in (
                (prop.deal_earnest_payment_cash, 'Efectivo'),
                (prop.deal_earnest_payment_transfer, 'Transferencia'),
                (prop.deal_earnest_payment_deposit, 'Depósito'),
            ) if flag]
            if prop.deal_earnest_payment_other:
                como.append(prop.deal_earnest_payment_other)
            order.estate_earnest_received_by = ', '.join(quien) or False
            order.estate_earnest_method = ', '.join(como) or False

    def _compute_estate_deal_stage(self):
        for order in self:
            if not order.estate_commission_collected:
                order.estate_deal_stage = 'sold'
            elif order.estate_advisors_state == 'paid':
                order.estate_deal_stage = 'paid'
            else:
                order.estate_deal_stage = 'collected'

    def _compute_estate_advisors_state(self):
        commissions = self.env['estate.commission'].sudo().search([
            ('property_id', 'in', self.property_id.ids),
            ('parent_commission_id', '=', False),
            ('state', '!=', 'cancelled'),
        ]) if self.property_id else self.env['estate.commission']
        for order in self:
            mine = commissions.filtered(lambda c: c.property_id == order.property_id)
            if not mine:
                order.estate_advisors_state = 'none'
                continue
            # Lo que se paga es la comisión suelta o, si se repartió, cada hija.
            to_pay = mine.filtered(lambda c: c.state != 'split') | mine.child_commission_ids.filtered(
                lambda c: c.state != 'cancelled')
            order.estate_advisors_state = ('paid' if to_pay and all(c.state == 'paid' for c in to_pay)
                                           else 'pending')

    def action_estate_mark_collected(self):
        """Pide la fecha real del cobro (las ventas antiguas se cobran tarde)."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Marcar comisión cobrada',
            'res_model': 'estate.sale.collect.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_model': 'sale.order', 'active_ids': self.ids},
        }

    def action_estate_open_commission(self):
        """Lleva a la comisión de la propiedad para repartirla y pagar a los asesores."""
        self.ensure_one()
        commissions = self.env['estate.commission'].search([
            ('property_id', '=', self.property_id.id),
            ('parent_commission_id', '=', False),
            ('state', '!=', 'cancelled'),
        ])
        action = {
            'type': 'ir.actions.act_window',
            'name': 'Comisión — %s' % (self.property_id.display_name or self.name),
            'res_model': 'estate.commission',
            'context': {'default_property_id': self.property_id.id,
                        'default_amount': self.amount_untaxed},
        }
        if len(commissions) == 1:
            action.update(view_mode='form', res_id=commissions.id)
        else:
            action.update(view_mode='list,form', domain=[('property_id', '=', self.property_id.id)])
        return action

    def action_estate_unmark_collected(self):
        self.write({'estate_collected_manual': False,
                    'estate_collected_manual_date': False})

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
