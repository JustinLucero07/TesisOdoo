{
    'name': 'Web Responsive',
    'version': '19.0.1.0.0',
    'summary': 'Fullscreen app drawer, backend responsive para móviles y tablets',
    'category': 'Web',
    'author': 'Inmobi / Tesis',
    'depends': ['web'],
    'assets': {
        'web.assets_backend': [
            'web_responsive/static/src/web_responsive.scss',
            'web_responsive/static/src/navbar_patch.js',
            'web_responsive/static/src/navbar_patch.xml',
            'web_responsive/static/src/web_responsive.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
