import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class MetaWebhookController(http.Controller):
    """
    Webhook universal de Meta (WhatsApp Business, Facebook Messenger, Instagram DMs).

    Un solo endpoint recibe eventos de los tres canales porque Meta usa la misma
    infraestructura de Webhooks de la API Graph para todos.

    Endpoint : /meta/webhook
    Métodos  : GET  → verificación del endpoint (Meta lo llama al configurar)
               POST → recibe los mensajes en tiempo real

    Configuración en developers.facebook.com:
        Tu App → Webhooks → Agregar suscripción:
            URL de devolución de llamada : https://tu-odoo.com/meta/webhook
            Token de verificación        : (el mismo que en Ajustes → estate_crm.meta_verify_token)
        Campos a suscribir:
            - messages          (WhatsApp / Instagram DMs)
            - messaging_postbacks (Facebook Messenger)
    """

    # ─── utilidades ────────────────────────────────────────────────────────────

    def _verify_token(self):
        """Devuelve el token de verificación configurado en parámetros del sistema."""
        return request.env['ir.config_parameter'].sudo().get_param(
            'estate_crm.meta_verify_token', 'mi_token_secreto')

    def _get_or_create_partner(self, env, phone=None, name=None, email=None):
        """Busca un partner existente por teléfono o email; si no existe, lo crea."""
        Partner = env['res.partner'].sudo()
        partner = None
        if phone:
            clean = ''.join(c for c in phone if c.isdigit())
            partner = Partner.search(
                ['|', ('phone', 'ilike', clean), ('mobile', 'ilike', clean)], limit=1)
        if not partner and email:
            partner = Partner.search([('email', '=', email)], limit=1)
        if not partner:
            partner = Partner.create({
                'name': name or phone or 'Sin nombre',
                'phone': phone or False,
                'email': email or False,
            })
        return partner

    def _create_lead(self, env, source, name, phone=None, email=None,
                     message='', sender_id=None):
        """Crea la oportunidad en el CRM evitando duplicados recientes (24 h)."""
        from datetime import datetime, timedelta

        Lead = env['crm.lead'].sudo()

        # Evitar duplicar: si ya existe un lead de este remitente en las últimas 24h
        # con el mismo sender_id (PSID de Facebook / número de WhatsApp) no crear otro.
        if sender_id:
            cutoff = datetime.now() - timedelta(hours=24)
            existing = Lead.search([
                ('description', 'ilike', sender_id),
                ('lead_source', '=', source),
                ('create_date', '>=', cutoff),
            ], limit=1)
            if existing:
                # Agregar el nuevo mensaje al chatter del lead existente
                existing.message_post(
                    body=f'📨 Nuevo mensaje vía {source}: {message}',
                    message_type='comment',
                    subtype_xmlid='mail.mt_note',
                )
                _logger.info('Meta webhook: mensaje agregado a lead existente #%d', existing.id)
                return existing

        partner = self._get_or_create_partner(env, phone=phone, name=name, email=email)

        source_labels = {
            'whatsapp': 'WhatsApp',
            'facebook': 'Facebook Messenger',
            'instagram': 'Instagram DM',
        }
        lead_title = f"Consulta vía {source_labels.get(source, source)} — {name or phone or 'Sin nombre'}"

        lead = Lead.create({
            'name': lead_title,
            'partner_id': partner.id,
            'contact_name': name or False,
            'phone': phone or False,
            'email_from': email or False,
            'type': 'opportunity',
            'lead_source': source,
            'description': (
                f'Sender ID: {sender_id}\n'
                f'Mensaje: {message}'
            ) if sender_id else message,
        })
        _logger.info('Meta webhook: lead #%d creado (fuente=%s, remitente=%s)',
                     lead.id, source, phone or sender_id)
        return lead

    # ─── GET — verificación del endpoint por Meta ───────────────────────────────

    @http.route('/meta/webhook', type='http', auth='public', methods=['GET'], csrf=False)
    def meta_verify(self, **kwargs):
        """
        Meta llama a este endpoint con GET cuando configuras el webhook en tu app.
        Responde con hub.challenge si el token coincide.
        """
        mode      = kwargs.get('hub.mode', '')
        challenge = kwargs.get('hub.challenge', '')
        token     = kwargs.get('hub.verify_token', '')

        if mode == 'subscribe' and token == self._verify_token():
            _logger.info('Meta webhook verificado correctamente.')
            return request.make_response(
                challenge, headers=[('Content-Type', 'text/plain')])

        _logger.warning('Meta webhook: verificación fallida (token incorrecto).')
        return request.make_response('Forbidden', status=403,
                                     headers=[('Content-Type', 'text/plain')])

    # ─── POST — recibe mensajes en tiempo real ──────────────────────────────────

    @http.route('/meta/webhook', type='http', auth='public', methods=['POST'], csrf=False)
    def meta_receive(self, **kwargs):
        """
        Recibe el payload de Meta y lo enruta al handler correcto según el objeto:
            - whatsapp_business_account → WhatsApp
            - page                      → Facebook Messenger
            - instagram                 → Instagram DMs
        """
        try:
            raw  = request.httprequest.data
            data = json.loads(raw) if raw else {}
        except Exception:
            return request.make_json_response({'status': 'error'}, status=400)

        obj = data.get('object', '')

        if obj == 'whatsapp_business_account':
            self._handle_whatsapp(data)
        elif obj == 'page':
            self._handle_facebook(data)
        elif obj == 'instagram':
            self._handle_instagram(data)
        else:
            _logger.debug('Meta webhook: objeto desconocido "%s" — ignorado.', obj)

        # Meta exige siempre 200 OK, aunque no proceses el evento
        return request.make_json_response({'status': 'ok'})

    # ─── Handlers por canal ─────────────────────────────────────────────────────

    def _handle_whatsapp(self, data):
        """
        Procesa mensajes entrantes de WhatsApp Business.
        Payload: entry[].changes[].value.messages[]
        """
        env = request.env
        for entry in data.get('entry', []):
            for change in entry.get('changes', []):
                value    = change.get('value', {})
                messages = value.get('messages', [])
                contacts = value.get('contacts', [])

                for msg in messages:
                    if msg.get('type') != 'text':
                        continue  # Solo texto; ignora audio/imagen por ahora

                    phone = msg.get('from', '')
                    text  = msg.get('text', {}).get('body', '')
                    name  = (contacts[0].get('profile', {}).get('name', '')
                             if contacts else '') or phone

                    self._create_lead(
                        env,
                        source='whatsapp',
                        name=name,
                        phone=phone,
                        message=text,
                        sender_id=phone,
                    )

    def _handle_facebook(self, data):
        """
        Procesa mensajes entrantes de Facebook Messenger.
        Payload: entry[].messaging[].message.text
        """
        env = request.env
        for entry in data.get('entry', []):
            for event in entry.get('messaging', []):
                sender  = event.get('sender', {})
                message = event.get('message', {})

                if not message or message.get('is_echo'):
                    continue  # Ignorar mensajes enviados por la página

                psid = sender.get('id', '')
                text = message.get('text', '')

                # Facebook no da nombre ni teléfono directamente en el webhook;
                # usamos el PSID como identificador.
                self._create_lead(
                    env,
                    source='facebook',
                    name=f'FB-{psid}',
                    message=text,
                    sender_id=psid,
                )

    def _handle_instagram(self, data):
        """
        Procesa Direct Messages entrantes de Instagram Business.
        Payload idéntico a Facebook Messenger pero con objeto 'instagram'.
        """
        env = request.env
        for entry in data.get('entry', []):
            for event in entry.get('messaging', []):
                sender  = event.get('sender', {})
                message = event.get('message', {})

                if not message or message.get('is_echo'):
                    continue

                igsid = sender.get('id', '')
                text  = message.get('text', '')

                self._create_lead(
                    env,
                    source='instagram',
                    name=f'IG-{igsid}',
                    message=text,
                    sender_id=igsid,
                )
