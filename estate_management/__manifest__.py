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
    'author': 'Inmobi Community',
    'website': '',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'sale_management', 'account', 'portal', 'calendar', 'hr_attendance'],
    'data': [
        'security/estate_security.xml',
        'security/estate_standard_modules_security.xml',
        'security/ir.model.access.csv',
        'security/standard/ir.model.access.csv',
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
        'data/estate_paperformat.xml',
        'report/estate_contract_report.xml',
        'report/estate_contract_pdf.xml',
        'report/estate_capture_sheet_report.xml',
        'views/estate_sale_views.xml',
        'views/res_partner_views.xml',
        'data/estate_contract_cron.xml',
        'data/estate_mail_templates.xml',
        'wizards/estate_property_comparator_wizard_views.xml',
        'wizards/estate_sale_wizard_views.xml',
        'data/estate_hr_integrations.xml',
        'views/estate_portal_templates.xml',
        'views/estate_advisor_fb_post_views.xml',
        'views/estate_menus.xml',
        'views/estate_access_views.xml',
        'views/res_config_settings_views.xml',
        'views/estate_finance_menu.xml',
        'data/estate_users_roles.xml',
        'data/estate_defaults_fix.xml',
    ],
    'demo': [
        'data/estate_demo_data.xml',
    ],
    'assets': {
        'web._assets_primary_variables': [
            ('prepend', 'estate_management/static/src/scss/primary_variables_override.scss'),
        ],
        'web.assets_backend': [
            'estate_management/static/src/scss/brand_palette.scss',
            'estate_management/static/src/scss/document_pdf_layout.scss',
            'estate_management/static/src/components/**/*',
            'estate_management/static/src/js/estate_auto_geocode.js',
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
