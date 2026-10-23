# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """El cobro ahora es solo manual: se recalcula el estado de todas las
    ventas. Las que estaban "Cobradas" solo por tener la factura pagada vuelven
    a "Por cobrar"; las marcadas a mano se quedan como estaban."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    orders = env['sale.order'].with_context(active_test=False).search([])
    for fname in ('estate_commission_collected', 'estate_collection_state', 'estate_collected_date',
                  'estate_collected_method', 'estate_collected_invoice'):
        env.add_to_compute(orders._fields[fname], orders)
    orders.flush_recordset()
