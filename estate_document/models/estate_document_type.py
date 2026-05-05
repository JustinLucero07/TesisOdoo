from odoo import models, fields


CATEGORY_SELECTION = [
    ('contract', 'Contrato'),
    ('identity', 'Identidad'),
    ('property', 'Propiedad'),
    ('financial', 'Financiero'),
    ('legal', 'Legal'),
    ('other', 'Otro'),
]


class EstateDocumentType(models.Model):
    """Catálogo de tipos de documento inmobiliario.
    Reemplaza al Selection antiguo de 6 valores con un modelo configurable
    que admite ~25+ tipos agrupados por categoría con icono y color.
    """
    _name = 'estate.document.type'
    _description = 'Tipo de Documento Inmobiliario'
    _order = 'category, sequence, name'

    name = fields.Char(string='Nombre', required=True, translate=True)
    code = fields.Char(
        string='Código', required=True, copy=False,
        help='Código único usado por integraciones automáticas (ej: contract_signed).')
    category = fields.Selection(
        CATEGORY_SELECTION, string='Categoría', required=True, default='other',
        help='Agrupación visual del tipo en kanbans y filtros.')
    sequence = fields.Integer(string='Orden', default=10)
    icon = fields.Char(
        string='Ícono FontAwesome', default='fa-file-text-o',
        help='Clase de ícono FontAwesome (ej: fa-file-pdf-o).')
    color = fields.Integer(string='Color del tag', default=0)
    description = fields.Text(string='Descripción')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'El código de tipo de documento debe ser único.'),
    ]
