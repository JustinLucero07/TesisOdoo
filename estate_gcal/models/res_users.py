# -*- coding: utf-8 -*-
from odoo import fields, models

# Colores de evento disponibles en Google Calendar (colorId 1-11).
GCAL_COLORS = [
    ('1', 'Lavanda'), ('2', 'Salvia'), ('3', 'Uva'), ('4', 'Flamenco'),
    ('5', 'Plátano'), ('6', 'Mandarina'), ('7', 'Pavo Real'), ('8', 'Grafito'),
    ('9', 'Arándano'), ('10', 'Albahaca'), ('11', 'Tomate'),
]


class ResUsers(models.Model):
    _inherit = 'res.users'

    gcal_initials = fields.Char(
        string='Iniciales (Google Calendar)', size=4,
        help='Código corto que identifica al asesor en los eventos del calendario '
             'compartido de Google (ej. RM, EP, CR). Aparece como "(RM) Propiedad / Cliente".')
    gcal_color_id = fields.Selection(
        GCAL_COLORS, string='Color (Google Calendar)',
        help='Color con el que se pintan en Google Calendar las visitas de este asesor.')
