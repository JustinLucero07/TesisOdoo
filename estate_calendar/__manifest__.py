{
    'name': 'Agenda Inmobiliaria',
    'version': '19.0.1.0.0',
    'category': 'Real Estate',
    'summary': 'Agenda de citas integrada en el calendario estándar de Odoo',
    'description': """
        Agenda Inmobiliaria
        ===================
        * Integración en el calendario estándar (Google/Outlook sync)
        * Campos para Propiedad y Cliente en citas
        * Seguimiento de Visitas (Resultado y Valoración)
        * Recordatorios WhatsApp automáticos (Meta Cloud API)
    """,
    'author': 'Tesis - Sistema Inmobiliario',
    'license': 'LGPL-3',
    'depends': ['estate_management', 'estate_crm', 'crm', 'calendar'],
    'data': [
        'security/ir.model.access.csv',
        'data/estate_whatsapp_cron.xml',
        'views/calendar_event_views.xml',
        'views/estate_whatsapp_config_views.xml',
        'views/estate_calendar_menus.xml',
    ],
    'demo': [
    ],
    'external_dependencies': {
        'python': ['requests'],
    },
    'installable': True,
    'auto_install': False,
}
