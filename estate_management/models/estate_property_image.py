from odoo import models, fields


class EstatePropertyImage(models.Model):
    _name = 'estate.property.image'
    _description = 'Imagen de Propiedad'
    _order = 'sequence, id'

    name = fields.Char(string='Nombre', required=True)
    sequence = fields.Integer(string='Secuencia', default=10)
    image = fields.Binary(string='Imagen', required=True)
    property_id = fields.Many2one(
        'estate.property', string='Propiedad',
        required=True, ondelete='cascade')
