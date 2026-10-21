# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Los usuarios internos sin pantalla de inicio propia abren en "Mi día"."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    action = env.ref('estate_calendar.action_estate_my_day', raise_if_not_found=False)
    if action:
        env['res.users'].with_context(active_test=False).search([
            ('share', '=', False), ('action_id', '=', False),
        ]).write({'action_id': action.id})
