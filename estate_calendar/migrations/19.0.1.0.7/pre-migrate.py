# -*- coding: utf-8 -*-


def migrate(cr, version):
    """Se retiró la pantalla "Mi día": los usuarios que la tenían como inicio
    vuelven a abrir Odoo como antes (sin pantalla de inicio propia)."""
    cr.execute("""
        UPDATE res_users SET action_id = NULL
         WHERE action_id IN (
               SELECT res_id FROM ir_model_data
                WHERE module = 'estate_calendar' AND name = 'action_estate_my_day')
    """)
