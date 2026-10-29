# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError

from ..tools.invoice_modes import INVOICE_MODES, find_tax, split_amounts


class EstateSaleCollectWizard(models.TransientModel):
    _name = 'estate.sale.collect.wizard'
    _description = 'Marcar comisión de venta como cobrada'

    order_ids = fields.Many2many('sale.order', string='Ventas')
    currency_id = fields.Many2one(
        'res.currency', string='Moneda',
        default=lambda self: self.env.company.currency_id)
    date = fields.Date(string='Fecha de cobro', required=True,
                       default=fields.Date.context_today,
                       help='Día en que el propietario pagó la comisión. Para ventas '
                            'antiguas pon la fecha real del cobro.')
    method = fields.Selection(
        selection=lambda self: self.env['sale.order']._estate_collect_methods(),
        string='¿Cómo te pagaron?', required=True, default='transfer')
    invoice = fields.Selection(
        INVOICE_MODES, string='¿Con factura?', required=True, default='with')
    reference = fields.Char(string='Comprobante / Referencia',
                            help='Nº de transferencia, recibo o depósito.')
    bank_from = fields.Char(string='Banco de origen', help='Banco desde el que pagó el propietario.')
    bank_to = fields.Char(string='Banco de destino', help='Banco de la oficina donde entró el pago.')
    note = fields.Text(string='Observaciones')
    # Con agencia aliada
    has_allied = fields.Boolean(compute='_compute_order_count')
    collect_full = fields.Boolean(
        string='Cobramos el total y le pagamos al aliado',
        help='Marca si el propietario te pagó la comisión completa: se registra '
             'también el pago al aliado por su parte. Si no, solo se registra la '
             'parte que nos corresponde.')
    allied_gross = fields.Float(string='Comisión total del negocio', compute='_compute_order_count')
    allied_share = fields.Float(string='Parte del aliado', compute='_compute_order_count')
    our_share = fields.Float(string='Nuestra parte', compute='_compute_order_count')
    allied_label = fields.Char(compute='_compute_order_count')
    has_referral = fields.Boolean(compute='_compute_order_count')
    referral_label = fields.Char(compute='_compute_order_count')
    pay_referral = fields.Boolean(
        string='Registrar el pago al referido', default=True,
        help='Registra el pago al tercero o referido anotado en el negocio cerrado. '
             'Se descuenta de la ganancia de la oficina.')
    order_count = fields.Integer(compute='_compute_order_count')
    amount_untaxed = fields.Float(string='Subtotal comisión', compute='_compute_order_count')
    amount_vat = fields.Float(string='IVA', compute='_compute_order_count')
    amount_total = fields.Float(string='Total a marcar', compute='_compute_order_count')

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        ids = self.env.context.get('active_ids') or []
        if self.env.context.get('active_model') == 'sale.order' and ids:
            orders = self.env['sale.order'].browse(ids).filtered(
                lambda o: o.property_id and o.state == 'sale' and not o.estate_commission_collected)
            vals['order_ids'] = [(6, 0, orders.ids)]
        return vals

    @staticmethod
    def _order_gross(order):
        if order.estate_commission_gross:
            return order.estate_commission_gross
        lines = order.order_line.filtered(lambda l: not l.display_type)
        return sum(l.price_unit * l.product_uom_qty for l in lines)

    @api.depends('order_ids', 'invoice', 'collect_full')
    def _compute_order_count(self):
        for wiz in self:
            wiz.order_count = len(wiz.order_ids)
            untaxed = vat = total = gross = allied = 0.0
            agencies = []
            referrals = []
            for order in wiz.order_ids:
                if order.estate_referral_partner_id and order.estate_referral_amount:
                    referrals.append('%s $%s' % (order.estate_referral_partner_id.name,
                                                 '{:,.2f}'.format(order.estate_referral_amount)))
                order_gross = self._order_gross(order)
                share = order_gross
                if order.estate_is_allied:
                    ours = round(order_gross * (order.estate_allied_pct or 50.0) / 100.0, 2)
                    allied += order_gross - ours
                    agencies.append('%s (%.0f%%)' % (
                        order.estate_allied_agency_id.name or 'aliado / colega',
                        100.0 - (order.estate_allied_pct or 50.0)))
                    share = order_gross if wiz.collect_full else ours
                gross += order_gross
                b, v, t = split_amounts(share, wiz.invoice)
                untaxed += b
                vat += v
                total += t
            wiz.has_allied = bool(agencies)
            wiz.has_referral = bool(referrals)
            wiz.referral_label = ', '.join(referrals)
            wiz.allied_gross = round(gross, 2)
            wiz.allied_share = round(allied, 2)
            wiz.our_share = round(gross - allied, 2)
            wiz.allied_label = ', '.join(agencies)
            wiz.amount_untaxed = round(untaxed, 2)
            wiz.amount_vat = round(vat, 2)
            wiz.amount_total = round(total, 2)

    @api.onchange('invoice', 'order_ids', 'collect_full')
    def _onchange_invoice(self):
        self._compute_order_count()

    def action_confirm(self):
        return self._estate_register(follow_up=True)

    def _estate_register(self, follow_up=True):
        if not self.order_ids:
            raise UserError('No hay ventas por cobrar en la selección (solo cuentan las '
                            'órdenes de venta confirmadas con propiedad y sin cobrar).')
        tax = find_tax(self.env, 'sale', self.invoice)
        for order in self.order_ids:
            order._estate_gross()
            order.estate_collect_full = self.collect_full and order.estate_is_allied
            order.estate_pay_referral = self.pay_referral and bool(order.estate_referral_partner_id)
            order._estate_set_collect_lines(order._estate_collect_amount(), tax)

        self.order_ids.write({
            'estate_collected_manual': True,
            'estate_collected_manual_date': self.date,
            'estate_collected_method_manual': self.method,
            'estate_collected_invoice_manual': self.invoice,
            'estate_collected_reference': self.reference,
            'estate_collected_bank_from': self.bank_from,
            'estate_collected_bank_to': self.bank_to,
            'estate_collected_note': self.note,
        })
        metodo = dict(self.env['sale.order']._estate_collect_methods()).get(self.method)
        factura = dict(INVOICE_MODES).get(self.invoice)
        for order in self.order_ids:
            payments = order._estate_register_collection(
                self.invoice, tax, self.date, self.method, metodo, self.reference,
                self.bank_from, self.bank_to, self.note)
            if order.estate_collect_full:
                order._estate_pay_allied(self.date, self.method, metodo, self.reference)
            if order.estate_pay_referral:
                order._estate_pay_referral(self.date, self.method, metodo, self.reference)
            total_str = '{:,.2f}'.format(sum(payments.mapped('amount')) or order.amount_total)
            order.message_post(body='Comisión cobrada el %s · %s · %s · Total cobrado: $%s%s.' % (
                self.date.strftime('%d/%m/%Y'), metodo, factura, total_str,
                ' · Comprobante %s' % self.reference if self.reference else ''))
        if not follow_up:
            return True
        # Una sola venta con el reparto ya listo: seguir directo al pago de los
        # asesores, con la misma forma de pago propuesta.
        if len(self.order_ids) == 1:
            commission = self.env['estate.commission'].search([
                ('property_id', '=', self.order_ids.property_id.id),
                ('parent_commission_id', '=', False),
                ('state', 'in', ('approved', 'split')),
                '|', ('split_line_ids', '!=', False), ('child_commission_ids', '!=', False),
            ], limit=1)
            pending = commission and (commission.state == 'approved' or commission.child_commission_ids.filtered(
                lambda c: c.state in ('draft', 'approved')))
            if pending:
                action = commission.action_open_payout_wizard()
                action['name'] = 'Comisión cobrada · ¿pagar ahora a los asesores?'
                method = self.method if self.method in dict(
                    self.env['estate.commission']._fields['payment_method'].selection) else 'other'
                action['context'] = dict(action['context'], default_payment_method=method)
                return action
        return {'type': 'ir.actions.act_window_close'}
