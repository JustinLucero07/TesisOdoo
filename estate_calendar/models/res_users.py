# -*- coding: utf-8 -*-
import json
import logging
import os
import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request

from odoo import api, fields, models

from .calendar_event import REMINDER_UNITS, reminder_to_minutes

_logger = logging.getLogger(__name__)

FCM_SCOPES = ['https://www.googleapis.com/auth/firebase.messaging']


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
    fcm_token = fields.Char(
        string='Firebase FCM Token',
        index=True,
        help='Token de registro de Firebase Cloud Messaging para notificaciones push en Android/iOS.')

    @api.depends('whatsapp_reminder_value', 'whatsapp_reminder_unit')
    def _compute_whatsapp_reminder_minutes(self):
        for user in self:
            user.whatsapp_reminder_minutes = reminder_to_minutes(
                user.whatsapp_reminder_value, user.whatsapp_reminder_unit)

    def _get_firebase_credentials_path(self):
        # 1. Busca en la raíz del proyecto o en el módulo
        possible_paths = [
            os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'firebase_credentials.json')),
            os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'firebase_credentials.json')),
            '/opt/inmobi/firebase_credentials.json',
            '/opt/inmobi/addons/firebase_credentials.json',
        ]
        for p in possible_paths:
            if os.path.exists(p):
                return p
        return None

    def send_firebase_push(self, title, body, data=None):
        """Envía una notificación Push a los dispositivos móviles de los usuarios en self."""
        cred_path = self._get_firebase_credentials_path()
        if not cred_path:
            _logger.warning("No se encontró el archivo de credenciales de Firebase (firebase_credentials.json).")
            return False

        try:
            with open(cred_path, 'r', encoding='utf-8') as f:
                cred_json = json.load(f)
            project_id = cred_json.get('project_id')
            if not project_id:
                return False

            credentials = service_account.Credentials.from_service_account_file(
                cred_path, scopes=FCM_SCOPES
            )
            credentials.refresh(Request())
            access_token = credentials.token

            url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; UTF-8",
            }

            for user in self:
                if not user.fcm_token:
                    continue

                payload = {
                    "message": {
                        "token": user.fcm_token,
                        "notification": {
                            "title": title,
                            "body": body,
                        },
                        "android": {
                            "priority": "high",
                            "notification": {
                                "icon": "ic_notification",
                                "color": "#D81F26",
                                "sound": "default",
                                "default_sound": True,
                                "default_vibrate_timings": True,
                            }
                        },
                        "apns": {
                            "payload": {
                                "aps": {
                                    "sound": "default",
                                    "badge": 1,
                                }
                            }
                        },
                        "data": {str(k): str(v) for k, v in (data or {}).items()},
                    }
                }

                resp = requests.post(url, headers=headers, json=payload, timeout=10)
                if resp.status_code == 200:
                    _logger.info("Notificación Push FCM enviada con éxito a usuario %s (ID %s)", user.name, user.id)
                else:
                    _logger.warning("Error al enviar notificación FCM a usuario %s: %s", user.name, resp.text)
            return True
        except Exception as e:
            _logger.error("Error al procesar notificación Firebase FCM: %s", e)
            return False
