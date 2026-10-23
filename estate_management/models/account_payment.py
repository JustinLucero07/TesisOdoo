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
    estate_link_order_id = fields.Many2one(
        'sale.order', string='Venta vinculada', compute='_compute_estate_link_order')
    estate_link_commission_count = fields.Integer(compute='_compute_estate_link_order')

    def _compute_estate_link_order(self):
        SaleOrder = self.env['sale.order']
        for pay in self:
            order = pay.estate_sale_order_id
            if not order and pay.estate_property_id:
                order = SaleOrder.search([('property_id', '=', pay.estate_property_id.id),
                                          ('state', '!=', 'cancel')], order='id desc', limit=1)
            pay.estate_link_order_id = order
            pay.estate_link_commission_count = len(pay._estate_commissions())

    def _estate_commissions(self):
        self.ensure_one()
        if self.estate_kind == 'advisor':
            return self.estate_commission_ids or self.estate_commission_id
        if self.estate_property_id:
            return self.env['estate.commission'].search([
                ('property_id', '=', self.estate_property_id.id),
                ('parent_commission_id', '=', False), ('state', '!=', 'cancelled')])
        return self.env['estate.commission']

    def action_estate_view_order(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'res_model': 'sale.order',
                'res_id': self.estate_link_order_id.id, 'view_mode': 'form'}

    def action_estate_view_property(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'res_model': 'estate.property',
                'res_id': self.estate_property_id.id, 'view_mode': 'form'}

    def action_estate_view_commissions(self):
        self.ensure_one()
        coms = self._estate_commissions()
        action = {'type': 'ir.actions.act_window', 'name': 'Comisiones',
                  'res_model': 'estate.commission'}
        if len(coms) == 1:
            action.update(view_mode='form', res_id=coms.id)
        else:
            action.update(view_mode='list,form', domain=[('id', 'in', coms.ids)])
        return action

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
