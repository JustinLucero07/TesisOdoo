from odoo import models, fields, api


class EstatePropertyImage(models.Model):
    _name = 'estate.property.image'
    _description = 'Imagen de Propiedad'
    _order = 'sequence, id'

    name = fields.Char(string='Nombre', default='Imagen')
    sequence = fields.Integer(string='Secuencia', default=10)
    image = fields.Binary(string='Imagen', required=True, attachment=True)
    property_id = fields.Many2one(
        'estate.property', string='Propiedad',
        required=True, ondelete='cascade')

    @api.model_create_multi
    def create(self, vals_list):
        for i, vals in enumerate(vals_list):
            if not vals.get('name') or vals.get('name') == 'Imagen':
                # Auto-numerar: busca cuántas imágenes tiene la propiedad
                prop_id = vals.get('property_id')
                if prop_id:
                    count = self.search_count([('property_id', '=', prop_id)])
                    vals['name'] = f'Imagen {count + i + 1}'
                else:
                    vals['name'] = f'Imagen {i + 1}'
        return super().create(vals_list)
