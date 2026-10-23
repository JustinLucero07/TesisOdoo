# -*- coding: utf-8 -*-
"""Corregir un cobro o un pago a asesor ya registrado.

Si algo se llenó mal (fecha, forma de pago, factura, referencia o bancos), se
anula lo contable que había y se vuelve a registrar con los datos correctos.
El pago anulado queda en Facturación como "Cancelado", como constancia.
"""
from odoo import api, fields, models
from odoo.exceptions import UserError

from ..tools.invoice_modes import INVOICE_MODES


class EstatePaymentCorrectWizard(models.TransientModel):
    _name = 'estate.payment.correct.wizard'
    _description = 'Corregir cobro o pago'

    commission_ids = fields.Many2many('estate.commission', string='Comisiones')
    order_id = fields.Many2one('sale.order', string='Venta')
    kind = fields.Selection([
        ('advisor', 'Pago a asesor'),
        ('collection', 'Cobro al propietario'),
    ], required=True, readonly=True)
    partner_name = fields.Char(string='A / De', readonly=True)
    date = fields.Date(string='Fecha', required=True)
    method = fields.Selection(
        selection=lambda self: self.env['sale.order']._estate_collect_methods(),
        string='Forma de pago', required=True)
    invoice = fields.Selection(INVOICE_MODES, string='Factura', required=True)
    reference = fields.Char(string='Comprobante / Referencia')
    bank_from = fields.Char(string='Banco de origen')
    bank_to = fields.Char(string='Banco de destino')

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        model = self.env.context.get('active_model')
        ids = self.env.context.get('active_ids') or []
        commissions = self.env['estate.commission']
        order = self.env['sale.order']
        if model == 'estate.commission':
            commissions = commissions.browse(ids)
        elif model == 'sale.order':
            order = order.browse(ids[:1])
        elif model == 'account.payment':
            pay = self.env['account.payment'].browse(ids[:1])
            commissions = pay.estate_commission_ids or pay.estate_commission_id
            order = pay.estate_sale_order_id if not commissions else order
        if commissions:
            # Todo lo que se pagó con el mismo pago se corrige junto.
            pays = commissions.mapped('payment_id')
            if pays:
                commissions |= commissions.search([('payment_id', 'in', pays.ids)])
            com = commissions[:1]
            vals.update({
                'kind': 'advisor',
                'commission_ids': [(6, 0, commissions.ids)],
                'partner_name': com.user_id.name,
                'date': com.payment_date,
                'method': com.payment_method,
                'invoice': com.has_invoice or 'without',
                'reference': com.payment_reference,
                'bank_from': com.payment_bank_from,
                'bank_to': com.payment_bank_to,
            })
        elif order:
            vals.update({
                'kind': 'collection',
                'order_id': order.id,
                'partner_name': order.partner_id.name,
                'date': order.estate_collected_manual_date,
                'method': order.estate_collected_method_manual,
                'invoice': order.estate_collected_invoice_manual or 'with',
                'reference': order.estate_collected_reference,
                'bank_from': order.estate_collected_bank_from,
                'bank_to': order.estate_collected_bank_to,
            })
        return vals

    def action_confirm(self):
        self.ensure_one()
        if self.kind == 'advisor':
            coms = self.commission_ids
            if not coms or any(c.state != 'paid' for c in coms):
                raise UserError('Solo se puede corregir un pago ya registrado.')
            coms.action_reset_to_approved()
            coms.write({
                'payment_date': self.date,
                'payment_method': self.method,
                'has_invoice': self.invoice,
                'payment_reference': self.reference,
                'payment_bank_from': self.bank_from,
                'payment_bank_to': self.bank_to,
            })
            coms.action_register_payment()
            for com in coms:
                com.message_post(body='Pago corregido por %s.' % self.env.user.name)
            return {'type': 'ir.actions.act_window_close'}

        order = self.order_id
        if not order.estate_commission_collected:
            raise UserError('Esta venta todavía no está marcada como cobrada.')
        order._estate_collection_payments()
        order.action_estate_unmark_collected()
        self.env['estate.sale.collect.wizard'].create({
            'order_ids': [(6, 0, order.ids)],
            'date': self.date,
            'method': self.method,
            'invoice': self.invoice,
            'reference': self.reference,
            'bank_from': self.bank_from,
            'bank_to': self.bank_to,
        })._estate_register(follow_up=False)
        order.message_post(body='Cobro corregido por %s.' % self.env.user.name)
        return {'type': 'ir.actions.act_window_close'}
