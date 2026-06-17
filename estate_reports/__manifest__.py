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
    'author': 'Inmobi Community',
    'license': 'LGPL-3',
    'depends': ['estate_management', 'estate_crm', 'board'],
    'data': [
        'security/ir.model.access.csv',
        'data/estate_reports_cron.xml',
        'reports/estate_report_templates.xml',
        'reports/estate_dashboard_report.xml',
        'reports/estate_negocio_cerrado_report.xml',
        'reports/estate_commission_report.xml',
        'reports/estate_owner_report.xml',
        'reports/estate_avg_sales_report.xml',
        'wizards/estate_report_wizard_views.xml',
        'wizards/estate_commission_wizard_views.xml',
        'wizards/estate_sales_report_wizard_views.xml',
        'views/estate_property_report_button.xml',
        'views/estate_dashboard_views.xml',
        'views/estate_sales_target_views.xml',
        'views/estate_visitor_report_views.xml',
        'views/estate_analytics_views.xml',
        'views/estate_sales_analytics_views.xml',
        'views/estate_reports_menus.xml',
        'data/estate_board_reset.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'estate_reports/static/src/css/estate_dashboard.scss',
            'estate_reports/static/src/js/estate_dashboard.js',
            'estate_reports/static/src/components/**/*.js',
            'estate_reports/static/src/components/**/*.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
}
