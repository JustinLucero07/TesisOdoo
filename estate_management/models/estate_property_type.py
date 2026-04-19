from odoo import models, fields


class EstatePropertyType(models.Model):
    _name = 'estate.property.type'
    _description = 'Tipo de Propiedad'
    _order = 'sequence, name'

    name = fields.Char(string='Nombre', required=True)
    sequence = fields.Integer(string='Secuencia', default=10)
    active = fields.Boolean(string='Activo', default=True)
    property_count = fields.Integer(
        string='Nº Propiedades', compute='_compute_property_count')

    _sql_const_name_uniq = models.Constraint(
        'unique(name)',
        'El tipo de propiedad debe ser único.'
    )

    def _compute_property_count(self):
        for record in self:
            record.property_count = self.env['estate.property'].search_count(
                [('property_type_id', '=', record.id)])
