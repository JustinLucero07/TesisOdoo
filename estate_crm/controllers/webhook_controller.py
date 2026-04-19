# -*- coding: utf-8 -*-
import json
import logging
import hmac
import hashlib

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class EstateLeadWebhookController(http.Controller):
    """
    Webhook receptor universal de leads.
    Acepta peticiones desde: WordPress, WhatsApp Business API,
    Instagram, Google Business, formularios externos, etc.

    Endpoint: POST /estate/webhook/lead
    Auth:     token en header X-Estate-Token o en query param ?token=

    Ejemplo WordPress (plugin Contact Form 7 + CF7 to Webhook):
        URL: https://tu-odoo.com/estate/webhook/lead
        Body (JSON):
        {
            "source": "wordpress",
            "name": "Juan Pérez",
            "email": "juan@email.com",
            "phone": "0991234567",
            "message": "Quiero información sobre la casa en Cuenca",
            "budget": "85000",
            "property_type": "casa"
        }
    """

    def _get_webhook_token(self):
        """Lee el token de seguridad configurado en Ajustes > Parámetros."""
        return request.env['ir.config_parameter'].sudo().get_param(
            'estate_crm.webhook_token', '')

    def _verify_token(self, req_token):
        """Verifica que el token del request coincide con el configurado."""
        configured = self._get_webhook_token()
        if not configured:
            return True  # Sin token configurado → acceso libre (desarrollo)
        return hmac.compare_digest(str(configured), str(req_token or ''))

    @http.route(
        '/estate/webhook/lead',
        type='http', auth='public', methods=['POST'], csrf=False,
    )
    def receive_lead(self, **kwargs):
        """
        Endpoint principal. Acepta JSON en el body o form-encoded.
        Devuelve JSON con el resultado.
        """
        # Parsear body
        try:
            raw = request.httprequest.data
            data = json.loads(raw) if raw else {}
        except Exception:
            data = {}

        # También acepta form-encoded
        if not data:
            data = dict(kwargs)

        # Verificar token de seguridad
        token = (
            request.httprequest.headers.get('X-Estate-Token')
            or data.get('token')
            or request.httprequest.args.get('token', '')
        )
        if not self._verify_token(token):
            _logger.warning("Webhook lead: token inválido desde %s",
                            request.httprequest.remote_addr)
            return request.make_json_response(
                {'error': 'Token inválido'}, status=403)

        source = data.get('source', 'website')
        name = (data.get('name') or data.get('contact_name') or '').strip()
        email = (data.get('email') or data.get('email_from') or '').strip()
        phone = (data.get('phone') or data.get('mobile') or '').strip()
        message = (data.get('message') or data.get('description') or '').strip()
        subject = (data.get('subject') or data.get('lead_name') or '').strip()
        budget = data.get('budget') or data.get('client_budget')
        property_type = (data.get('property_type') or '').strip()
        city = (data.get('city') or data.get('preferred_city') or '').strip()
        bedrooms = data.get('bedrooms') or data.get('preferred_bedrooms')
        referral_code = (data.get('referral_code') or '').strip()

        if not name and not email and not phone:
            return request.make_json_response(
                {'error': 'Se requiere al menos nombre, email o teléfono'}, status=400)

        env = request.env

        # Buscar o crear partner
        partner = None
        if email:
            partner = env['res.partner'].sudo().search(
                [('email', '=', email)], limit=1)
        if not partner and phone:
            clean_phone = ''.join(c for c in phone if c.isdigit() or c == '+')
            partner = env['res.partner'].sudo().search(
                [('phone', '=', clean_phone)], limit=1)
        if not partner and name:
            partner = env['res.partner'].sudo().create({
                'name': name,
                'email': email or False,
                'phone': phone or False,
            })

        # Título del lead
        lead_name = subject or (
            f"{'Interés en ' + property_type if property_type else 'Consulta'}"
            f"{' en ' + city if city else ''}"
            f" — {name or email or phone}"
        )

        # Buscar tipo de propiedad si se indicó
        ptype = None
        if property_type:
            ptype = env['estate.property.type'].sudo().search(
                [('name', 'ilike', property_type)], limit=1)

        # Buscar referidor si viene código (email o nombre)
        referral_partner = None
        if referral_code:
            referral_partner = env['res.partner'].sudo().search(
                ['|', ('email', '=', referral_code),
                      ('name', 'ilike', referral_code)], limit=1)

        vals = {
            'name': lead_name,
            'contact_name': name,
            'email_from': email or False,
            'phone': phone or False,
            'type': 'opportunity',
            'description': message or False,
            'lead_source': source,
        }
        if partner:
            vals['partner_id'] = partner.id
        if budget:
            try:
                vals['client_budget'] = float(str(budget).replace(',', '').replace('$', ''))
            except (ValueError, TypeError):
                pass
        if ptype:
            vals['preferred_property_type_id'] = ptype.id
        if city:
            vals['preferred_city'] = city
        if bedrooms:
            try:
                vals['preferred_bedrooms'] = int(bedrooms)
            except (ValueError, TypeError):
                pass
        if referral_partner:
            vals['referral_partner_id'] = referral_partner.id
            vals['lead_source'] = 'referral'

        lead = env['crm.lead'].sudo().create(vals)

        # Notificar al equipo de ventas
        lead.message_post(
            body=(
                f'📥 <b>Lead recibido via webhook</b> — Fuente: <b>{source}</b><br/>'
                f'Canal: {request.httprequest.remote_addr}'
            )
        )

        _logger.info("Webhook: lead #%d creado desde fuente '%s' — %s",
                     lead.id, source, name or email or phone)

        return request.make_json_response({
            'success': True,
            'lead_id': lead.id,
            'message': f'Lead #{lead.id} creado correctamente',
        })

    @http.route(
        '/estate/webhook/lead',
        type='http', auth='public', methods=['GET'], csrf=False,
    )
    def webhook_verify(self, **kwargs):
        """
        Verificación GET para servicios como Meta/Facebook que verifican el endpoint.
        Responde con hub.challenge si el token es correcto.
        """
        hub_mode = kwargs.get('hub.mode', '')
        hub_challenge = kwargs.get('hub.challenge', '')
        hub_token = kwargs.get('hub.verify_token', '')

        if hub_mode == 'subscribe' and self._verify_token(hub_token):
            return request.make_response(
                hub_challenge,
                headers=[('Content-Type', 'text/plain')])
        return request.make_json_response({'status': 'ok'})
