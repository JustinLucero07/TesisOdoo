# -*- coding: utf-8 -*-
"""Sincronización de visitas a un Google Calendar COMPARTIDO (Opción B).

Usa una cuenta de servicio de Google: cada visita (calendar.event con
property_id) se empuja a un único calendario compartido del equipo.
Robusto: si Google falla, NUNCA rompe la creación/edición de la visita.
"""
import json
import logging
from datetime import timezone

import requests
from odoo import api, fields, models

_logger = logging.getLogger(__name__)

GCAL_SCOPES = ['https://www.googleapis.com/auth/calendar']
GCAL_API = 'https://www.googleapis.com/calendar/v3/calendars'

try:
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request as GoogleAuthRequest
    GAUTH_OK = True
except ImportError:
    GAUTH_OK = False


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    gcal_event_id = fields.Char(
        string='ID Evento Google', copy=False, readonly=True,
        help='ID del evento en el Google Calendar compartido.')

    # ── Configuración ────────────────────────────────────────────────────────
    @api.model
    def _gcal_conf(self):
        ICP = self.env['ir.config_parameter'].sudo()
        return {
            'mode': ICP.get_param('estate_gcal.mode', 'none'),
            'sa_json': ICP.get_param('estate_gcal.sa_json', ''),
            'calendar_id': ICP.get_param('estate_gcal.calendar_id', ''),
        }

    @api.model
    def _gcal_token(self, sa_json):
        """Obtiene un access token desde la cuenta de servicio."""
        info = json.loads(sa_json)
        creds = service_account.Credentials.from_service_account_info(
            info, scopes=GCAL_SCOPES)
        creds.refresh(GoogleAuthRequest())
        return creds.token

    def _gcal_is_visit(self):
        """Solo sincronizamos visitas inmobiliarias (con propiedad)."""
        return bool(self.filtered(lambda e: e.property_id)) if 'property_id' in self._fields else False

    def _gcal_body(self):
        """Construye el cuerpo del evento para Google."""
        self.ensure_one()
        def iso(dt):
            return fields.Datetime.to_datetime(dt).replace(tzinfo=timezone.utc).isoformat()
        prop = self.property_id if 'property_id' in self._fields else False
        asesor = self.user_id.name if self.user_id else ''
        desc = []
        if prop:
            desc.append(f"Propiedad: {prop.title or prop.name}")
            if prop.street or prop.city:
                desc.append(f"Ubicación: {prop.street or ''} {prop.city or ''}".strip())
        cliente = self.client_id if 'client_id' in self._fields else False
        if cliente:
            desc.append(f"Cliente: {cliente.name}")
        elif self.partner_ids:
            desc.append("Cliente(s): " + ", ".join(self.partner_ids.mapped('name')))
        if asesor:
            desc.append(f"Asesor: {asesor}")
        desc.append("— Generado por Inmobi (Odoo)")
        body = {
            'summary': self.name or 'Visita',
            'description': "\n".join(desc),
            'start': {'dateTime': iso(self.start), 'timeZone': 'UTC'},
            'end': {'dateTime': iso(self.stop or self.start), 'timeZone': 'UTC'},
        }
        if prop and (prop.street or prop.city):
            body['location'] = f"{prop.street or ''}, {prop.city or ''}".strip(', ')
        return body

    def _gcal_sync(self):
        """Crea o actualiza el evento en el calendario compartido."""
        conf = self._gcal_conf()
        if conf['mode'] != 'shared' or not GAUTH_OK:
            return
        if not conf['sa_json'] or not conf['calendar_id']:
            return
        try:
            token = self._gcal_token(conf['sa_json'])
            headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
            cal = conf['calendar_id']
            for ev in self.filtered(lambda e: e.property_id and e.start):
                body = ev._gcal_body()
                if ev.gcal_event_id:
                    r = requests.patch(f"{GCAL_API}/{cal}/events/{ev.gcal_event_id}",
                                       headers=headers, json=body, timeout=20)
                    if r.status_code == 404:  # se borró en Google → recrear
                        ev.gcal_event_id = False
                if not ev.gcal_event_id:
                    r = requests.post(f"{GCAL_API}/{cal}/events",
                                      headers=headers, json=body, timeout=20)
                    if r.ok:
                        ev.with_context(gcal_skip=True).gcal_event_id = r.json().get('id')
                if not r.ok:
                    _logger.warning("Google Calendar push %s: %s", r.status_code, r.text[:200])
        except Exception as e:
            _logger.warning("Google Calendar sync falló: %s", e)

    def _gcal_remove(self):
        conf = self._gcal_conf()
        if conf['mode'] != 'shared' or not GAUTH_OK or not conf['sa_json']:
            return
        try:
            token = self._gcal_token(conf['sa_json'])
            headers = {'Authorization': f'Bearer {token}'}
            cal = conf['calendar_id']
            for ev in self.filtered(lambda e: e.gcal_event_id):
                requests.delete(f"{GCAL_API}/{cal}/events/{ev.gcal_event_id}",
                                headers=headers, timeout=20)
        except Exception as e:
            _logger.warning("Google Calendar delete falló: %s", e)

    # ── Hooks ────────────────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        events = super().create(vals_list)
        events._gcal_sync()
        return events

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get('gcal_skip') and vals.keys() - {'gcal_event_id'}:
            self._gcal_sync()
        return res

    def unlink(self):
        self._gcal_remove()
        return super().unlink()
