# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    property_id = fields.Many2one('estate.property', string='Propiedad Vinculada')
    estate_transaction_type = fields.Selection([
        ('sale', 'Venta'),
        ('rent', 'Alquiler')
    ], string='Tipo de Contrato Inmobiliario', default='sale')
    lead_id = fields.Many2one('crm.lead', string='Lead de Origen', tracking=True,
                              help='Lead CRM que originó esta orden de venta.')
    customer_signature = fields.Binary(
        string='Firma del Cliente', copy=False, attachment=True,
        help='Firma digital del cliente para aprobar la orden.')
    signature_date = fields.Datetime(
        string='Fecha de Firma', readonly=True, copy=False)

    @api.onchange('customer_signature')
    def _onchange_customer_signature(self):
        if self.customer_signature and not self.signature_date:
            self.signature_date = fields.Datetime.now()

    def action_confirm(self):
        result = super().action_confirm()
        for order in self:
            if order.property_id:
                # Notificar en el chatter de la propiedad
                order.property_id.message_post(
                    body=f'✅ Orden de venta <b>{order.name}</b> CONFIRMADA para '
                         f'<b>{order.partner_id.name}</b> por ${order.amount_total:,.2f}.')
            if order.lead_id:
                # Notificar en el chatter del lead CRM
                order.lead_id.message_post(
                    body=f'✅ Orden de venta <b>{order.name}</b> confirmada para la propiedad '
                         f'<b>{order.property_id.title if order.property_id else "N/A"}</b> '
                         f'por ${order.amount_total:,.2f}.')
            # Enviar email de confirmación al cliente si tiene correo
            if order.partner_id and order.partner_id.email:
                order.message_post(
                    body=(f'<p>Estimado/a <strong>{order.partner_id.name}</strong>,</p>'
                          f'<p>Su orden de venta <strong>{order.name}</strong> ha sido confirmada.</p>'
                          f'<p><strong>Propiedad:</strong> {order.property_id.title if order.property_id else "N/A"}<br/>'
                          f'<strong>Monto total:</strong> ${order.amount_total:,.2f}</p>'
                          f'<p>Nuestro equipo le contactará para coordinar los siguientes pasos.</p>'),
                    partner_ids=[order.partner_id.id],
                    subtype_xmlid='mail.mt_comment',
                )
        return result
