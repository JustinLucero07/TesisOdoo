{
    'name': 'Gestión Inmobiliaria',
    'version': '19.0.1.0.0',
    'category': 'Real Estate',
    'summary': 'Módulo base para gestión de propiedades inmobiliarias',
    'description': """
        Sistema de Gestión Inmobiliaria - Módulo Base
        ==============================================
        * Gestión de propiedades (casas, departamentos, terrenos, oficinas)
        * Tipos de propiedad
        * Galería de imágenes
        * Estados de propiedad (disponible, vendido, alquilado, reservado)
        * Roles de seguridad (Agente, Manager, Administrador)
        * Gestión de contratos inmobiliarios
        * Control de pagos por contrato
    """,
    'author': 'Tesis - Sistema Inmobiliario',
    'website': '',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'sale_management', 'account', 'portal', 'calendar', 'hr_attendance'],
    'data': [
        'security/estate_security.xml',
        'security/ir.model.access.csv',
        'data/estate_sequence_data.xml',
        'data/estate_property_type_data.xml',
        'data/res_partner_category_data.xml',
        'views/estate_property_views.xml',
        'views/estate_commission_views.xml',
        'views/estate_property_type_views.xml',
        'views/estate_contract_views.xml',
        'views/estate_offer_views.xml',
        'views/estate_expense_views.xml',
        'views/estate_tenant_views.xml',
        'views/estate_appraisal_views.xml',
        'views/estate_account_views.xml',
        'report/estate_contract_report.xml',
        'views/estate_sale_views.xml',
        'views/res_partner_views.xml',
        'data/estate_contract_cron.xml',
        'data/estate_mail_templates.xml',
        'wizards/estate_property_comparator_wizard_views.xml',
        'data/estate_hr_integrations.xml',
        'views/estate_portal_templates.xml',
        'views/estate_finance_menu.xml',
        'views/estate_menus.xml',
        'data/estate_users_roles.xml',
    ],
    'demo': [
        'data/estate_demo_data.xml',
    ],
    'assets': {
        'web._assets_primary_variables': [
            ('prepend', 'estate_management/static/src/scss/primary_variables_override.scss'),
        ],
        'web.assets_backend': [
            'estate_management/static/src/components/**/*',
        ],
    },
    'installable': True,
    'application': True,
    'external_dependencies': {
        'python': ['requests', 'qrcode', 'python-dateutil'],
    },
    'auto_install': False,
    'sequence': 1,
}
