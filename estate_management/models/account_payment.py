# -*- coding: utf-8 -*-
from odoo import fields, models

from ..tools.invoice_modes import INVOICE_MODES


class AccountPayment(models.Model):
    """Datos inmobiliarios de cada cobro o pago, para verlos en Facturación."""
    _inherit = 'account.payment'

    estate_kind = fields.Selection([
        ('collection', 'Cobro de comisión (propietario)'),
        ('advisor', 'Pago a asesor'),
    ], string='Movimiento inmobiliario', index=True, copy=False)
    estate_invoice_mode = fields.Selection(
        INVOICE_MODES, string='Factura', copy=False)
    estate_property_id = fields.Many2one(
        'estate.property', string='Propiedad', index=True, copy=False)
    estate_sale_order_id = fields.Many2one(
        'sale.order', string='Venta', copy=False)
    estate_commission_id = fields.Many2one(
        'estate.commission', string='Comisión', copy=False)
    estate_base_amount = fields.Monetary(
        string='Base (sin IVA)', currency_field='currency_id', copy=False)
    estate_vat_amount = fields.Monetary(
        string='IVA', currency_field='currency_id', copy=False)
    estate_method_label = fields.Char(string='Forma de pago', copy=False)
