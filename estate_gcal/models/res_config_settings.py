# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    gcal_mode = fields.Selection([
        ('none', 'Desactivado'),
        ('native', 'Nativo de Odoo (cada usuario su cuenta de Google)'),
        ('shared', 'Calendario compartido (cuenta de servicio)'),
    ], string='Sincronización de Calendario', default='none',
        config_parameter='estate_gcal.mode',
        help='Cómo se sincronizan las visitas con Google Calendar.')

    gcal_calendar_id = fields.Char(
        string='ID del Calendario compartido',
        config_parameter='estate_gcal.calendar_id',
        help='Ej: equipo@inmobi.com o el ID largo del calendario (Configuración del calendario en Google).')

    gcal_sa_json = fields.Char(
        string='Credenciales de la cuenta de servicio (JSON)',
        config_parameter='estate_gcal.sa_json',
        help='Pega aquí el contenido del archivo JSON de la cuenta de servicio de Google Cloud.')
