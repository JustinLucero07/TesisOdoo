# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """La columna Difusión de ventas se calculó al instalarse en
    estate_management sin la fuente del lead; se recalcula con ella."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    orders = env['sale.order'].with_context(active_test=False).search([])
    env.add_to_compute(orders._fields['estate_source'], orders)
    orders._recompute_recordset(['estate_source'])
