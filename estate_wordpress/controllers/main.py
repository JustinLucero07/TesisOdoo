# -*- coding: utf-8 -*-
from odoo import http, _, fields
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)

class EstateWordpressController(http.Controller):

    @http.route('/estate_wordpress/lead/create', type='jsonrpc', auth='public', methods=['POST'], csrf=False)
    def create_lead_from_external(self, **post):
        """
        Endpoint para recibir leads desde WordPress o WhatsApp.
        JSON Esperado: {
            "name": "Nombre Cliente",
            "email": "email@test.com",
            "phone": "0999999999",
            "property_id": "PROP-0001",
            "message": "Me interesa esta casa"
        }
        """
        try:
            name = post.get('name', 'Consulta Web')
            email = post.get('email')
            phone = post.get('phone')
            property_id = post.get('property_id')
            message = post.get('message', '')

            property_record = False
            if property_id:
                property_record = request.env['estate.property'].sudo().search([('name', '=', property_id)], limit=1)

            description = message
            if property_record:
                description += f"\n\n--- INTERÉS EN PROPIEDAD ---\n"
                description += f"ID: {property_record.name}\n"
                description += f"Título: {property_record.title}\n"
                description += f"Precio: ${property_record.price:,.2f}"

            lead_vals = {
                'name': f"Consulta: {property_record.title if property_record else 'Inmueble General'}",
                'contact_name': name,
                'email_from': email,
                'phone': phone,
                'description': description,
                'user_id': property_record.user_id.id if property_record and property_record.user_id else False,
                'team_id': request.env.ref('sales_team.team_sales_department', raise_if_not_found=False).id,
            }

            new_lead = request.env['crm.lead'].sudo().create(lead_vals)

            return {
                'status': 'success',
                'lead_id': new_lead.id,
                'message': _('Lead creado correctamente en el CRM.')
            }

        except Exception as e:
            _logger.error("Error creating lead from External Webhook: %s", str(e))
            return {'status': 'error', 'message': str(e)}

    @http.route('/estate_wordpress/webhook/contact', type='jsonrpc', auth='public', methods=['POST'], csrf=False)
    def webhook_contact_form(self, **kwargs):
        """
        Webhook mejorado para formularios de contacto de WordPress/Houzez.
        Acepta payload JSON con validación de token secreto.
        Payload esperado:
        {
            "secret": "token_secreto_configurado",
            "name": "Juan Pérez",
            "email": "juan@example.com",
            "phone": "+593999999999",
            "message": "Estoy interesado en...",
            "wp_post_id": 42,
            "property_title": "Casa en Cuenca",
            "budget": 85000
        }
        """
        try:
            data = request.get_json_data() or kwargs
        except Exception:
            data = kwargs

        # Validar token secreto
        ICP = request.env['ir.config_parameter'].sudo()
        expected_secret = ICP.get_param('estate_wp.webhook_secret', '')
        if expected_secret and data.get('secret') != expected_secret:
            _logger.warning("WordPress webhook /contact: token inválido desde %s", request.httprequest.remote_addr)
            return {'success': False, 'error': 'Token inválido'}

        name = data.get('name', 'Contacto WordPress')
        email = data.get('email', '')
        phone = data.get('phone', '')
        message = data.get('message', '')
        property_title = data.get('property_title', '')
        wp_post_id = data.get('wp_post_id')
        budget = data.get('budget', 0)

        # Buscar o crear contacto
        Partner = request.env['res.partner'].sudo()
        partner = False
        if email:
            partner = Partner.search([('email', '=ilike', email)], limit=1)
        if not partner and phone:
            clean_phone = ''.join(filter(str.isdigit, phone))
            partner = Partner.search([('phone', 'like', clean_phone[-8:])], limit=1)
        if not partner:
            partner = Partner.create({'name': name, 'email': email, 'phone': phone})

        # Buscar propiedad por WordPress post ID
        estate_property = False
        if wp_post_id:
            estate_property = request.env['estate.property'].sudo().search(
                [('wp_post_id', '=', int(wp_post_id))], limit=1)

        description = f"Contacto recibido desde el sitio web WordPress.\n"
        if message:
            description += f"\nMensaje:\n{message}"
        if property_title:
            description += f"\n\nPropiedad de interés: {property_title}"

        lead_vals = {
            'name': f"Web: {name} — {property_title or 'Consulta General'}",
            'partner_id': partner.id,
            'email_from': email,
            'phone': phone,
            'description': description,
            'type': 'lead',
        }
        if estate_property:
            lead_vals['target_property_id'] = estate_property.id
        if budget:
            lead_vals['client_budget'] = float(budget)

        lead = request.env['crm.lead'].sudo().create(lead_vals)
        _logger.info("WordPress webhook: lead %d creado para %s", lead.id, name)

        # Notificar al asesor responsable con actividad y mensaje en chatter
        try:
            responsible_id = (estate_property.user_id.id if estate_property else False) or request.env.uid
            activity_type = request.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
            if activity_type:
                note_parts = [f'Nombre: {name}']
                if email:
                    note_parts.append(f'Email: {email}')
                if phone:
                    note_parts.append(f'Tel: {phone}')
                if property_title:
                    note_parts.append(f'Interesado en: {property_title}')
                if budget:
                    note_parts.append(f'Presupuesto: ${float(budget):,.0f}')
                request.env['mail.activity'].sudo().create({
                    'res_id': lead.id,
                    'res_model_id': request.env['ir.model'].sudo()._get_id('crm.lead'),
                    'activity_type_id': activity_type.id,
                    'summary': f'🌐 Nuevo lead desde WordPress: {name}',
                    'note': ' · '.join(note_parts),
                    'user_id': responsible_id,
                    'date_deadline': fields.Date.today(),
                })
            lead.message_post(
                body=(
                    f'<p><strong>Lead creado automáticamente desde WordPress.</strong><br/>'
                    f'{"Propiedad: " + property_title + "<br/>" if property_title else ""}'
                    f'{"Email: " + email + "<br/>" if email else ""}'
                    f'{"Teléfono: " + phone if phone else ""}</p>'
                )
            )
        except Exception as ex:
            _logger.warning("No se pudo crear actividad para lead %d: %s", lead.id, ex)

        return {'success': True, 'lead_id': lead.id}

    # ------------------------------------------------------------------
    # Endpoint HTTP simple para Houzez (WordPress lo llama con wp_remote_post)
    # ------------------------------------------------------------------
    @http.route('/estate/wp/houzez/inquiry', type='http', auth='public', methods=['POST'], csrf=False)
    def houzez_inquiry(self, **post):
        """
        Recibe el formulario de contacto de Houzez y crea un lead en CRM.
        WordPress envía: secret, name, email, phone, message, wp_post_id,
                         property_title, role (buyer/tenant/other)
        """
        try:
            raw = request.httprequest.data
            data = json.loads(raw) if raw else post
        except Exception:
            data = post

        def _resp(ok, **kw):
            return request.make_response(
                json.dumps({'success': ok, **kw}),
                headers=[('Content-Type', 'application/json')]
            )

        # Validar token
        ICP = request.env['ir.config_parameter'].sudo()
        expected = ICP.get_param('estate_wp.webhook_secret', '')
        if expected and data.get('secret') != expected:
            _logger.warning("Houzez inquiry: token inválido desde %s", request.httprequest.remote_addr)
            return _resp(False, error='Token inválido')

        name           = data.get('name', 'Contacto Houzez')
        email          = data.get('email', '')
        phone          = data.get('phone', '')
        message        = data.get('message', '')
        property_title = data.get('property_title', '')
        wp_post_id     = data.get('wp_post_id')
        role           = data.get('role', '')          # buyer / tenant / other

        # Buscar o crear contacto (res.partner)
        Partner = request.env['res.partner'].sudo()
        partner = False
        if email:
            partner = Partner.search([('email', '=ilike', email)], limit=1)
        if not partner and phone:
            digits = str(''.join(filter(str.isdigit, phone)))
            partner = Partner.search([('phone', 'like', digits[-8:])], limit=1)
        if not partner:
            partner = Partner.create({'name': name, 'email': email, 'phone': phone})

        # Buscar propiedad por wp_post_id
        estate_property = False
        if wp_post_id:
            estate_property = request.env['estate.property'].sudo().search(
                [('wp_post_id', '=', int(wp_post_id))], limit=1)

        role_labels = {'buyer': 'Comprador', 'tenant': 'Arrendatario', 'other': 'Otro'}
        role_text = role_labels.get(role, role)

        desc_parts = ['Consulta recibida desde el formulario de contacto de Houzez (WordPress).']
        if role_text:
            desc_parts.append(f'Tipo de contacto: {role_text}')
        if message:
            desc_parts.append(f'\nMensaje:\n{message}')
        if property_title:
            desc_parts.append(f'\nPropiedad de interés: {property_title}')

        lead_vals = {
            'name': f"Web Houzez: {name} — {property_title or 'Consulta General'}",
            'partner_id': partner.id,
            'email_from': email,
            'phone': phone,
            'description': '\n'.join(desc_parts),
            'type': 'lead',
        }
        if estate_property:
            lead_vals['target_property_id'] = estate_property.id
        if role == 'tenant':
            lead_vals['offer_type'] = 'rent' if hasattr(request.env['crm.lead'], 'offer_type') else None

        lead = request.env['crm.lead'].sudo().create(lead_vals)
        _logger.info("Houzez inquiry: lead %d creado para '%s' (prop: %s)", lead.id, name, property_title)

        # Actividad para el asesor responsable
        try:
            responsible_id = (estate_property.user_id.id if estate_property else False) or request.env.ref('base.user_admin').id
            activity_type = request.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
            if activity_type:
                parts = [f'Nombre: {name}']
                if email:   parts.append(f'Email: {email}')
                if phone:   parts.append(f'Tel: {phone}')
                if role_text: parts.append(f'Rol: {role_text}')
                if property_title: parts.append(f'Interesado en: {property_title}')
                request.env['mail.activity'].sudo().create({
                    'res_id': lead.id,
                    'res_model_id': request.env['ir.model'].sudo()._get_id('crm.lead'),
                    'activity_type_id': activity_type.id,
                    'summary': f'Nuevo lead Houzez: {name}',
                    'note': ' · '.join(parts),
                    'user_id': responsible_id,
                    'date_deadline': fields.Date.today(),
                })
            lead.message_post(body=(
                f'<p><strong>Lead creado automáticamente desde formulario Houzez (WordPress).</strong><br/>'
                f'{"Propiedad: " + property_title + "<br/>" if property_title else ""}'
                f'{"Rol: " + role_text + "<br/>" if role_text else ""}'
                f'{"Email: " + email + "<br/>" if email else ""}'
                f'{"Teléfono: " + phone if phone else ""}</p>'
            ))
        except Exception as ex:
            _logger.warning("No se pudo crear actividad para lead %d: %s", lead.id, ex)

        return _resp(True, lead_id=lead.id)
