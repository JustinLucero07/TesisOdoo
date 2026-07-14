# -*- coding: utf-8 -*-
from odoo import api, fields, models

from .calendar_event import REMINDER_UNITS, reminder_to_minutes


class ResUsers(models.Model):
    _inherit = 'res.users'

    whatsapp_reminder_value = fields.Integer(
        string='Recordar antes de',
        help='Con cuánta anticipación quiere este asesor el recordatorio de WhatsApp '
             'de sus citas. 0 = usa el valor general de Configuración > Ajustes > '
             'WhatsApp Citas.')
    whatsapp_reminder_unit = fields.Selection(
        REMINDER_UNITS, string='Unidad', default='minutes')
    whatsapp_reminder_minutes = fields.Integer(
        string='Recordatorio (minutos)', store=True, readonly=True,
        compute='_compute_whatsapp_reminder_minutes',
        help='Equivalente en minutos de la anticipación elegida (uso interno).')

    @api.depends('whatsapp_reminder_value', 'whatsapp_reminder_unit')
    def _compute_whatsapp_reminder_minutes(self):
        for user in self:
            user.whatsapp_reminder_minutes = reminder_to_minutes(
                user.whatsapp_reminder_value, user.whatsapp_reminder_unit)
