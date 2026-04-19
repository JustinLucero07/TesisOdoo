{
    'name': 'Documentos Inmobiliarios',
    'version': '19.0.1.0.0',
    'category': 'Real Estate',
    'summary': 'Gestión de documentos legales y adjuntos',
    'description': """
        Documentos Inmobiliarios
        ========================
        * Contratos escaneados
        * Documentos legales
        * Archivos adjuntos vinculados a propiedades, clientes y contratos
    """,
    'author': 'Tesis - Sistema Inmobiliario',
    'license': 'LGPL-3',
    'depends': ['estate_management', 'crm'],
    'data': [
        'security/ir.model.access.csv',
        'security/estate_document_security.xml',
        'views/estate_document_views.xml',
        'views/estate_document_menus.xml',
    ],
    'installable': True,
    'auto_install': False,
}
