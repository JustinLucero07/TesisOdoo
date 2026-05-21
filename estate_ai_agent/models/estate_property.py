# -*- coding: utf-8 -*-
import base64
import logging
from odoo import models, api, fields, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    from google import genai
    GOOGLE_GENAI_AVAILABLE = True
except ImportError:
    GOOGLE_GENAI_AVAILABLE = False

class EstateProperty(models.Model):
    _inherit = 'estate.property'

    ai_marketing_description = fields.Text(
        string='Descripción Comercial IA',
        help='Generada por IA: 3 versiones (formal, emocional, directa) + titulares para redes.')
    ai_property_summary = fields.Html(
        string='Resumen IA',
        help='Resumen ejecutivo generado por IA con los puntos clave de la propiedad.')
    ai_summary_date = fields.Datetime(
        string='Fecha del Resumen', readonly=True)
    ai_condition = fields.Selection([
        ('excellent', 'Excelente'),
        ('good', 'Buena'),
        ('regular', 'Regular'),
        ('needs_renovation', 'Necesita Renovación'),
    ], string='Estado del Inmueble (IA)', readonly=True)
    ai_red_flags = fields.Text(
        string='Alertas IA', readonly=True,
        help='Problemas detectados en las imágenes por la IA (humedad, deterioro, etc.)')
    ai_staging_suggestions = fields.Text(
        string='Sugerencias de Staging IA', readonly=True,
        help='Recomendaciones de la IA para mejorar la presentación del inmueble.')
    ai_room_type = fields.Char(string='Tipo de Ambiente (IA)', readonly=True)

    def action_analyze_image_ai(self):
        """Analyze the main image using Gemini Vision and update tags/description."""
        self.ensure_one()
        if not self.image_main:
            raise UserError(_("Por favor, suba una imagen principal antes de analizar."))

        if not GOOGLE_GENAI_AVAILABLE:
            raise UserError(_("La librería 'google-genai' no está instalada. Ejecute: pip install google-genai"))

        # Get API Configuration
        ICP = self.env['ir.config_parameter'].sudo()
        api_key = ICP.get_param('estate_ai.api_key', '')
        if not api_key:
            raise UserError(_("No se ha configurado la API Key de Gemini. Vaya a Configuracion > Agente IA."))

        try:
            # Configure retries for transient errors (503, 429, etc.)
            retry_options = genai.types.HttpRetryOptions(
                attempts=3,
                initial_delay=2.0,
                max_delay=30.0,
                http_status_codes=[429, 500, 502, 503, 504]
            )

            client = genai.Client(
                api_key=api_key,
                http_options=genai.types.HttpOptions(
                    api_version='v1beta',
                    retry_options=retry_options
                ),
            )

            # Prepare image for Gemini
            image_data = base64.b64decode(self.image_main)

            prompt = """
            Analiza esta imagen de una propiedad inmobiliaria y responde UNICAMENTE en formato JSON valido:
            {
                "description": "Descripcion profesional y atractiva de maximo 3 frases",
                "tags": ["Tag1", "Tag2", "Tag3"],
                "condition": "excellent|good|regular|needs_renovation",
                "red_flags": ["Problema visible 1 si existe"],
                "staging_suggestions": ["Sugerencia concreta 1", "Sugerencia concreta 2"],
                "room_type": "sala|cocina|dormitorio|bano|exterior|garaje|area_social|otro"
            }

            Guias:
            - condition: excellent=impecable, good=bien mantenido, regular=uso normal visible, needs_renovation=danos visibles
            - red_flags: SOLO si hay problemas visibles (manchas, humedad, grietas, pintura deteriorada). Array vacio [] si no hay.
            - staging_suggestions: 2-3 sugerencias concretas para mejorar la presentacion en fotos/visitas.
            - room_type: identifica el tipo de ambiente en la imagen.
            """

            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[
                    prompt,
                    genai.types.Part.from_bytes(data=image_data, mime_type='image/jpeg')
                ]
            )

            # Clean response (Gemini sometimes adds markdown blocks)
            raw_text = response.text.strip()
            if raw_text.startswith('```json'):
                raw_text = raw_text.replace('```json', '').replace('```', '').strip()

            import json
            result = json.loads(raw_text)

            # Update description
            self.ai_vision_description = result.get('description', '')

            # Update tags (match or create)
            tag_names = result.get('tags', [])
            if tag_names:
                TagModel = self.env['estate.property.tag']
                tag_ids = []
                for name in tag_names:
                    tag = TagModel.search([('name', '=ilike', name)], limit=1)
                    if not tag:
                        tag = TagModel.create({'name': name.capitalize()})
                    tag_ids.append(tag.id)
                self.tag_ids = [(6, 0, tag_ids)]

            # Update extended AI fields
            condition = result.get('condition', '')
            if condition in ('excellent', 'good', 'regular', 'needs_renovation'):
                self.ai_condition = condition

            red_flags = result.get('red_flags', [])
            self.ai_red_flags = '\n'.join(f'• {f}' for f in red_flags) if red_flags else ''

            staging = result.get('staging_suggestions', [])
            self.ai_staging_suggestions = '\n'.join(f'• {s}' for s in staging) if staging else ''

            self.ai_room_type = result.get('room_type', '')

            return {
                'effect': {
                    'fadeout': 'slow',
                    'message': 'Imagen analizada con exito!',
                    'type': 'rainbow_man',
                }
            }

        except Exception as e:
            _logger.error(f"Error en Vision IA: {str(e)}")
            raise UserError(_("Error al conectar con Gemini Vision: %s") % str(e))

    def action_generate_ai_description(self):
        """Genera descripción comercial profesional con IA y la guarda en el campo descripción."""
        self.ensure_one()
        if not GOOGLE_GENAI_AVAILABLE:
            raise UserError(_("La librería 'google-genai' no está instalada."))

        ICP = self.env['ir.config_parameter'].sudo()
        api_key = ICP.get_param('estate_ai.api_key', '')
        if not api_key:
            raise UserError(_("No se ha configurado la API Key. Vaya a Configuración > Agente IA."))

        prop = self

        # Gather advisor phone numbers
        advisor_phones = []
        if prop.user_id and prop.user_id.partner_id.phone:
            advisor_phones.append(prop.user_id.partner_id.phone)
        if prop.co_user_id and prop.co_user_id.partner_id.phone:
            advisor_phones.append(prop.co_user_id.partner_id.phone)
        phones_text = ' – '.join(advisor_phones) if advisor_phones else 'Consultar'

        # Build property info
        tipo = prop.property_type_id.name if prop.property_type_id else 'Inmueble'
        operacion = 'EN VENTA' if prop.offer_type == 'sale' else 'EN ARRIENDO'
        ciudad = prop.city or ''
        sector = prop.street or ''
        area_terreno = prop.area or 0
        habitaciones = prop.bedrooms or 0
        banos = prop.bathrooms or 0
        parking = prop.parking_spaces or 0
        vehiculos = prop.vehicle_capacity or 0
        piso = prop.floor or 0
        year_built = prop.year_built or 0
        precio = f"${prop.price:,.2f}" if prop.price else 'Consultar'

        # AI vision info if available
        vision_info = ''
        if prop.ai_vision_description:
            vision_info = f"\nAnálisis visual IA de la propiedad: {prop.ai_vision_description}"

        detalles = (
            f"Tipo de propiedad: {tipo}\n"
            f"Operación: {operacion}\n"
            f"Ciudad: {ciudad} | Sector/Dirección: {sector}\n"
            f"Área: {area_terreno} m²\n"
            f"Habitaciones: {habitaciones} | Baños: {banos} | Parqueaderos: {parking} | Capacidad vehículos: {vehiculos}\n"
            f"Piso/Planta: {piso} | Año de construcción: {year_built}\n"
            f"Precio: {precio}\n"
            f"Teléfonos asesores: {phones_text}"
            f"{vision_info}"
        )

        prompt = f"""Eres un experto copywriter inmobiliario de Ecuador. Genera una descripción comercial
ATRACTIVA y PROFESIONAL en formato HTML para publicar en portales inmobiliarios y redes sociales.

REGLAS OBLIGATORIAS:
1. Empieza con un TITULAR llamativo con el tipo de operación (VENTA/ARRIENDO) y el nombre de la propiedad
2. Sigue con un PÁRRAFO GANCHO emocional de 2-3 oraciones que enganche al lector
3. Incluye SECCIONES con ESTOS emojis EXACTOS como encabezados (siempre estos, no otros):
   - 🏠 Propiedad (tipo y descripción general)
   - 📍 Ubicación (ciudad, sector, ventajas de la zona)
   - 💰 Precio e Inversión
   - 📐 Características (área, dimensiones, metros cuadrados)
   - 🛏️ Distribución (habitaciones, baños, cocina, áreas sociales, parqueaderos)
   - ✅ Acabados y Extras
   - 🏷️ Tipo de Propiedad
   - 📞 Contacto (teléfonos de asesores)
4. Usa listas con ✅ o viñetas para las características
5. Termina con un CTA (llamada a la acción) para agendar visita
6. Los teléfonos de los asesores son: {phones_text}
7. El HTML debe usar <h3>, <p>, <ul><li>, <b>, <br/> — NO uses CSS inline ni estilos
8. Sé CREATIVO, VENDEDOR y usa lenguaje emocional pero profesional
9. NO inventes datos que no estén en la información proporcionada
10. Si algún dato es 0 o vacío, NO lo menciones

DATOS DE LA PROPIEDAD:
{detalles}

Responde SOLO con el HTML de la descripción, sin bloques de código ni explicaciones."""

        try:
            retry_options = genai.types.HttpRetryOptions(
                attempts=3,
                initial_delay=2.0,
                max_delay=30.0,
                http_status_codes=[429, 500, 502, 503, 504]
            )

            client = genai.Client(
                api_key=api_key,
                http_options=genai.types.HttpOptions(
                    api_version='v1beta',
                    retry_options=retry_options
                ),
            )
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=genai.types.GenerateContentConfig(temperature=0.85, max_output_tokens=2000),
            )

            html_desc = response.text.strip()
            # Clean markdown code blocks if Gemini wraps it
            if html_desc.startswith('```html'):
                html_desc = html_desc.replace('```html', '').replace('```', '').strip()
            elif html_desc.startswith('```'):
                html_desc = html_desc.replace('```', '').strip()

            # Save to main description field (HTML)
            prop.description = html_desc
            # Also keep copy in marketing field
            prop.ai_marketing_description = html_desc

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': '✨ Descripción generada',
                    'message': 'La descripción comercial se ha generado y guardado exitosamente.',
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.error("Error en generador de descripción IA: %s", str(e))
            raise UserError(_("Error al generar descripción: %s") % str(e))

    def action_generate_property_summary(self):
        """Genera análisis ejecutivo IA completo con TODOS los datos de la propiedad."""
        self.ensure_one()
        import re as _re
        if not GOOGLE_GENAI_AVAILABLE:
            raise UserError(_("La librería 'google-genai' no está instalada."))

        ICP = self.env['ir.config_parameter'].sudo()
        api_key = ICP.get_param('estate_ai.api_key', '')
        if not api_key:
            raise UserError(_("Configure la API Key de IA en Configuración > Agente IA."))

        prop = self

        # ── Datos básicos ──────────────────────────────────────────────────
        tipo = prop.property_type_id.name if prop.property_type_id else 'Inmueble'
        operacion = 'Venta' if prop.offer_type == 'sale' else 'Arriendo'
        estado_label = dict(prop._fields['state'].selection).get(prop.state, prop.state)
        precio = f"${prop.price:,.2f}" if prop.price else 'No definido'
        precio_m2 = f"${prop.price / prop.area:,.2f}/m²" if prop.price and prop.area else ''

        avm_info = 'No calculado'
        if prop.avm_estimated_price:
            diff = ((prop.price - prop.avm_estimated_price) / prop.avm_estimated_price * 100) if prop.price else 0
            avm_label = {'fair': 'En rango de mercado', 'high': 'Por encima del mercado', 'low': 'Por debajo del mercado'}.get(prop.avm_status, '')
            avm_info = f"${prop.avm_estimated_price:,.2f} → {avm_label} ({diff:+.1f}% vs precio actual)"

        # ── Historial de precios ───────────────────────────────────────────
        motivo_map = dict(self.env['estate.property.price.history']._fields['change_reason'].selection) \
            if 'estate.property.price.history' in self.env else {}
        price_lines = []
        for ph in prop.price_history_ids[:8]:
            motivo = motivo_map.get(ph.change_reason, ph.change_reason or '')
            price_lines.append(
                f"  • {ph.date.strftime('%d/%m/%Y')}: ${ph.old_price:,.0f} → ${ph.new_price:,.0f} "
                f"({ph.change_pct:+.1f}%) [{motivo}{' — ' + ph.notes if ph.notes else ''}]"
            )

        # ── Leads interesados ──────────────────────────────────────────────
        leads = self.env['crm.lead'].search(
            [('target_property_id', '=', prop.id)],
            order='lead_score asc, create_date desc', limit=20
        ) if 'target_property_id' in self.env['crm.lead']._fields else []

        temp_map = {'cold': 'Frío', 'warm': 'Tibio', 'hot': 'Caliente', 'boiling': 'Hirviendo'}
        lead_lines = []
        for l in leads:
            nombre = (l.partner_id.name if l.partner_id else None) or l.partner_name or l.name or 'Sin nombre'
            budget = f"${l.client_budget:,.0f}" if l.client_budget else 'N/A'
            temp = temp_map.get(l.lead_temperature, l.lead_temperature or '—')
            score = l.lead_score or '—'
            stage = l.stage_id.name if l.stage_id else 'Sin etapa'
            lead_lines.append(f"  • {nombre} | Presupuesto: {budget} | Temperatura: {temp} | Score: {score} | Etapa: {stage}")

        # ── Visitas / Citas ────────────────────────────────────────────────
        visits = self.env['calendar.event'].search(
            [('property_id', '=', prop.id)], order='start desc', limit=10
        ) if 'property_id' in self.env['calendar.event']._fields else []

        rating_map = {'1': '⭐ Muy bajo', '2': '⭐⭐ Bajo', '3': '⭐⭐⭐ Normal', '4': '⭐⭐⭐⭐ Bueno', '5': '⭐⭐⭐⭐⭐ Excelente'}
        visit_lines = []
        for v in visits:
            attendees = ', '.join(a.partner_id.name for a in v.attendee_ids if a.partner_id) or 'Sin asistentes'
            rating = rating_map.get(str(getattr(v, 'visit_rating', '') or ''), 'Sin calificar')
            visit_lines.append(f"  • {v.start.strftime('%d/%m/%Y %H:%M')}: {attendees} — Rating: {rating}")

        # ── Mensajes recientes del chatter ─────────────────────────────────
        messages = self.env['mail.message'].search([
            ('res_id', '=', prop.id), ('model', '=', 'estate.property'),
            ('message_type', 'in', ['comment', 'email']),
        ], order='date desc', limit=6)
        msg_lines = []
        for m in messages:
            author = m.author_id.name if m.author_id else 'Sistema'
            body = _re.sub('<[^<]+?>', '', m.body or '').strip()[:180]
            if body:
                msg_lines.append(f"  • [{m.date.strftime('%d/%m/%Y')}] {author}: {body}")

        # ── Contexto completo para IA ──────────────────────────────────────
        context_text = f"""
PROPIEDAD: {prop.name or 'Sin nombre'} | Código: {getattr(prop, 'ref', '') or prop.id}
Tipo: {tipo} | Operación: {operacion} | Estado: {estado_label}
Ubicación: {prop.street or ''}, {prop.city or ''}, {prop.state_id.name if prop.state_id else ''}
Área: {prop.area or 0} m² | Hab: {prop.bedrooms or 0} | Baños: {prop.bathrooms or 0} | Parqueaderos: {prop.parking_spaces or 0}
Piso: {getattr(prop, 'floor', 0) or 0} | Año construcción: {getattr(prop, 'year_built', '') or 'N/A'}
Precio actual: {precio} {f'({precio_m2})' if precio_m2 else ''}
Valoración AVM: {avm_info}
Días en mercado: {prop.days_on_market or 0}
Propietario: {prop.owner_id.name if prop.owner_id else 'Sin asignar'}
Asesor: {prop.user_id.name if prop.user_id else 'Sin asignar'}
Publicado en web: {'Sí' if prop.wp_published else 'No'}

HISTORIAL DE PRECIOS ({len(price_lines)} cambio(s)):
{chr(10).join(price_lines) if price_lines else '  Sin cambios de precio registrados.'}

LEADS INTERESADOS ({len(lead_lines)} lead(s)):
{chr(10).join(lead_lines) if lead_lines else '  Sin leads asignados a esta propiedad.'}

VISITAS REALIZADAS ({len(visit_lines)} cita(s)):
{chr(10).join(visit_lines) if visit_lines else '  Sin visitas registradas.'}

ACTIVIDAD RECIENTE:
{chr(10).join(msg_lines) if msg_lines else '  Sin mensajes recientes.'}
"""

        prompt = f"""Genera un análisis inmobiliario en HTML para el asesor. SIN introducción, SIN "Estimado Asesor", ve DIRECTO a las secciones.

USA EXACTAMENTE esta estructura (6 secciones, emojis como encabezados):

<p><strong>🏠 Ficha</strong></p>
<ul><li>...</li></ul>

<p><strong>💰 Precio</strong></p>
<ul><li>...</li></ul>

<p><strong>👥 Interesados</strong></p>
<ul><li>NOMBRE REAL de cada lead, su presupuesto y temperatura</li></ul>

<p><strong>📅 Visitas</strong></p>
<ul><li>NOMBRE REAL de cada visitante, fecha y calificación</li></ul>

<p><strong>⚠️ Alertas</strong></p>
<ul><li>...</li></ul>

<p><strong>🎯 Acción inmediata</strong></p>
<ul><li>1-2 acciones concretas</li></ul>

REGLAS CRÍTICAS:
- SIEMPRE menciona los NOMBRES REALES de leads y visitantes (están en los datos)
- Si no hay visitas/leads, escribe "Sin registros — registra citas para dar seguimiento"
- Máximo 350 palabras, sin CSS inline, sin intro genérica
- Interpreta los datos: ¿el precio está bien? ¿hay interés real? ¿qué falta?

DATOS:
{context_text}

Responde SOLO el HTML listo para insertar. Sin markdown, sin explicaciones."""

        try:
            client = genai.Client(
                api_key=api_key,
                http_options=genai.types.HttpOptions(api_version='v1beta'),
            )
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=genai.types.GenerateContentConfig(temperature=0.35, max_output_tokens=2500),
            )
            html = response.text.strip()
            html = _re.sub(r'^```\w*\n?', '', html)
            html = _re.sub(r'\n?```$', '', html).strip()

            prop.write({
                'ai_property_summary': html,
                'ai_summary_date': fields.Datetime.now(),
            })
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': '🤖 Análisis actualizado',
                    'message': 'El análisis ejecutivo IA se generó con todos los datos disponibles.',
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.error("Error generando análisis IA: %s", str(e))
            raise UserError(_("Error al generar análisis: %s") % str(e))

    def action_open_ai_chat_for_property(self):
        """Opens the AI chat action with a pre-loaded question about this property."""
        self.ensure_one()
        prop_name = self.name or f"ID {self.id}"
        return {
            'type': 'ir.actions.client',
            'tag': 'estate_ai_chat',
            'name': f'Asistente IA — {prop_name}',
            'context': {
                'default_message': (
                    f"Dame un análisis completo de la propiedad \"{prop_name}\" "
                    f"(ID: {self.id}): precio, valoración AVM, días en mercado, "
                    f"leads interesados y recomendación de estrategia."
                )
            },
        }
