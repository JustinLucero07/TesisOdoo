# -*- coding: utf-8 -*-
from odoo import fields, models


class CrmStage(models.Model):
    _inherit = 'crm.stage'

    is_lost = fields.Boolean(
        string='¿Es Etapa Perdida?',
        help='Marca la etapa "Perdido". Odoo de fábrica archiva los leads perdidos '
             '(y por eso desaparecen del embudo). Con esta marca, el lead perdido '
             'se queda VISIBLE en su columna, pero sigue contando como "Perdido" '
             'en los filtros y reportes.')
