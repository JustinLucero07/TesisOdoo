{
    'name': 'Reportes Inmobiliarios',
    'version': '19.0.1.0.0',
    'category': 'Real Estate',
    'summary': 'Dashboard y reportes del sistema inmobiliario',
    'description': """
        Reportes Inmobiliarios
        ======================
        * Dashboard con KPIs
        * Reportes PDF
        * Exportación Excel
        * Gráficos dinámicos
    """,
    'author': 'Tesis - Sistema Inmobiliario',
    'license': 'LGPL-3',
    'depends': ['estate_management', 'estate_crm'],
    'data': [
        'security/ir.model.access.csv',
        'data/estate_reports_cron.xml',
        'reports/estate_report_templates.xml',
        'reports/estate_commission_report.xml',
        'reports/estate_owner_report.xml',
        'wizards/estate_report_wizard_views.xml',
        'wizards/estate_commission_wizard_views.xml',
        'views/estate_dashboard_views.xml',
        'views/estate_visitor_report_views.xml',
        'views/estate_analytics_views.xml',
        'views/estate_reports_menus.xml',
    ],
    'installable': True,
    'auto_install': False,
}
