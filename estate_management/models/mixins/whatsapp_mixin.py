import logging

from odoo import models

from ...tools.http_retry import request_with_retry

_logger = logging.getLogger(__name__)

# Versión de la API de Meta usada por defecto. Se puede cambiar sin tocar el
# código con el parámetro de sistema `estate.whatsapp_api_version`.
DEFAULT_META_API_VERSION = 'v25.0'


class EstateWhatsAppMixin(models.AbstractModel):
    """Único punto de envío de WhatsApp (Meta Cloud API) de todo el sistema.

    Citas, recordatorios, contratos y pagos vencidos usan estos métodos, así la
    versión de la API, las credenciales y el manejo de errores están en un solo
    lugar. Devuelven `(enviado, motivo)`.
    """
    _name = 'estate.whatsapp.mixin'
    _inherit = 'estate.phone.mixin'
    _description = 'Envío de WhatsApp (Meta Cloud API)'

    def _wa_config(self):
        ICP = self.env['ir.config_parameter'].sudo()
        return {
            'active': ICP.get_param('estate_calendar.whatsapp_active', 'False') == 'True',
            'phone_number_id': ICP.get_param('estate_calendar.whatsapp_phone_number_id', ''),
            'token': ICP.get_param('estate_calendar.whatsapp_access_token', ''),
            'version': ICP.get_param('estate.whatsapp_api_version', DEFAULT_META_API_VERSION)
                       or DEFAULT_META_API_VERSION,
        }

    def _wa_post(self, phone, payload_extra, require_active=True):
        cfg = self._wa_config()
        if require_active and not cfg['active']:
            return False, 'la integración de WhatsApp está desactivada en Ajustes.'
        if not cfg['phone_number_id'] or not cfg['token']:
            return False, 'faltan las credenciales de Meta en Ajustes → WhatsApp.'
        if not phone:
            return False, 'no hay número de teléfono.'
        payload = {'messaging_product': 'whatsapp', 'to': self._clean_phone(phone)}
        payload.update(payload_extra)
        url = 'https://graph.facebook.com/%s/%s/messages' % (cfg['version'], cfg['phone_number_id'])
        try:
            resp = request_with_retry('POST', url, json=payload, timeout=30, headers={
                'Authorization': 'Bearer %s' % cfg['token'],
                'Content-Type': 'application/json',
            })
            data = resp.json()
        except Exception as e:
            _logger.error('WhatsApp: error de conexión con Meta: %s', e)
            return False, 'error de conexión con Meta.'
        if resp.status_code == 200 and data.get('messages'):
            _logger.info('WhatsApp enviado a %s', payload['to'])
            return True, ''
        error = (data.get('error') or {}).get('message') or resp.text[:200]
        _logger.warning('WhatsApp falló (%s): %s', resp.status_code, error)
        return False, 'Meta respondió: %s' % error

    def _wa_send_template(self, phone, template, params, lang='es', require_active=True):
        """Envía una plantilla aprobada. `params` son los textos {{1}}, {{2}}…"""
        # Meta no acepta saltos de línea ni variables vacías.
        clean = [' '.join(str(p or '-').split())[:900] or '-' for p in params]
        return self._wa_post(phone, {
            'type': 'template',
            'template': {
                'name': template,
                'language': {'code': lang or 'es'},
                'components': [{
                    'type': 'body',
                    'parameters': [{'type': 'text', 'text': p} for p in clean],
                }],
            },
        }, require_active=require_active)

    def _wa_send_text(self, phone, message, require_active=True):
        """Texto libre: solo llega si el contacto escribió en las últimas 24 h."""
        return self._wa_post(phone, {'type': 'text', 'text': {'body': message}},
                             require_active=require_active)
