# -*- coding: utf-8 -*-
"""Sincronización BIDIRECCIONAL de visitas con un Google Calendar COMPARTIDO.

Odoo -> Google: cada visita (calendar.event con property_id) se crea/actualiza
en el calendario compartido; al cancelarse o eliminarse en Odoo, se borra en
Google. El evento se pinta con el color del asesor y su título sigue el
formato "(Iniciales) Propiedad / Cliente".

Google -> Odoo: una tarea programada (_cron_gcal_pull) revisa periódicamente
los cambios en Google mediante un "sync token" incremental. Si una visita se
elimina directamente en Google, se marca como Cancelada en Odoo (no se borra,
para no perder el historial ante un borrado accidental). Si se reprograma el
horario en Google, se refleja en Odoo.

Robusto: si Google falla, NUNCA rompe la creación/edición de la visita.
"""
import json
import logging
from datetime import datetime, timedelta, timezone

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

    # ── Formato del evento (título con iniciales + color por asesor) ────────
    def _gcal_advisor_initials(self):
        self.ensure_one()
        advisor = self.user_id
        if not advisor:
            return ''
        initials = (advisor.gcal_initials or '').strip()
        if initials:
            return initials
        parts = (advisor.name or '').split()
        return ''.join(p[0] for p in parts[:2]).upper()

    def _gcal_body(self):
        """Construye el cuerpo del evento para Google."""
        self.ensure_one()

        def iso(dt):
            return fields.Datetime.to_datetime(dt).replace(tzinfo=timezone.utc).isoformat()

        prop = self.property_id if 'property_id' in self._fields else False
        cliente = self.client_id if 'client_id' in self._fields else False
        advisor = self.user_id

        initials = self._gcal_advisor_initials()
        prop_label = (prop.title or prop.name) if prop else (self.name or 'Visita')
        client_label = cliente.name if cliente else (
            ", ".join(self.partner_ids.mapped('name')) if self.partner_ids else '')

        title = f"({initials}) {prop_label}" if initials else prop_label
        if client_label:
            title = f"{title} / {client_label}"

        desc = []
        if prop:
            desc.append(f"Propiedad: {prop.title or prop.name}")
            if prop.street or prop.city:
                desc.append(f"Ubicación: {prop.street or ''} {prop.city or ''}".strip())
        if client_label:
            desc.append(f"Cliente: {client_label}")
        if advisor:
            desc.append(f"Asesor: {advisor.name}")
        desc.append("— Generado por Inmobi (Odoo)")

        body = {
            'summary': title,
            'description': "\n".join(desc),
            'start': {'dateTime': iso(self.start), 'timeZone': 'UTC'},
            'end': {'dateTime': iso(self.stop or self.start), 'timeZone': 'UTC'},
        }
        if advisor and advisor.gcal_color_id:
            body['colorId'] = advisor.gcal_color_id
        if prop and (prop.street or prop.city):
            body['location'] = f"{prop.street or ''}, {prop.city or ''}".strip(', ')
        return body

    # ── Odoo -> Google ───────────────────────────────────────────────────────
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
            # Las visitas canceladas no se sincronizan (si ya estaban en Google, se retiran aparte).
            for ev in self.filtered(lambda e: e.property_id and e.start and e.visit_state != 'cancelled'):
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
        """Elimina el evento en Google (usado al cancelar/eliminar en Odoo)."""
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
                ev.with_context(gcal_skip=True).gcal_event_id = False
        except Exception as e:
            _logger.warning("Google Calendar delete falló: %s", e)

    # ── Google -> Odoo (revisión periódica, sin webhooks) ───────────────────
    def _gcal_fetch_changes(self, token, calendar_id, sync_token):
        """Lista los cambios del calendario desde el último sync token.

        Aislado en su propio método para poder simularlo (mock) en pruebas.
        Devuelve (eventos, nuevo_sync_token).
        """
        headers = {'Authorization': f'Bearer {token}'}
        events = []
        page_token = None
        next_sync_token = None
        while True:
            params = {'singleEvents': 'true', 'showDeleted': 'true', 'maxResults': 250}
            if sync_token:
                params['syncToken'] = sync_token
            else:
                # Primera sincronización: no traer todo el historial, solo lo reciente.
                params['timeMin'] = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
            if page_token:
                params['pageToken'] = page_token
            r = requests.get(f"{GCAL_API}/{calendar_id}/events",
                             headers=headers, params=params, timeout=20)
            r.raise_for_status()
            data = r.json()
            events.extend(data.get('items', []))
            page_token = data.get('nextPageToken')
            next_sync_token = data.get('nextSyncToken', next_sync_token)
            if not page_token:
                break
        return events, next_sync_token

    @api.model
    def _cron_gcal_pull(self):
        """Revisa Google Calendar en busca de cambios y los refleja en Odoo.

        Si una visita se eliminó en Google, se marca como Cancelada (no se
        borra, para no perder historial). Si cambió el horario, se actualiza.
        """
        conf = self._gcal_conf()
        if conf['mode'] != 'shared' or not GAUTH_OK or not conf['sa_json'] or not conf['calendar_id']:
            return
        ICP = self.env['ir.config_parameter'].sudo()
        sync_token = ICP.get_param('estate_gcal.sync_token', '') or None
        try:
            token = self._gcal_token(conf['sa_json'])
            events, next_sync_token = self._gcal_fetch_changes(token, conf['calendar_id'], sync_token)
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 410:
                _logger.warning("Google Calendar: sync token expirado; se hará sincronización completa la próxima vez.")
                ICP.set_param('estate_gcal.sync_token', '')
            else:
                _logger.warning("Google Calendar pull falló: %s", e)
            return
        except Exception as e:
            _logger.warning("Google Calendar pull falló: %s", e)
            return

        cancelled = 0
        for gev in events:
            gid = gev.get('id')
            if not gid:
                continue
            local = self.sudo().search([('gcal_event_id', '=', gid)], limit=1)
            if not local:
                continue  # evento del calendario ajeno a Odoo (no lo tocamos)

            if gev.get('status') == 'cancelled':
                if local.visit_state != 'cancelled':
                    local.with_context(gcal_skip=True).write(
                        {'visit_state': 'cancelled', 'gcal_event_id': False})
                    local.message_post(
                        body='La visita fue eliminada en Google Calendar y se marcó como Cancelada.')
                    cancelled += 1
                continue

            # Reprogramación hecha directamente en Google: reflejarla en Odoo.
            vals = {}
            g_start = gev.get('start', {}).get('dateTime')
            g_end = gev.get('end', {}).get('dateTime')
            if g_start:
                new_start = datetime.fromisoformat(g_start).astimezone(timezone.utc).replace(tzinfo=None)
                if not local.start or abs((new_start - local.start).total_seconds()) >= 60:
                    vals['start'] = new_start
            if g_end:
                new_stop = datetime.fromisoformat(g_end).astimezone(timezone.utc).replace(tzinfo=None)
                if not local.stop or abs((new_stop - local.stop).total_seconds()) >= 60:
                    vals['stop'] = new_stop
            if vals:
                local.with_context(gcal_skip=True).write(vals)

        if next_sync_token:
            ICP.set_param('estate_gcal.sync_token', next_sync_token)
        if cancelled:
            _logger.info("Google Calendar pull: %d visita(s) marcadas como Cancelada.", cancelled)

    # ── Hooks ────────────────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        events = super().create(vals_list)
        events._gcal_sync()
        return events

    def write(self, vals):
        res = super().write(vals)
        if self.env.context.get('gcal_skip'):
            return res
        if vals.get('visit_state') == 'cancelled':
            self._gcal_remove()
        elif vals.keys() - {'gcal_event_id'}:
            self._gcal_sync()
        return res

    def unlink(self):
        self._gcal_remove()
        return super().unlink()
