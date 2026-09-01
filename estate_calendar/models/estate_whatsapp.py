import logging
from datetime import timedelta

from odoo import models, fields, api
from odoo.addons.estate_management.tools.http_retry import request_with_retry

_logger = logging.getLogger(__name__)

META_API_VERSION = 'v25.0'

# Margen de gracia: si un tick del cron se salta la ventana exacta de una cita
# (recordatorio corto + intervalo del cron), igual la recupera en el siguiente
# tick en lugar de perderla para siempre (antes el filtro `start >= now` la
# sacaba de la búsqueda apenas la cita quedaba en el pasado).
_REMINDER_GRACE_MINUTES = 180


class CalendarEventWhatsApp(models.Model):
    _inherit = 'calendar.event'
    # _clean_phone() heredado de estate.phone.mixin (aplicado en calendar_event.py)

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
            resp = request_with_retry('POST', url, json=payload, headers=headers, timeout=30)
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
            resp = request_with_retry('POST', url, json=payload, headers=headers, timeout=30)
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
        """Cron: envía el recordatorio de cada cita con la anticipación efectiva
        (configurada en la propia cita, o la del asesor, o la general)."""
        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param('estate_calendar.whatsapp_active', 'False') != 'True':
            return

        default_minutes = self._global_reminder_minutes()
        now = fields.Datetime.now()
        # Ventana amplia de búsqueda: cubre el mayor tiempo de anticipación posible
        # (el general, el de cualquier asesor, o el de cualquier cita próxima).
        advisor_minutes = self.env['res.users'].sudo().search(
            [('whatsapp_reminder_minutes', '>', 0)]).mapped('whatsapp_reminder_minutes')
        upcoming = self.search([
            ('start', '>=', now), ('whatsapp_sent', '=', False),
            ('property_id', '!=', False), ('whatsapp_reminder_minutes', '>', 0),
        ])
        event_minutes = upcoming.mapped('whatsapp_reminder_minutes')
        max_minutes = max([default_minutes] + advisor_minutes + event_minutes)

        events = self.search([
            ('start', '>=', now - timedelta(minutes=_REMINDER_GRACE_MINUTES)),
            ('start', '<=', now + timedelta(minutes=max_minutes)),
            ('whatsapp_sent', '=', False),
            ('property_id', '!=', False),
        ])

        notify_client = ICP.get_param('estate_calendar.whatsapp_notify_client', 'True') == 'True'
        processed = 0

        for event in events:
            reminder_minutes = event._effective_reminder_minutes()
            if event.start > now + timedelta(minutes=reminder_minutes):
                continue  # aún no toca avisar esta cita
            processed += 1
            time_str = event._format_local_time(event.start)
            client = event.client_id
            client_name = client.name if client else 'Sin cliente'
            property_name = event.property_id.title if event.property_id else ''
            agent = event.user_id
            agent_name = agent.name if agent else ''
            sent_any = False

            # Recordatorio al asesor
            agent_partner = agent.partner_id if agent and agent.partner_id else None
            agent_phone = (getattr(agent_partner, 'mobile', None) or getattr(agent_partner, 'phone', None) or '') if agent_partner else ''
            if agent_phone:
                if self._send_whatsapp(agent_phone, event.name, time_str, client_name, property_name):
                    sent_any = True
                    _logger.info('Recordatorio enviado a asesor %s — cita "%s"', agent_name, event.name)
            else:
                _logger.warning('Sin teléfono para asesor "%s" — cita "%s".', agent_name, event.name)

            # Recordatorio al cliente (si está habilitado y tiene teléfono)
            if notify_client and client:
                client_phone = getattr(client, 'mobile', None) or getattr(client, 'phone', None) or ''
                if client_phone:
                    if self._send_whatsapp(client_phone, event.name, time_str, client_name, property_name):
                        sent_any = True
                        _logger.info('Recordatorio enviado a cliente %s — cita "%s"', client_name, event.name)

            if sent_any:
                event.write({'whatsapp_sent': True})

        _logger.info('Cron WhatsApp: %d evento(s) procesados.', processed)

    def action_send_reminder_now(self):
        """Botón manual: envía YA el recordatorio de esta cita, sin esperar al
        cron. Reutiliza la misma plantilla y destinatarios (asesor + cliente)
        que el envío automático; se expone como método público para poder
        dispararlo desde la app móvil.

        Devuelve un dict con `sent` (cuántos envíos salieron) y `detail`, para
        que quien lo llame pueda dar un mensaje concreto al usuario."""
        self.ensure_one()
        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param('estate_calendar.whatsapp_active', 'False') != 'True':
            return {'sent': 0, 'detail': 'La integración de WhatsApp está desactivada en Ajustes.'}

        time_str = self._format_local_time(self.start)
        client = self.client_id
        client_name = client.name if client else 'Sin cliente'
        property_name = self.property_id.title if self.property_id else ''
        agent = self.user_id

        sent = 0
        destinos = []

        agent_partner = agent.partner_id if agent and agent.partner_id else None
        agent_phone = (getattr(agent_partner, 'mobile', None)
                       or getattr(agent_partner, 'phone', None) or '') if agent_partner else ''
        if agent_phone and self._send_whatsapp(agent_phone, self.name, time_str, client_name, property_name):
            sent += 1
            destinos.append('asesor')

        notify_client = ICP.get_param('estate_calendar.whatsapp_notify_client', 'True') == 'True'
        if notify_client and client:
            client_phone = getattr(client, 'mobile', None) or getattr(client, 'phone', None) or ''
            if client_phone and self._send_whatsapp(client_phone, self.name, time_str, client_name, property_name):
                sent += 1
                destinos.append('cliente')

        if sent:
            self.write({'whatsapp_sent': True})
            return {'sent': sent, 'detail': 'Recordatorio enviado a: %s.' % ' y '.join(destinos)}
        return {'sent': 0, 'detail': 'No se pudo enviar: revisa que el asesor o el cliente tengan teléfono.'}

    def action_send_whatsapp_followup(self):
        """Botón manual: envía seguimiento post-visita al cliente (texto libre)."""
        self.ensure_one()
        partner = self.client_id
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
