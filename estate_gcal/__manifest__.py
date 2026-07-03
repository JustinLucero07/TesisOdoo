{
    'name': 'Inmobi — Sincronización Google Calendar',
    'version': '19.0.1.0.0',
    'category': 'Real Estate',
    'summary': 'Sincroniza las visitas con Google Calendar (nativo por usuario o calendario compartido)',
    'description': """
        Sincronización de visitas con Google Calendar
        ==============================================
        * Modo NATIVO: cada usuario conecta su propia cuenta de Google y sincroniza su calendario personal.
        * Modo COMPARTIDO: todas las visitas se empujan a un único calendario del equipo mediante una cuenta de servicio de Google Cloud.
        * Sincronización bidireccional: cancelar o eliminar una visita en Odoo la borra en Google; eliminarla en Google la marca como Cancelada en Odoo; los cambios de horario se reflejan en ambos sentidos.
        * Cada visita se identifica en Google con el color y las iniciales configurados por asesor, en el formato "(Iniciales) Propiedad / Cliente".
    """,
    'author': 'Inmobi Community',
    'license': 'LGPL-3',
    # google_calendar habilita la Opción A (nativa); estate_calendar aporta las visitas
    'depends': ['estate_calendar', 'google_calendar'],
    'data': [
        'views/res_config_settings_views.xml',
        'views/res_users_views.xml',
        'data/estate_gcal_cron.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
