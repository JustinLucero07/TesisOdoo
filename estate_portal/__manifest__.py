{
    'name': 'Portal de Propietarios',
    'version': '19.0.1.0.0',
    'category': 'Real Estate',
    'summary': 'Extranet para que los dueños de inmuebles vean el estado y visitas de sus propiedades.',
    'description': """
        Portal de Propietarios (Extranet)
        =================================
        * Agrega un panel en Mi Cuenta (Odoo Portal) para los clientes propietarios.
        * Vista de lista de propiedades activas del dueño.
        * Vista de detalle con métricas (días en el mercado, precio AVM, número de citas agendadas).
    """,
    'author': 'Tesis - Sistema Inmobiliario',
    'license': 'LGPL-3',
    'depends': ['portal', 'estate_management', 'estate_calendar', 'estate_crm'],
    'data': [
        'views/portal_templates.xml',
    ],
    'installable': True,
    'auto_install': False,
}
