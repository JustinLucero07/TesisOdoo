# -*- coding: utf-8 -*-
import re

from odoo import models, fields, api
from odoo.exceptions import UserError
from markupsafe import Markup

from ..tools.invoice_modes import INVOICE_MODES, find_tax, is_invoiced, payment_journal, vat_amount


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
    estate_buyer_phones = fields.Char(
        string='Teléfonos comprador', compute='_compute_estate_phones',
        help='Todos los números del comprador, separados por " / ".')
    estate_owner_phones = fields.Char(
        string='Teléfonos propietario', compute='_compute_estate_phones',
        help='Todos los números del propietario, separados por " / ".')
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
    estate_collected_method_manual = fields.Selection(
        selection='_estate_collect_methods', string='Forma de cobro (manual)', copy=False)
    estate_collected_invoice_manual = fields.Selection(
        INVOICE_MODES, string='Factura del cobro (manual)', copy=False)
    estate_collected_reference = fields.Char(
        string='Comprobante del cobro', copy=False,
        help='Nº de transferencia, recibo o depósito con el que pagó el propietario.')
    estate_collected_bank_from = fields.Char(
        string='Banco de origen (cobro)', copy=False,
        help='Banco desde el que pagó el propietario.')
    estate_collected_bank_to = fields.Char(
        string='Banco de destino (cobro)', copy=False,
        help='Banco de la oficina donde entró el pago.')
    estate_collected_method = fields.Selection(
        selection='_estate_collect_methods', string='Forma de cobro',
        compute='_compute_estate_collected', store=True)
    estate_collected_invoice = fields.Selection(
        INVOICE_MODES, string='Factura', compute='_compute_estate_collected', store=True)
    estate_collection_payment_ids = fields.One2many(
        'account.payment', 'estate_sale_order_id', string='Pagos del cobro',
        domain=[('estate_kind', '=', 'collection')])
    estate_commission_collected = fields.Boolean(
        string='Comisión cobrada', compute='_compute_estate_collected', store=True,
        help='Se marca cuando el propietario pagó la comisión y lo registras con '
             '"Marcar cobrada" (con la fecha y la forma de pago reales).')
    estate_collected_date = fields.Date(
        string='Fecha de cobro', compute='_compute_estate_collected', store=True)
    estate_collection_state = fields.Selection([
        ('pending', 'Por cobrar'),
        ('collected', 'Cobrada'),
    ], string='Cobro', compute='_compute_estate_collected', store=True)
    # --- Proceso ordenado de la venta: venta → cobro → asesores ---
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
    # --- Ganancia de la oficina por venta cobrada ---
    estate_advisors_amount = fields.Monetary(
        string='A asesores', compute='_compute_estate_office', store=True,
        help='Lo pagado o asignado a los asesores por esta venta (reparto por pasos '
             'o pago a un solo asesor).')
    estate_advisors_pct = fields.Float(
        string='% a asesores', compute='_compute_estate_office', store=True)
    estate_office_amount = fields.Monetary(
        string='Ganancia oficina', compute='_compute_estate_office', store=True,
        help='Comisión cobrada al propietario (sin IVA) menos lo de los asesores.')
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

    @api.model
    def _estate_collect_methods(self):
        return [('cash', 'Efectivo'), ('transfer', 'Transferencia'),
                ('deposit', 'Depósito'), ('check', 'Cheque'), ('other', 'Otro')]

    @api.depends('estate_collected_manual', 'estate_collected_manual_date',
                 'estate_collected_method_manual', 'estate_collected_invoice_manual')
    def _compute_estate_collected(self):
        """Una venta queda "Cobrada" SOLO cuando el usuario la marca con
        "Marcar cobrada". El pago de la factura en Facturación ya no la marca
        sola: así todas las ventas pasan por "Comisiones por cobrar" y el
        control del cobro lo lleva la oficina."""
        for order in self:
            collected = bool(order.estate_collected_manual)
            order.estate_commission_collected = collected
            order.estate_collection_state = 'collected' if collected else 'pending'
            order.estate_collected_date = order.estate_collected_manual_date if collected else False
            order.estate_collected_method = order.estate_collected_method_manual if collected else False
            order.estate_collected_invoice = order.estate_collected_invoice_manual if collected else False

    def _compute_estate_deal_stage(self):
        for order in self:
            if not order.estate_commission_collected:
                order.estate_deal_stage = 'sold'
            elif order.estate_advisors_state == 'paid':
                order.estate_deal_stage = 'paid'
            else:
                order.estate_deal_stage = 'collected'

    @api.depends('amount_untaxed', 'property_id.commission_ids.amount',
                 'property_id.commission_ids.state',
                 'property_id.commission_ids.parent_commission_id',
                 'property_id.commission_ids.split_line_ids.amount')
    def _compute_estate_office(self):
        for order in self:
            asesores = 0.0
            top = order.property_id.commission_ids.filtered(
                lambda c: not c.parent_commission_id and c.state != 'cancelled')
            for com in top:
                hijas = com.child_commission_ids.filtered(lambda c: c.state != 'cancelled')
                if hijas:
                    asesores += sum(hijas.mapped('amount'))
                elif com.split_line_ids:
                    # Reparto preparado o guardado sin pagar: ya se sabe cuánto va.
                    asesores += sum(com.split_line_ids.mapped('amount'))
                elif com.state == 'paid':
                    asesores += com.amount
            base = order.amount_untaxed
            order.estate_advisors_amount = asesores
            order.estate_advisors_pct = (asesores / base * 100.0) if base else 0.0
            order.estate_office_amount = base - asesores

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
        }
        if len(commissions) == 1:
            action.update(view_mode='form', res_id=commissions.id)
        else:
            action['context'] = {'default_property_id': self.property_id.id}
            action.update(view_mode='list,form', domain=[('property_id', '=', self.property_id.id)])
        return action

    def _estate_register_collection(self, mode, tax, date, method, method_label, reference,
                                    bank_from=False, bank_to=False):
        """Deja el cobro de la comisión en Facturación.

        Con factura (15% o 0%) la factura del cliente queda con ese IVA y se le
        registra el pago. Sin factura se anula la factura pendiente y se
        registra un recibo de cobro directo por el monto de la comisión."""
        self.ensure_one()
        journal = payment_journal(self.env, method)
        invoices = self.invoice_ids.filtered(
            lambda m: m.move_type == 'out_invoice' and m.state != 'cancel')
        base = self.amount_untaxed or self.amount_total
        estate_vals = {
            'estate_kind': 'collection',
            'estate_invoice_mode': mode,
            'estate_property_id': self.property_id.id,
            'estate_sale_order_id': self.id,
            'estate_base_amount': base,
            'estate_vat_amount': vat_amount(base, mode),
            'estate_method_label': method_label,
            'estate_bank_from': bank_from,
            'estate_bank_to': bank_to,
        }
        payments = self.env['account.payment']
        if is_invoiced(mode):
            if not invoices:
                for line in self.order_line.filtered(lambda l: not l.display_type):
                    line.qty_delivered = line.product_uom_qty
                invoices = self._create_invoices()
            for inv in invoices:
                if inv.payment_state in ('paid', 'in_payment'):
                    continue
                lines = inv.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
                if any(l.tax_ids != tax for l in lines):
                    if inv.state == 'posted':
                        inv.button_draft()
                    lines.write({'tax_ids': [(6, 0, tax.ids)]})
                if inv.state == 'draft':
                    inv.invoice_date = inv.invoice_date or date
                    inv.action_post()
                payments |= self.env['account.payment.register'].with_context(
                    active_model='account.move', active_ids=inv.ids,
                ).create({
                    'payment_date': date,
                    'journal_id': journal.id,
                    'communication': reference or inv.name,
                })._create_payments()
        else:
            for inv in invoices.filtered(lambda m: m.payment_state not in ('paid', 'in_payment')):
                if inv.state == 'posted':
                    inv.button_draft()
                inv.button_cancel()
            if base > 0:
                payments = self.env['account.payment'].create(dict(estate_vals, **{
                    'payment_type': 'inbound',
                    'partner_type': 'customer',
                    'partner_id': self.partner_id.id,
                    'amount': base,
                    'date': date,
                    'journal_id': journal.id,
                    'memo': '%s · %s' % (self.name, reference or 'Comisión sin factura'),
                }))
                payments.action_post()
        payments.write(estate_vals)
        return payments

    def _estate_collection_payments(self):
        """Pagos del cobro. Las ventas marcadas como cobradas antes de que el
        cobro se registrara en Facturación no tienen pago: se registra ahora
        con los datos que se pusieron al marcarla (fecha, forma, factura y
        referencia). Si la factura ya se había pagado en Facturación, se usa
        ese pago."""
        self.ensure_one()
        payments = self.estate_collection_payment_ids.filtered(lambda p: p.state != 'canceled')
        if payments or not self.estate_commission_collected:
            return payments
        mode = self.estate_collected_invoice_manual or 'with'
        invoices = self.invoice_ids.filtered(
            lambda m: m.move_type == 'out_invoice' and m.state == 'posted')
        paid = invoices._get_reconciled_payments().filtered(lambda p: p.state != 'canceled')
        method = self.estate_collected_method_manual
        method_label = dict(self._estate_collect_methods()).get(method, '')
        if paid:
            base = self.amount_untaxed or self.amount_total
            paid.write({
                'estate_kind': 'collection',
                'estate_invoice_mode': mode,
                'estate_property_id': self.property_id.id,
                'estate_sale_order_id': self.id,
                'estate_base_amount': base,
                'estate_vat_amount': vat_amount(base, mode),
                'estate_method_label': method_label,
                'estate_bank_from': self.estate_collected_bank_from,
                'estate_bank_to': self.estate_collected_bank_to,
            })
            return paid
        return self._estate_register_collection(
            mode, find_tax(self.env, 'sale', mode),
            self.estate_collected_manual_date or self.estate_collected_date or fields.Date.context_today(self),
            method, method_label, self.estate_collected_reference,
            self.estate_collected_bank_from, self.estate_collected_bank_to)

    def action_estate_view_collection(self):
        self.ensure_one()
        payments = self._estate_collection_payments()
        if not payments:
            raise UserError('Esta venta todavía no tiene un cobro registrado.')
        action = {
            'type': 'ir.actions.act_window',
            'name': 'Cobro de la comisión',
            'res_model': 'account.payment',
        }
        if len(payments) == 1:
            action.update(view_mode='form', res_id=payments.id)
        else:
            action.update(view_mode='list,form', domain=[('id', 'in', payments.ids)])
        return action

    def action_estate_print_collection(self):
        payments = self.env['account.payment']
        for order in self:
            payments |= order._estate_collection_payments()
        if not payments:
            raise UserError('Esta venta todavía no tiene un cobro registrado.')
        return self.env.ref('estate_management.action_report_estate_payment_receipt').report_action(payments)

    def action_estate_unmark_collected(self):
        # Se anula lo contable del cobro: el pago y, si se anuló la factura por
        # cobrar sin factura, vuelve a quedar pendiente.
        for order in self:
            payments = order.estate_collection_payment_ids.filtered(lambda p: p.state != 'canceled')
            for pay in payments:
                pay.action_draft()
                pay.action_cancel()
            if order.estate_collected_invoice_manual == 'without':
                for inv in order.invoice_ids.filtered(
                        lambda m: m.move_type == 'out_invoice' and m.state == 'cancel'):
                    inv.button_draft()
                    inv.action_post()
        self.write({'estate_collected_manual': False,
                    'estate_collected_manual_date': False,
                    'estate_collected_method_manual': False,
                    'estate_collected_invoice_manual': False,
                    'estate_collected_reference': False,
                    'estate_collected_bank_from': False,
                    'estate_collected_bank_to': False})

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
