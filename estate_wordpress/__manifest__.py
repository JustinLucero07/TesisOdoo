{
    'name': 'Integración WordPress',
    'version': '19.0.1.0.0',
    'category': 'Real Estate',
    'summary': 'Publicación automática de propiedades en WordPress',
    'description': """
        Integración WordPress
        =====================
        * Publicar propiedades automáticamente
        * Sincronización de precio, estado e imágenes
        * Actualización automática
    """,
    'author': 'Tesis - Sistema Inmobiliario',
    'license': 'LGPL-3',
    'depends': ['estate_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/estate_wordpress_config_views.xml',
        'views/estate_wordpress_menus.xml',
        'views/res_users_views.xml',
    ],
    'external_dependencies': {
        'python': ['requests'],
    },
    'installable': True,
    'auto_install': False,
}
