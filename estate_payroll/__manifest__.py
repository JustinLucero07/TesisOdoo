{
    'name': 'Nómina Inmobiliaria',
    'version': '19.0.1.0.0',
    'category': 'Real Estate',
    'summary': 'Gestión de nómina y sueldos para asesores inmobiliarios',
    'description': """
        Módulo de Nómina para Inmobiliaria
        ===================================
        * Registro de nómina mensual por asesor
        * Sueldo base + bonos de comisiones
        * Deducciones (IESS, anticipo, otros)
        * Flujo: Borrador → Confirmado → Pagado
        * Generación automática de factura de proveedor al pagar
    """,
    'author': 'Tesis - Sistema Inmobiliario',
    'license': 'LGPL-3',
    'depends': ['estate_management', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'data/estate_payroll_sequence.xml',
        'views/estate_payroll_views.xml',
        'views/estate_payroll_config_views.xml',
        'views/estate_payroll_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
