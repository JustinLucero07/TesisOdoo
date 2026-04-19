{
    'name': 'Agente Inteligente Inmobiliario',
    'version': '19.0.1.0.0',
    'category': 'Real Estate',
    'summary': 'Agente conversacional con IA para gestión inmobiliaria',
    'description': """
        Agente Inteligente Inmobiliario
        ===============================
        * Chat conversacional con IA
        * Interpretación de lenguaje natural
        * Consultas inteligentes a la base de datos
        * Generación de reportes por chat
        * Panel de configuración (ChatGPT / Gemini)
    """,
    'author': 'Tesis - Sistema Inmobiliario',
    'license': 'LGPL-3',
    'depends': ['estate_management', 'estate_crm'],
    'data': [
        'security/ir.model.access.csv',
        'security/estate_ai_security.xml',
        'views/estate_ai_config_views.xml',
        'views/estate_ai_chat_views.xml',
        'views/estate_ai_memory_views.xml',
        'views/estate_ai_menus.xml',
        'views/estate_ai_contract_views.xml',
        'views/estate_property_views.xml',
        'data/estate_ai_cron.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'estate_ai_agent/static/src/components/ai_chat_float/ai_chat_float.css',
            'estate_ai_agent/static/src/components/ai_chat/ai_chat.css',
            'estate_ai_agent/static/src/components/**/*.js',
            'estate_ai_agent/static/src/components/**/*.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
}
