# -*- coding: utf-8 -*-
"""Pago a un tercero que ayudó en el negocio (colaborador, referido, otra
agencia). Sale del cobro de la venta: se descuenta de la ganancia de la oficina
y queda en Facturación → Inmobiliaria → Pagos a terceros con su comprobante."""
from odoo import fields, models
from odoo.exceptions import UserError


class EstateThirdPaymentWizard(models.TransientModel):
    _name = 'estate.third.payment.wizard'
    _description = 'Registrar pago a tercero'

    order_id = fields.Many2one('sale.order', string='Venta', required=True, readonly=True)
    property_id = fields.Many2one(related='order_id.property_id')
    currency_id = fields.Many2one(related='order_id.currency_id')
    partner_id = fields.Many2one('res.partner', string='¿A quién se le paga?', required=True)
    concept = fields.Char(string='Concepto', required=True, default='Colaboración en la venta',
                          help='Ej. Referido, ayuda con la visita, parte de otra agencia.')
    amount = fields.Monetary(string='Monto', required=True)
    date = fields.Date(string='Fecha de pago', required=True, default=fields.Date.context_today)
    method = fields.Selection(
        selection=lambda self: self.env['sale.order']._estate_collect_methods(),
        string='Forma de pago', required=True, default='transfer')
    reference = fields.Char(string='Comprobante / Referencia')
    bank_from = fields.Char(string='Banco de origen')
    bank_to = fields.Char(string='Banco de destino')
    invoice_number = fields.Char(string='Nº de factura recibida',
                                 help='Si el tercero entregó factura, su número.')
    note = fields.Text(string='Observaciones')

    def action_confirm(self):
        self.ensure_one()
        if self.amount <= 0:
            raise UserError('El monto debe ser mayor que cero.')
        metodo = dict(self.env['sale.order']._estate_collect_methods()).get(self.method)
        payment = self.order_id._estate_create_third_payment(
            self.partner_id, self.amount, self.date, self.method, metodo, self.concept,
            reference=self.reference, bank_from=self.bank_from, bank_to=self.bank_to,
            invoice_number=self.invoice_number, note=self.note)
        return self.env.ref('estate_management.action_report_estate_payment_receipt').report_action(payment)
