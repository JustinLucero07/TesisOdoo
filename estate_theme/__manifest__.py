# -*- coding: utf-8 -*-
{
    'name': 'Inmobi — Tema visual',
    'version': '19.0.1.0.0',
    'category': 'Hidden/Theme',
    'summary': 'Diseño minimalista y elegante para el backend de Inmobi',
    'description': """
Tema del backend de Odoo para Inmobi: tipografía Inter (fina y legible),
barra superior clara, tarjetas y formularios con más aire, listas más limpias,
botones de acción en tonos suaves y ajustes para celular.

Solo cambia la apariencia (CSS): se puede desinstalar en cualquier momento y
Odoo vuelve a verse como antes.
    """,
    'author': 'Inmobi',
    'license': 'LGPL-3',
    'depends': ['web', 'estate_management'],
    'assets': {
        'web._assets_primary_variables': [
            ('prepend', 'estate_theme/static/src/scss/primary_variables.scss'),
        ],
        'web.assets_backend': [
            'estate_theme/static/src/scss/fonts.scss',
            'estate_theme/static/src/scss/theme.scss',
            'estate_theme/static/src/scss/mobile.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
