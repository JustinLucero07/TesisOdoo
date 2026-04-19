# -*- coding: utf-8 -*-
import urllib.parse
from odoo import models, fields, api, _

class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    whatsapp_followup_sent = fields.Boolean(string='WhatsApp de Seguimiento Enviado', default=False)

    def action_send_whatsapp_followup(self):
        """Manual trigger for WhatsApp follow-up after a visit."""
        self.ensure_one()
        if not self.partner_id or not self.partner_id.mobile:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('El cliente no tiene un número de móvil configurado.'),
                    'type': 'danger',
                    'sticky': False,
                }
            }

        text = self._get_followup_text()
        mobile = self.partner_id.mobile.replace(' ', '').replace('+', '')
        wa_url = f"https://wa.me/{mobile}?text={urllib.parse.quote(text)}"
        
        self.whatsapp_followup_sent = True
        
        return {
            'type': 'ir.actions.act_url',
            'url': wa_url,
            'target': 'new',
        }

    def _get_followup_text(self):
        """Generate a professional follow-up text."""
        self.ensure_one()
        property_title = self.property_id.title if self.property_id else 'la propiedad visitada'
        text = f"""Hola {self.partner_id.name}, 
Gracias por visitar {property_title} el día de hoy. 
¿Qué le pareció la propiedad? ¿Tiene alguna duda adicional que le gustaría aclarar?

Quedo atento a sus comentarios.
Saludos, {self.user_id.name}"""
        return text

    @api.model
    def _cron_whatsapp_followup_reminder(self):
        """Cron to identify visits done today without followup and notify the agent."""
        today = fields.Date.today()
        # Find visits done today where followup is not sent
        visits = self.search([
            ('visit_state', '=', 'done'),
            ('whatsapp_followup_sent', '=', False),
            ('start', '<=', today),
            ('property_id', '!=', False)
        ])
        for visit in visits:
            # Create a notification or log for the agent
            visit.message_post(body=_("Recordatorio: Aún no se ha enviado el WhatsApp de seguimiento para esta visita."))
