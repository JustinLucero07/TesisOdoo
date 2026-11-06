# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """El asesor de la web pasa a ser el captador: las propiedades publicadas
    cuyo captador es distinto del responsable quedan marcadas para volver a
    publicarse con el asesor correcto."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    props = env['estate.property'].search([
        ('wp_published', '=', True), ('state', 'in', ('available', 'reserved')),
        ('exclusive_user_id', '!=', False)])
    props.filtered(lambda p: p.exclusive_user_id != p.user_id).with_context(
        no_wp_sync=True).write({'wp_needs_sync': True})
