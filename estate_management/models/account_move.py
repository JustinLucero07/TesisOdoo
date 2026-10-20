# -*- coding: utf-8 -*-
from odoo import models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    property_id = fields.Many2one('estate.property', string='Propiedad Inmueble')
    property_qr_image = fields.Binary(
        related='property_id.qr_image', string='QR Propiedad', readonly=True)
    estate_transaction_type = fields.Selection([
        ('sale', 'Venta'),
        ('commission', 'Comisión'),
        ('other', 'Otro')
    ], string='Tipo de Transacción Inmobiliaria', default='other')
    
    closing_payment_type = fields.Selection([
        ('cash', 'Contado'),
        ('credit', 'Con Crédito (Hipotecario)'),
    ], string='Tipo de Cierre (Condición de Pago)')

    def write(self, vals):
        result = super().write(vals)
        # Cuando la factura se paga → sincronizar el estate.payment relacionado
        if 'payment_state' in vals and vals['payment_state'] in ('paid', 'in_payment'):
            for move in self:
                if move.move_type != 'out_invoice':
                    continue
                estate_payments = self.env['estate.payment'].search([
                    ('invoice_id', '=', move.id),
                    ('state', '=', 'pending'),
                ])
                if estate_payments:
                    estate_payments.write({'state': 'paid'})
                    move.message_post(
                        body=f'Pago inmobiliario <b>{", ".join(estate_payments.mapped("name"))}</b> '
                             f'marcado como <b>Pagado</b> automáticamente al confirmar la factura.')
        return result

