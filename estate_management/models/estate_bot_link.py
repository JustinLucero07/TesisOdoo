import logging
from odoo import models, fields

_logger = logging.getLogger(__name__)

class EstatePropertyBotLink(models.Model):
    _name = 'estate.property.bot.link'
    _description = 'Bot Link for Estate Property'

    url = fields.Char(string='URL del Bot', required=True)
    property_id = fields.Many2one('estate.property', string='Propiedad', required=True, ondelete='cascade')
