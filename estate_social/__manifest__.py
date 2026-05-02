{
    'name': 'Redes Sociales Inmobiliaria',
    'version': '19.0.1.0.0',
    'category': 'Real Estate',
    'summary': 'Compartir propiedades en redes sociales',
    'description': """
        Redes Sociales Inmobiliaria
        ===========================
        * Compartir propiedades en Facebook
        * Compartir propiedades en Instagram
        * Generación de URLs para compartir
    """,
    'author': 'Tesis - Sistema Inmobiliario',
    'license': 'LGPL-3',
    'depends': ['estate_management', 'calendar'],
    'data': [
        'security/ir.model.access.csv',
        'data/estate_social_cron.xml',
        'views/estate_social_views.xml',
        'views/estate_social_config_views.xml',
        'views/estate_instagram_stats_views.xml',
        'views/estate_facebook_stats_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'estate_social/static/src/components/fb_insights_dashboard/fb_insights_dashboard.scss',
            'estate_social/static/src/components/fb_insights_dashboard/fb_insights_dashboard.js',
            'estate_social/static/src/components/fb_insights_dashboard/fb_insights_dashboard.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
}
