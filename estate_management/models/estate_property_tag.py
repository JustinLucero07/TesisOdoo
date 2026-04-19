from odoo import models, fields


class EstatePropertyTag(models.Model):
    _name = 'estate.property.tag'
    _description = 'Etiqueta de Propiedad'
    _order = 'name'

    name = fields.Char(string='Etiqueta', required=True, translate=True)
    color = fields.Integer(string='Color', default=0)

    _sql_const_name_unique = models.Constraint(
        'unique(name)',
        'Ya existe una etiqueta con este nombre.'
    )
