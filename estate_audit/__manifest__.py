{
    'name': 'Inmobi — Registro de Auditoría',
    'version': '19.0.1.0.0',
    'category': 'Real Estate',
    'summary': 'Audit log: quién creó, modificó o eliminó cada registro clave',
    'description': """
        Registro de Auditoría (Audit Log)
        =================================
        Adaptación ligera y nativa para Odoo 19 (inspirado en OCA auditlog).
        Registra automáticamente create/write/unlink de los modelos clave:
        propiedades, contratos, pagos, comisiones, ofertas y leads — con el
        detalle de los campos que cambiaron (valor anterior → nuevo).
    """,
    'author': 'Inmobi Community',
    'license': 'LGPL-3',
    'depends': ['estate_management', 'estate_crm'],
    'data': [
        'security/ir.model.access.csv',
        'views/audit_log_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
