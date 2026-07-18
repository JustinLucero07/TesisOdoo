{
    'name': 'CRM Inmobiliario',
    'version': '19.0.1.0.0',
    'category': 'Real Estate',
    'summary': 'Gestión de clientes inmobiliarios',
    'description': """
        CRM Inmobiliario
        ================
        * Gestión de clientes (compradores, arrendatarios, propietarios)
        * Historial de interacciones
        * Seguimiento de oportunidades
        * Estados del cliente
    """,
    'author': 'Inmobi Community',
    'license': 'LGPL-3',
    'depends': ['crm', 'sales_team', 'estate_management', 'estate_document', 'calendar'],
    'data': [
        'security/ir.model.access.csv',
        'security/estate_crm_security.xml',
        'reports/estate_crm_quotation_report.xml',
        'data/estate_crm_cron.xml',
        'data/estate_lead_source_data.xml',
        'data/estate_lead_source_migrate.xml',
        'views/res_partner_views.xml',
        'views/estate_interaction_views.xml',
        'views/estate_property_match_views.xml',
        'data/estate_allied_fields_migrate.xml',
        'views/estate_lead_source_views.xml',
        'views/estate_crm_lead_views.xml',
        'views/estate_crm_actions.xml',
        'views/estate_crm_menus.xml',
        'data/estate_crm_stage_data.xml',
        'data/estate_crm_postventa_data.xml',
        'data/estate_crm_postventa_migrate.xml',
        'data/estate_crm_postventa_pipeline_domain.xml',
        'data/estate_crm_agent_scope.xml',
        'data/estate_client_import_cron.xml',
        'views/estate_crm_postventa_views.xml',
        'views/estate_crm_lost_views.xml',
        'wizards/estate_client_import_views.xml',
        'views/res_config_settings_views.xml',
        'data/estate_email_templates.xml',
    ],
    'demo': [
        'data/estate_crm_leads_demo.xml',
    ],
    'installable': True,
    'auto_install': False,
}
