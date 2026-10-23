# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError

from ..tools.invoice_modes import INVOICE_MODES, find_tax, is_invoiced, vat_amount


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

    @api.depends('order_ids', 'invoice')
    def _compute_order_count(self):
        for wiz in self:
            wiz.order_count = len(wiz.order_ids)
            base = sum(wiz.order_ids.mapped('amount_untaxed'))
            if not base:
                base = sum(wiz.order_ids.mapped('amount_total'))
            wiz.amount_untaxed = round(base, 2)
            wiz.amount_vat = vat_amount(base, wiz.invoice)
            wiz.amount_total = round(base + wiz.amount_vat, 2)

    @api.onchange('invoice', 'order_ids')
    def _onchange_invoice(self):
        self._compute_order_count()

    def action_confirm(self):
        if not self.order_ids:
            raise UserError('No hay ventas por cobrar en la selección (solo cuentan las '
                            'órdenes de venta confirmadas con propiedad y sin cobrar).')
        tax = find_tax(self.env, 'sale', self.invoice)
        for order in self.order_ids:
            lines = order.order_line.filtered(lambda l: not l.display_type)
            lines.write({'tax_ids': [(6, 0, tax.ids)]})

        self.order_ids.write({
            'estate_collected_manual': True,
            'estate_collected_manual_date': self.date,
            'estate_collected_method_manual': self.method,
            'estate_collected_invoice_manual': self.invoice,
            'estate_collected_reference': self.reference,
        })
        metodo = dict(self.env['sale.order']._estate_collect_methods()).get(self.method)
        factura = dict(INVOICE_MODES).get(self.invoice)
        for order in self.order_ids:
            payments = order._estate_register_collection(
                self.invoice, tax, self.date, self.method, metodo, self.reference)
            total_str = '{:,.2f}'.format(sum(payments.mapped('amount')) or order.amount_total)
            order.message_post(body='Comisión cobrada el %s · %s · %s · Total cobrado: $%s%s.' % (
                self.date.strftime('%d/%m/%Y'), metodo, factura, total_str,
                ' · Comprobante %s' % self.reference if self.reference else ''))
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
