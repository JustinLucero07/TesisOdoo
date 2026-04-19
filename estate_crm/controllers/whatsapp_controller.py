import json
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class WhatsAppWebhook(http.Controller):

    @http.route('/whatsapp/webhook', type='jsonrpc', auth='public', methods=['POST'], csrf=False)
    def receive_whatsapp_message(self, **post):
        """
        Endpoint que recibe notificaciones de proveedores como Meta o Twilio.
        Crea Leads directamente en el CRM inmobiliario si recibe consultas.
        """
        data = request.jsonrequest
        if not data:
            return {'status': 'error', 'message': 'No payload received'}

        _logger.info(f"Real Estate WhatsApp Webhook payload: {data}")

        try:
            # Estructura de ejemplo adaptada para Meta API
            entry = data.get('entry', [{}])[0]
            changes = entry.get('changes', [{}])[0]
            value = changes.get('value', {})
            
            messages = value.get('messages', [])
            contacts = value.get('contacts', [])
            
            if not messages:
                return {'status': 'ok'}

            msg = messages[0]
            contact = contacts[0] if contacts else {}
            
            phone = msg.get('from', '')
            name = contact.get('profile', {}).get('name', f'WebLead-{phone}')
            text = msg.get('text', {}).get('body', '')

            if not phone:
                return {'status': 'error', 'message': 'Remitente no identificado'}

            partner = request.env['res.partner'].sudo().search(['|', ('phone', '=', phone), ('mobile', '=', phone)], limit=1)
            
            if not partner:
                partner = request.env['res.partner'].sudo().create({
                    'name': name,
                    'phone': phone,
                    'mobile': phone,
                })

            lead = request.env['crm.lead'].sudo().create({
                'name': f'Consulta Inmobiliaria por WhatsApp - {name}',
                'partner_id': partner.id,
                'description': f"Mensaje recibido:\n\n{text}",
                'type': 'lead',
            })
            
            _logger.info(f"Oportunidad generada exitosamente. Lead ID {lead.id}")
            return {'status': 'success', 'lead_id': lead.id}

        except Exception as e:
            _logger.error(f"Error procesando el Webhook de WhatsApp: {e}")
            return {'status': 'error', 'message': str(e)}
