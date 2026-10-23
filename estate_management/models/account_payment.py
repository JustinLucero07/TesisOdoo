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
    estate_commission_ids = fields.One2many(
        'estate.commission', 'payment_id', string='Comisiones pagadas')
    estate_base_amount = fields.Monetary(
        string='Base (sin IVA)', currency_field='currency_id', copy=False)
    estate_vat_amount = fields.Monetary(
        string='IVA', currency_field='currency_id', copy=False)
    estate_method_label = fields.Char(string='Forma de pago', copy=False)
    estate_bank_from = fields.Char(string='Banco de origen', copy=False)
    estate_bank_to = fields.Char(string='Banco de destino', copy=False)

    def action_estate_correct(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Corregir cobro' if self.estate_kind == 'collection' else 'Corregir pago',
            'res_model': 'estate.payment.correct.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_model': 'account.payment', 'active_ids': self.ids},
        }

    def action_estate_print(self):
        """Pagos a asesores: una hoja por asesor con su desglose por rol.
        Cobros: el recibo de cobro."""
        advisor = self.filtered(lambda p: p.estate_kind == 'advisor' and p.estate_commission_ids)
        if advisor and advisor == self:
            return self.env.ref('estate_management.action_report_commission_receipt').report_action(
                advisor.mapped('estate_commission_ids'))
        return self.env.ref('estate_management.action_report_estate_payment_receipt').report_action(self)
