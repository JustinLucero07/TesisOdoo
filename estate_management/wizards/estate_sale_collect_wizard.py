# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class EstateSaleCollectWizard(models.TransientModel):
    _name = 'estate.sale.collect.wizard'
    _description = 'Marcar comisión de venta como cobrada'

    order_ids = fields.Many2many('sale.order', string='Ventas')
    date = fields.Date(string='Fecha de cobro', required=True,
                       default=fields.Date.context_today,
                       help='Día en que el propietario pagó la comisión. Para ventas '
                            'antiguas pon la fecha real del cobro.')
    order_count = fields.Integer(compute='_compute_order_count')
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

    @api.depends('order_ids')
    def _compute_order_count(self):
        for wiz in self:
            wiz.order_count = len(wiz.order_ids)
            wiz.amount_total = sum(wiz.order_ids.mapped('amount_total'))

    def action_confirm(self):
        if not self.order_ids:
            raise UserError('No hay ventas por cobrar en la selección (solo cuentan las '
                            'órdenes de venta confirmadas con propiedad y sin cobrar).')
        self.order_ids.write({
            'estate_collected_manual': True,
            'estate_collected_manual_date': self.date,
        })
        for order in self.order_ids:
            order.message_post(body='Comisión marcada como cobrada el %s.'
                               % self.date.strftime('%d/%m/%Y'))
        return {'type': 'ir.actions.act_window_close'}
