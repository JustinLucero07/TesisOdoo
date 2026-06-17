{
    'name': 'Inmobi — Sincronización Google Calendar',
    'version': '19.0.1.0.0',
    'category': 'Real Estate',
    'summary': 'Sincroniza las visitas con Google Calendar (nativo por usuario o calendario compartido)',
    'description': """
        Sincronización de visitas con Google Calendar
        ==============================================
        Dos modos seleccionables en Ajustes:
        * NATIVO (Opción A): cada usuario conecta su cuenta Google (módulo google_calendar de Odoo).
        * COMPARTIDO (Opción B): todas las visitas se empujan a un único calendario del equipo
          mediante una cuenta de servicio de Google Cloud.
    """,
    'author': 'Inmobi Community',
    'license': 'LGPL-3',
    # google_calendar habilita la Opción A (nativa); estate_calendar aporta las visitas
    'depends': ['estate_calendar', 'google_calendar'],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
