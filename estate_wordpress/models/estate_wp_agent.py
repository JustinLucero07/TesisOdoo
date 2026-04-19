from odoo import models, fields

class EstateWpAgent(models.Model):
    _name = 'estate.wp.agent'
    _description = 'Agente WordPress Houzez'

    name = fields.Char(string='Nombre en WordPress', required=True)
    wp_id = fields.Integer(string='ID de WordPress', required=True)
    email = fields.Char(string='Correo (Referencia)')
    
    _wp_id_uniq = models.Constraint(
        'unique (wp_id)', 'El ID de WordPress debe ser único.')
