# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    property_id = fields.Many2one('estate.property', string='Propiedad Inmueble')
    property_qr_image = fields.Binary(
        related='property_id.qr_image', string='QR Propiedad', readonly=True)
    estate_transaction_type = fields.Selection([
        ('sale', 'Venta'),
        ('rent', 'Alquiler'),
        ('commission', 'Comisión'),
        ('other', 'Otro')
    ], string='Tipo de Transacción Inmobiliaria', default='other')

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
                        body=f'💰 Pago inmobiliario <b>{", ".join(estate_payments.mapped("name"))}</b> '
                             f'marcado como <b>Pagado</b> automáticamente al confirmar la factura.')
        return result

    def action_mark_property_from_invoice(self):
        """Botón manual: actualiza el estado de la propiedad vinculada al pagar esta factura."""
        self.ensure_one()
        if not self.property_id:
            raise ValidationError('Esta factura no tiene propiedad vinculada.')
        prop = self.property_id
        if self.payment_state not in ('paid', 'in_payment'):
            raise ValidationError('La factura aún no está marcada como pagada.')
        if prop.state not in ('reserved', 'available'):
            raise ValidationError(
                f'La propiedad ya está en estado "{prop.state}". Solo se puede actualizar desde Reservada o Disponible.')
        if prop.offer_type == 'sale':
            prop.write({'state': 'sold'})
            prop.message_post(
                body=f'✅ Propiedad marcada como <b>VENDIDA</b> desde la factura <b>{self.name}</b>.')
            self.message_post(
                body=f'✅ Propiedad <b>{prop.title}</b> marcada como VENDIDA.')
        elif prop.offer_type == 'rent':
            prop.write({'state': 'rented'})
            prop.message_post(
                body=f'✅ Propiedad marcada como <b>ARRENDADA</b> desde la factura <b>{self.name}</b>.')
            self.message_post(
                body=f'✅ Propiedad <b>{prop.title}</b> marcada como ARRENDADA.')

    @api.model
    def _cron_sync_property_state_from_invoices(self):
        """Cron diario: detecta facturas pagadas y actualiza estado de la propiedad vinculada."""
        paid_invoices = self.search([
            ('move_type', '=', 'out_invoice'),
            ('payment_state', 'in', ('paid', 'in_payment')),
            ('property_id', '!=', False),
            ('property_id.state', '=', 'reserved'),
        ])
        for move in paid_invoices:
            prop = move.property_id
            if prop.offer_type == 'sale':
                prop.write({'state': 'sold'})
                prop.message_post(
                    body=f'✅ Propiedad marcada como <b>VENDIDA</b> automáticamente '
                         f'(factura <b>{move.name}</b> pagada).')
            elif prop.offer_type == 'rent':
                prop.write({'state': 'rented'})
                prop.message_post(
                    body=f'✅ Propiedad marcada como <b>ARRENDADA</b> automáticamente '
                         f'(factura <b>{move.name}</b> pagada).')
