# -*- coding: utf-8 -*-
SPANISH = 'es_EC'


def set_spanish_defaults(env):
    """Español (Ecuador) como idioma por defecto del sistema y de los usuarios
    internos: así la pantalla de ingreso y los mensajes de Odoo salen en
    español y no en inglés."""
    Lang = env['res.lang'].with_context(active_test=False)
    lang = Lang.search([('code', '=', SPANISH)], limit=1)
    if not lang:
        return
    if not lang.active:
        lang.active = True
    env['ir.default'].set('res.partner', 'lang', SPANISH)
    env['res.users'].with_context(active_test=False).search([
        ('share', '=', False), ('lang', '!=', SPANISH),
    ]).write({'lang': SPANISH})


def post_init_hook(env):
    set_spanish_defaults(env)
