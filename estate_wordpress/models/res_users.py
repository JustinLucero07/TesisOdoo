from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    wp_agent_id = fields.Many2one(
        'estate.wp.agent', string='Agente WordPress (Houzez)',
        help='Selecciona tu perfil equivalente en WordPress para que las propiedades se publiquen a tu nombre.'
    )
