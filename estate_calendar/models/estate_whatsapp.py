import logging
import requests
from datetime import timedelta

from odoo import models, fields, api

_logger = logging.getLogger(__name__)

META_API_VERSION = 'v25.0'


class CalendarEventWhatsApp(models.Model):
    _inherit = 'calendar.event'

    def _clean_phone(self, phone):
        """Normaliza número a formato internacional sin + (ej: 593981112222)."""
        clean = phone.replace(' ', '').replace('-', '').replace('+', '').replace('(', '').replace(')', '')
        if clean.startswith('0') and len(clean) == 10:
            clean = '593' + clean[1:]
        elif not clean.startswith('593'):
            clean = '593' + clean
        return clean

    def _send_whatsapp(self, phone, event_name, time_str, client_name, property_name):
        """
        Envía mensaje de WhatsApp usando Meta Cloud API con plantilla aprobada.
        Parámetros de la plantilla: {{1}} cita, {{2}} hora, {{3}} cliente, {{4}} propiedad.
        """
        ICP = self.env['ir.config_parameter'].sudo()
        phone_number_id = ICP.get_param('estate_calendar.whatsapp_phone_number_id', '')
        access_token = ICP.get_param('estate_calendar.whatsapp_access_token', '')
        template_name = ICP.get_param('estate_calendar.whatsapp_template_name', 'recordatorio_cita')

        if not phone_number_id or not access_token:
            _logger.warning('WhatsApp: faltan credenciales Meta Cloud API.')
            return False

        if not phone:
            return False

        clean_phone = self._clean_phone(phone)
        url = f'https://graph.facebook.com/{META_API_VERSION}/{phone_number_id}/messages'
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        }
        payload = {
            'messaging_product': 'whatsapp',
            'to': clean_phone,
            'type': 'template',
            'template': {
                'name': template_name,
                'language': {'code': 'es_EC'},
                'components': [{
                    'type': 'body',
                    'parameters': [
                        {'type': 'text', 'text': event_name},
                        {'type': 'text', 'text': time_str},
                        {'type': 'text', 'text': client_name or 'Sin cliente'},
                        {'type': 'text', 'text': property_name or 'Sin propiedad'},
                    ],
                }],
            },
        }

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            data = resp.json()
            if resp.status_code == 200 and data.get('messages'):
                _logger.info('WhatsApp enviado a %s (cita: %s)', clean_phone, event_name)
                return True
            else:
                _logger.warning('WhatsApp Meta falló (%s): %s', resp.status_code, resp.text[:300])
                return False
        except Exception as e:
            _logger.error('WhatsApp Meta error: %s', e)
            return False

    def _send_whatsapp_text(self, phone, message):
        """
        Envía mensaje de texto libre (solo para contactos que ya te escribieron
        en las últimas 24h — ventana de servicio al cliente de Meta).
        Útil para follow-ups manuales.
        """
        ICP = self.env['ir.config_parameter'].sudo()
        phone_number_id = ICP.get_param('estate_calendar.whatsapp_phone_number_id', '')
        access_token = ICP.get_param('estate_calendar.whatsapp_access_token', '')

        if not phone_number_id or not access_token or not phone:
            return False

        clean_phone = self._clean_phone(phone)
        url = f'https://graph.facebook.com/{META_API_VERSION}/{phone_number_id}/messages'
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        }
        payload = {
            'messaging_product': 'whatsapp',
            'to': clean_phone,
            'type': 'text',
            'text': {'body': message},
        }

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            data = resp.json()
            if resp.status_code == 200 and data.get('messages'):
                _logger.info('WhatsApp texto enviado a %s', clean_phone)
                return True
            _logger.warning('WhatsApp texto falló (%s): %s', resp.status_code, resp.text[:300])
            return False
        except Exception as e:
            _logger.error('WhatsApp texto error: %s', e)
            return False

    @api.model
    def _cron_send_whatsapp_reminders(self):
        """Cron: envía recordatorio 1 hora antes de cada cita con propiedad asignada."""
        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param('estate_calendar.whatsapp_active', 'False') != 'True':
            return

        now = fields.Datetime.now()
        one_hour = now + timedelta(hours=1)

        events = self.search([
            ('start', '>=', now),
            ('start', '<=', one_hour),
            ('whatsapp_sent', '=', False),
            ('property_id', '!=', False),
        ])

        for event in events:
            time_str = fields.Datetime.context_timestamp(self, event.start).strftime('%H:%M')
            client = event.partner_id
            client_name = client.name if client else 'Sin cliente'
            property_name = event.property_id.title if event.property_id else ''
            agent = event.user_id
            agent_name = agent.name if agent else ''

            # Enviar solo al asesor
            agent_partner = agent.partner_id if agent and agent.partner_id else None
            agent_phone = (getattr(agent_partner, 'mobile', None) or getattr(agent_partner, 'phone', None) or '') if agent_partner else ''
            if not agent_phone:
                _logger.warning('Sin teléfono para asesor "%s" — cita "%s" omitida.', agent_name, event.name)
                continue

            if self._send_whatsapp(agent_phone, event.name, time_str, client_name, property_name):
                event.write({'whatsapp_sent': True})
                _logger.info('Recordatorio enviado a asesor %s — cita "%s"', agent_name, event.name)

        _logger.info('Cron WhatsApp: %d evento(s) procesados.', len(events))

    def action_send_whatsapp_followup(self):
        """Botón manual: envía seguimiento post-visita al cliente (texto libre)."""
        self.ensure_one()
        partner = self.partner_id
        phone = (getattr(partner, 'mobile', None) or getattr(partner, 'phone', None) or '') if partner else ''

        if not phone:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Sin teléfono',
                    'message': 'El cliente no tiene número de teléfono registrado.',
                    'type': 'warning',
                },
            }

        property_line = f'\nPropiedad visitada: {self.property_id.title}' if self.property_id else ''
        message = (
            f'Hola {partner.name},\n'
            f'Gracias por su visita.'
            f'{property_line}\n'
            f'Quedamos a su disposición para cualquier consulta.\n'
            f'— Equipo Inmobiliario'
        )

        sent = self._send_whatsapp_text(phone, message)
        self.write({'whatsapp_sent': sent})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'WhatsApp enviado' if sent else 'Error al enviar',
                'message': (
                    f'Mensaje enviado a {partner.name}.' if sent
                    else 'No se pudo enviar. Verifica credenciales Meta o que el cliente haya escrito en las últimas 24h.'
                ),
                'type': 'success' if sent else 'danger',
            },
        }
