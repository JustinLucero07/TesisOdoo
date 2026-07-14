# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    birthday = fields.Date(
        string='Fecha de Cumpleaños',
        help='Fecha de nacimiento del cliente (para felicitaciones y campañas).')
