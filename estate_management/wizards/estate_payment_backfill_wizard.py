# -*- coding: utf-8 -*-
"""Registrar en Facturación los cobros y pagos marcados antes de que el sistema
los registrara solo (antes "sin factura" solo marcaba la comisión pagada)."""
from odoo import api, fields, models


class EstatePaymentBackfillWizard(models.TransientModel):
    _name = 'estate.payment.backfill.wizard'
    _description = 'Registrar cobros y pagos anteriores'

    commission_count = fields.Integer(string='Pagos a asesores sin registrar', readonly=True)
    order_count = fields.Integer(string='Cobros sin registrar', readonly=True)

    @api.model
    def _pending_commissions(self):
        return self.env['estate.commission'].search([
            ('state', '=', 'paid'), ('payment_id', '=', False), ('amount', '>', 0)])

    @api.model
    def _pending_orders(self):
        orders = self.env['sale.order'].search([('estate_commission_collected', '=', True)])
        return orders.filtered(lambda o: not o.estate_collection_payment_ids.filtered(
            lambda p: p.state != 'canceled'))

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        coms = self._pending_commissions()
        vals['commission_count'] = len(coms.mapped(
            lambda c: (c.user_id.id, c.property_id.id, c.payment_date)))
        vals['order_count'] = len(self._pending_orders())
        return vals

    def action_confirm(self):
        for order in self._pending_orders():
            order._estate_collection_payments()
        self._pending_commissions()._estate_backfill_payment()
        return self.env.ref('estate_management.action_estate_payments_advisor').read()[0]
