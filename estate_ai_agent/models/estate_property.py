# -*- coding: utf-8 -*-
import base64
import logging
from odoo import models, api, fields, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class EstateProperty(models.Model):
    _inherit = 'estate.property'

    ai_marketing_description = fields.Text(
        string='Descripción Comercial IA',
        help='Generada por IA: 3 versiones (formal, emocional, directa) + titulares para redes.')
    ai_extra_prompt = fields.Text(
        string='Aspectos adicionales para la IA',
        help='Escribe aquí cualquier detalle extra que quieras que la IA incluya: acabados especiales, vista, remodelaciones, cercanía a lugares, etc.')
    ai_refine_prompt = fields.Text(
        string='Instrucciones para refinar la descripción',
        help='Dile a la IA qué cambiar en la descripción ya generada: "hazla más corta", "quita el precio", "agrega más emoción", "enfócate en la vista", etc.')
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

        try:
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

            genai_mixin = self.env['estate.genai.mixin']
            raw_text = genai_mixin._genai_generate(
                prompt, image_bytes=image_data, image_mime='image/jpeg',
                temperature=0.4, max_output_tokens=2048,
            )
            raw_text = genai_mixin._genai_strip_fences(raw_text)

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
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Imagen analizada',
                    'message': 'Condición, tags y sugerencias de staging guardados.',
                    'type': 'success',
                    'sticky': False,
                    'next': {'type': 'ir.actions.client', 'tag': 'reload'},
                }
            }

        except UserError:
            raise
        except Exception as e:
            _logger.error(f"Error en Vision IA: {str(e)}")
            raise UserError(_("Error al conectar con Gemini Vision: %s") % str(e))

    def action_generate_ai_description(self):
        """Genera descripción comercial profesional con IA y la guarda en el campo descripción."""
        self.ensure_one()
        prop = self

        # ── Teléfonos de contacto ───────────────────────────────────────────
        # 1) Lista fija de la agencia (configurable): Ajustes > Agente IA →
        #    parámetro 'estate_ai.contact_phones' (ej: "099... – 098... – 097...").
        # 2) Si no hay lista fija, se arman con los teléfonos de TODOS los asesores
        #    (grupo Agente) + los asesores asignados a la propiedad.
        phones_param = self.env['ir.config_parameter'].sudo().get_param(
            'estate_ai.contact_phones', '').strip()
        if phones_param:
            phones_text = phones_param
        else:
            advisor_phones = []
            agent_group = self.env.ref(
                'estate_management.estate_group_agent', raise_if_not_found=False)
            candidates = list(agent_group.user_ids) if agent_group else []
            candidates += [prop.user_id, prop.co_user_id]
            for user in candidates:
                if user and user.partner_id:
                    p = (user.partner_id.mobile or user.partner_id.phone or '').strip()
                    if p and p not in advisor_phones:
                        advisor_phones.append(p)
            phones_text = ' – '.join(advisor_phones) if advisor_phones else (
                self.env.company.phone or 'Consultar')

        # ── Core fields ─────────────────────────────────────────────────────
        titulo   = (prop.title or '').strip()
        tipo     = prop.property_type_id.name if prop.property_type_id else 'Inmueble'
        operacion = 'EN VENTA' if prop.offer_type == 'sale' else 'EN ARRIENDO'
        ciudad   = (prop.city or 'Cuenca').strip()
        sector   = (prop.street or '').strip()
        precio_raw = prop.price or 0
        precio   = f"${precio_raw:,.0f}".replace(',', '.') if precio_raw else 'Consultar'
        area     = prop.area or 0
        habs     = prop.bedrooms or 0
        banos    = prop.bathrooms or 0
        parking  = prop.parking_spaces or 0
        piso     = prop.floor or 0
        year_built = prop.year_built or 0
        es_terreno = getattr(prop, 'is_land_type', False)
        exclusivo  = getattr(prop, 'is_exclusive', False)

        # Sector keywords (curated by advisor)
        sector_kw = (getattr(prop, 'sector_keywords', '') or '').strip()

        # Tags → amenities list
        tags_list = [t.name for t in prop.tag_ids] if prop.tag_ids else []

        # Mortgage financing info
        cuota = getattr(prop, 'mortgage_monthly_payment', 0) or 0

        # AVM / ROI
        avm_price = getattr(prop, 'avm_estimated_price', 0) or 0
        avm_status = getattr(prop, 'avm_status', '') or ''
        roi_rate = getattr(prop, 'roi_appreciation_rate', 0) or 0
        roi_5y   = getattr(prop, 'roi_5year_value', 0) or 0

        # AI Vision enrichment
        vision_desc = (prop.ai_vision_description or '').strip()
        ai_cond     = (getattr(prop, 'ai_condition', '') or '').strip()
        ai_staging  = (getattr(prop, 'ai_staging_suggestions', '') or '').strip()

        # ── Build structured data block ──────────────────────────────────────
        lines = [
            f"EMPRESA: Inmobi (inmobiliaria ecuatoriana)",
            f"OPERACIÓN: {operacion}",
            f"TIPO: {tipo}{'  [ES TERRENO]' if es_terreno else ''}{'  [EXCLUSIVIDAD]' if exclusivo else ''}",
            f"TÍTULO DEL ANUNCIO: {titulo}" if titulo else None,
            f"CIUDAD: {ciudad}" + (f" | SECTOR: {sector}" if sector else ''),
            f"PRECIO: {precio}" + (f"  (cuota crédito estimada: ${cuota:,.0f}/mes)".replace(',', '.') if cuota > 0 else ''),
            f"ÁREA TOTAL: {area} m²" if area else None,
            f"HABITACIONES: {habs}" if habs else None,
            f"BAÑOS: {banos}" if banos else None,
            f"PARQUEADEROS: {parking}" if parking else None,
            f"PISO/PLANTA: {piso}" if piso else None,
            f"AÑO CONSTRUCCIÓN: {year_built}" if year_built else None,
            f"AMENITIES/CARACTERÍSTICAS ESPECIALES: {', '.join(tags_list)}" if tags_list else None,
            f"PALABRAS CLAVE DEL SECTOR: {sector_kw}" if sector_kw else None,
            f"ANÁLISIS VISUAL IA: {vision_desc}" if vision_desc else None,
            f"CONDICIÓN DE LA PROPIEDAD (IA): {ai_cond}" if ai_cond else None,
            f"TIPO DE AMBIENTE (IA): {getattr(prop, 'ai_room_type', '') or ''}" if getattr(prop, 'ai_room_type', '') else None,
            f"VALORACIÓN AVM: ${avm_price:,.0f}".replace(',', '.') + f" ({avm_status})" if avm_price else None,
            f"TASA DE APRECIACIÓN ANUAL: {roi_rate:.1f}% | VALOR PROYECTADO 5 AÑOS: ${roi_5y:,.0f}".replace(',', '.') if roi_rate else None,
        ]
        detalles = '\n'.join(l for l in lines if l)

        extra_section = ''
        if prop.ai_extra_prompt and prop.ai_extra_prompt.strip():
            extra_section = f"\n\nDESTACAR OBLIGATORIAMENTE (instrucción del asesor):\n{prop.ai_extra_prompt.strip()}"

        # B4: instrucciones de estilo editables desde Configuración (no hardcodeadas)
        style_instructions = self.env['ir.config_parameter'].sudo().get_param(
            'estate_ai.desc_instructions', '').strip()
        if style_instructions:
            extra_section += f"\n\nESTILO Y TONO (configuración de la inmobiliaria):\n{style_instructions}"

        # ── Prompt ───────────────────────────────────────────────────────────
        prompt = f"""Eres el copywriter inmobiliario estrella de Inmobi, una inmobiliaria profesional de Ecuador especializada en Cuenca.
Tu misión: escribir una descripción comercial IMPACTANTE para publicar en portales y redes sociales.

═══════════════════════════════════════════════════════
DATOS DE LA PROPIEDAD
═══════════════════════════════════════════════════════
{detalles}{extra_section}

═══════════════════════════════════════════════════════
ESTRUCTURA OBLIGATORIA (en este orden exacto, con EMOJIS)
═══════════════════════════════════════════════════════

1. TITULAR (una sola línea, MAYÚSCULAS, en negrita <b>)
   Formato: "[TIPO] [OPERACIÓN] – [SECTOR/CIUDAD] – [GANCHO CORTO]"
   Ejemplo: "CASA EN VENTA – CUENCA, AV. 12 DE OCTUBRE – HOGAR MODERNO CON ALTA PLUSVALÍA"

2. PÁRRAFO DE APERTURA (2-3 oraciones)
   Empieza con: "Inmobi te presenta [artículo + tipo] en [operación] en [sector], ..."
   Engancha emocionalmente y menciona lo más valioso de la propiedad.

3. <b>✨ Características Principales</b> (lista <ul><li>)
   Cada viñeta inicia con un emoji adecuado. Incluye SOLO datos disponibles (> 0):
   📐 Área total · 🛏️ Habitaciones · 🚿 Baños · 🚗 Parqueaderos · 🏢 Piso · 🗓️ Año de construcción
   ✅ Amenities y características especiales de los tags
   - Si hay CONDICIÓN DE LA PROPIEDAD (IA), tradúcela comercial:
     excellent→"acabados en excelente estado", good→"bien conservada", regular→"lista para personalizarla"
   - Si hay ANÁLISIS VISUAL IA / TIPO DE AMBIENTE (IA), INTÉGRALO en la descripción
     (fachada, estilo, iluminación, ambiente) de forma natural — no lo ignores.

4. <b>📍 Ubicación y Entorno</b>
   Ciudad, sector y ventajas de la zona (usa PALABRAS CLAVE DEL SECTOR si existen).
   Cercanía a servicios, comercios y vías. Si no hay datos del sector, describe la ciudad.

5. <b>💰 Potencial e Inversión</b> (solo si aplica)
   - Terrenos: opciones de uso (vivienda, quinta, proyecto residencial/comercial).
   - Venta: ROI, plusvalía, valor proyectado (solo si hay datos).
   - Arriendo: beneficios del sector. Si no hay datos, omite esta sección.

6. <b>💵 Precio</b>
   Formato: <b>💵 Precio: $[precio con puntos ecuatorianos]</b>  (ej: $135.000)
   Si hay cuota crédito: <small>(Cuota estimada crédito: $xxx/mes)</small>

7. LLAMADA A LA ACCIÓN (1-2 oraciones cálidas para agendar una visita).

8. <b>📞 Información y Contactos</b>
   Una sola línea: "Celular / WhatsApp: {phones_text}"

═══════════════════════════════════════════════════════
REGLAS ESTRICTAS
═══════════════════════════════════════════════════════
- USA EMOJIS con elegancia en los encabezados de sección y viñetas clave
  (✨ 📍 💰 💵 📞 🏡 🛏️ 🚿 🚗 📐 ✅ 🗓️), como en los anuncios profesionales de Ecuador.
- HTML limpio: <b>, <p>, <ul><li>, <br/>, <small> — PROHIBIDO CSS inline ni style=""
- PROHIBIDO inventar datos que no estén en el bloque de datos
- Si un campo es 0 o vacío, OMÍTELO — no digas "0 habitaciones"
- Para terrenos: NO uses habitaciones/baños; usa potencial de construcción
- Español ecuatoriano profesional, precios con puntos (135.000 no 135,000)
- Texto cálido y fluido, NO genérico; completa TODAS las secciones
- TERMINA SIEMPRE con la línea de teléfonos exactamente: {phones_text}

Responde ÚNICAMENTE con el HTML final. Sin explicaciones, sin bloques ```html, sin comentarios."""

        try:
            html_desc = self.env['estate.genai.mixin']._genai_generate(
                prompt, temperature=0.85, max_output_tokens=8192,
            )

            # Extracción robusta heredada (el mixin ya lanza si viene vacío)
            html_desc = self.env['estate.genai.mixin']._genai_strip_fences(html_desc)

            # Save to main description field (HTML)
            prop.description = html_desc
            # Also keep copy in marketing field
            prop.ai_marketing_description = html_desc

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Descripción generada',
                    'message': 'La descripción comercial se guardó. Ya puedes verla y refinarla.',
                    'type': 'success',
                    'sticky': False,
                    'next': {'type': 'ir.actions.client', 'tag': 'reload'},
                }
            }
        except UserError:
            raise
        except Exception as e:
            _logger.error("Error en generador de descripción IA: %s", str(e))
            raise UserError(_("Error al generar descripción: %s") % str(e))

    def action_generate_ai_description_full(self):
        """Analiza imagen (si existe) + genera descripción comercial en un solo clic."""
        self.ensure_one()
        steps = []

        # Step 1: image analysis (optional — enriches ai_vision_description)
        if self.image_main:
            try:
                self.action_analyze_image_ai()
                steps.append('imagen analizada')
            except Exception as e:
                _logger.warning("Análisis de imagen omitido en acción completa: %s", str(e))

        # Step 2: generate commercial description (uses ai_vision_description if available)
        try:
            self.action_generate_ai_description()
            steps.append('descripción generada')
        except UserError:
            raise
        except Exception as e:
            raise UserError(_("Error al generar descripción: %s") % str(e))

        msg = ' · '.join(s.capitalize() for s in steps) if steps else 'Completado'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'IA completa',
                'message': f'{msg}. La descripción ya está visible.',
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            }
        }

    def action_refine_ai_description(self):
        """Refina la descripción existente con las instrucciones del usuario."""
        self.ensure_one()
        if not self.description:
            raise UserError(_("Primero genera una descripción base con el botón 'Generar Descripción'."))
        if not (self.ai_refine_prompt or '').strip():
            raise UserError(_("Escribe qué quieres cambiar en el campo 'Instrucciones para refinar'."))

        desc_text = self.description or ''

        prompt = f"""Eres un copywriter inmobiliario experto de Ecuador.
Esta es la descripción comercial ACTUAL de una propiedad (HTML con emojis):

--- DESCRIPCIÓN ACTUAL ---
{desc_text}
--- FIN ---

El usuario pide ESTOS cambios (y SOLO estos):
{self.ai_refine_prompt.strip()}

INSTRUCCIONES:
1. PARTE de la descripción actual: CONSERVA todo lo que el usuario NO pidió cambiar
   (sus secciones, datos, emojis y teléfonos). NO la reescribas desde cero ni la borres.
2. Aplica ÚNICAMENTE los cambios pedidos (ej: más larga / más corta, otro tono,
   agregar o quitar un detalle, reordenar). El resto queda igual.
3. Mantén el estilo: HTML limpio (<b>, <p>, <ul><li>, <br/>, <small>) y los EMOJIS
   de sección (✨ 📍 💰 💵 📞).
4. Conserva la línea de teléfonos del final tal cual estaba.
5. NO inventes datos nuevos que no estuvieran en la descripción original.

Responde SOLO con el HTML modificado, sin explicaciones, sin bloques ```html.
"""
        try:
            html_desc = self.env['estate.genai.mixin']._genai_generate(
                prompt, temperature=0.7, max_output_tokens=8192,
            )
            html_desc = self.env['estate.genai.mixin']._genai_strip_fences(html_desc)

            self.description = html_desc
            self.ai_refine_prompt = False
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Descripción refinada',
                    'message': 'Los cambios se aplicaron correctamente a la descripción.',
                    'type': 'success',
                    'sticky': False,
                    'next': {'type': 'ir.actions.client', 'tag': 'reload'},
                }
            }
        except Exception as e:
            raise UserError(_("Error al refinar descripción: %s") % str(e))

    def action_generate_property_summary(self):
        """Genera análisis ejecutivo IA completo con TODOS los datos de la propiedad."""
        self.ensure_one()
        import re as _re
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
        temp_map = {'cold': 'Frío', 'warm': 'Tibio', 'hot': 'Caliente', 'boiling': 'Hirviendo'}
        lead_lines = []
        if 'target_property_id' in self.env['crm.lead']._fields:
            # Usamos el MISMO criterio que el botón "Leads Interesados" de la
            # propiedad (presupuesto compatible), para que el número de la IA
            # coincida con el del botón. Se etiqueta cada lead como DIRECTO
            # (eligió esta propiedad) o POTENCIAL (solo coincide el presupuesto).
            if hasattr(prop, '_get_lead_match_domain') and prop.price:
                match_leads = self.env['crm.lead'].search(
                    prop._get_lead_match_domain(),
                    order='lead_score asc, create_date desc', limit=15)
            else:
                match_leads = self.env['crm.lead'].search(
                    [('target_property_id', '=', prop.id)],
                    order='lead_score asc, create_date desc', limit=15)
            for l in match_leads:
                nombre = (l.partner_id.name if l.partner_id else None) or l.partner_name or l.name or 'Sin nombre'
                budget = f"${l.client_budget:,.0f}" if l.client_budget else 'N/A'
                temp = temp_map.get(getattr(l, 'lead_temperature', ''), '—')
                score = getattr(l, 'lead_score', '—') or '—'
                stage = l.stage_id.name if l.stage_id else 'Sin etapa'
                es_directo = getattr(l, 'target_property_id', False) and l.target_property_id.id == prop.id
                etiqueta = 'DIRECTO' if es_directo else 'POTENCIAL'
                lead_lines.append(f"  • [{etiqueta}] {nombre} | Presupuesto: {budget} | Temperatura: {temp} | Score: {score} | Etapa: {stage}")

        # ── Visitas / Citas ────────────────────────────────────────────────
        visits = self.env['calendar.event'].search(
            [('property_id', '=', prop.id)], order='start desc', limit=10
        ) if 'property_id' in self.env['calendar.event']._fields else []

        rating_map = {'1': 'Muy bajo', '2': 'Bajo', '3': 'Normal', '4': 'Bueno', '5': 'Excelente'}
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

        prompt = f"""Genera un análisis inmobiliario en HTML para el asesor. SIN introducción, SIN saludos, ve DIRECTO a las secciones.

USA EXACTAMENTE esta estructura (6 secciones):

<p><strong>Ficha</strong></p><ul><li>Código, tipo, operación, ubicación, área, habitaciones, baños, parqueaderos</li></ul>

<p><strong>Precio</strong></p><ul><li>Análisis del precio, precio/m², comparación AVM si existe</li></ul>

<p><strong>Interesados</strong></p><ul><li>NOMBRE REAL de cada lead con presupuesto y temperatura. Si hay potenciales, mencionarlos.</li></ul>

<p><strong>Visitas</strong></p><ul><li>NOMBRE REAL de cada visitante, fecha, calificación</li></ul>

<p><strong>Alertas</strong></p><ul><li>Problemas detectados: propietario no asignado, AVM sin calcular, sin imágenes, etc.</li></ul>

<p><strong>Acción inmediata</strong></p><ul><li>2-3 acciones concretas y específicas para este caso</li></ul>

REGLAS:
- Usa SOLO etiquetas HTML: p, ul, li, strong, em. NUNCA uses asteriscos (*) ni markdown.
- SIEMPRE menciona NOMBRES REALES de leads y visitantes tal como aparecen en los datos.
- Si no hay leads directos, menciona los potenciales indicando que son clientes sin propiedad asignada.
- Si no hay visitas/leads de ningún tipo, escribe exactamente: <li>Sin registros aún.</li>
- Máximo 380 palabras. Sin CSS inline. Sin texto fuera de las etiquetas HTML.

DATOS:
{context_text}

Responde ÚNICAMENTE el bloque HTML. Nada más."""

        try:
            html = self.env['estate.genai.mixin']._genai_generate(
                prompt, temperature=0.35, max_output_tokens=6144,
            )
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
                    'title': 'Análisis actualizado',
                    'message': 'El análisis ejecutivo IA se generó con todos los datos disponibles.',
                    'type': 'success',
                    'sticky': False,
                    'next': {'type': 'ir.actions.client', 'tag': 'reload'},
                }
            }
        except Exception as e:
            _logger.error("Error generando análisis IA: %s", str(e))
            raise UserError(_("Error al generar análisis: %s") % str(e))

    # ── Computed visual fields for "Asistente IA" tab ─────────────────────
    avm_gauge_html = fields.Html(
        string='Gauge AVM vs Precio',
        compute='_compute_avm_gauge_html',
        store=False,
    )
    interesting_leads_html = fields.Html(
        string='Panel Leads Interesados',
        compute='_compute_interesting_leads_html',
        store=False,
    )
    similar_properties_html = fields.Html(
        string='Propiedades Similares',
        compute='_compute_similar_properties_html',
        store=False,
    )

    @api.depends('price', 'write_date')
    def _compute_avm_gauge_html(self):
        for prop in self:
            avm = getattr(prop, 'avm_estimated_price', 0) or 0
            price = prop.price or 0
            if not avm or not price:
                prop.avm_gauge_html = False
                continue
            diff_pct = ((price - avm) / avm) * 100
            status = getattr(prop, 'avm_status', '') or ''
            color = {'fair': '#00897B', 'high': '#E53935', 'low': '#FF9800'}.get(status, '#888')
            label = {
                'fair': '&#10003; En rango de mercado',
                'high': '&#8593; Precio alto vs. mercado',
                'low': '&#8595; Precio bajo vs. mercado',
            }.get(status, 'Sin clasificar')
            max_val = max(price, avm)
            price_w = round((price / max_val) * 100, 1)
            avm_w = round((avm / max_val) * 100, 1)
            sign = '+' if diff_pct >= 0 else ''
            prop.avm_gauge_html = (
                '<div style="font-size:12px;color:#555;padding:4px 0">'
                '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">'
                '<b style="color:#333;font-size:12.5px">Precio vs. Valoraci&#243;n de Mercado (AVM)</b>'
                f'<span style="background:{color}1a;color:{color};border-radius:20px;padding:2px 10px;font-weight:700;font-size:11px">{label}</span>'
                '</div>'
                '<div style="margin-bottom:7px">'
                '<div style="display:flex;justify-content:space-between;margin-bottom:3px">'
                f'<span>Precio actual</span><b style="color:#004274">${price:,.0f}</b>'
                '</div>'
                '<div style="background:#eef0f3;border-radius:10px;height:14px;overflow:hidden">'
                f'<div style="background:#004274;width:{price_w}%;height:100%;border-radius:10px;transition:width .6s"></div>'
                '</div></div>'
                '<div style="margin-bottom:7px">'
                '<div style="display:flex;justify-content:space-between;margin-bottom:3px">'
                f'<span>Estimado IA (AVM)</span><b style="color:{color}">${avm:,.0f}</b>'
                '</div>'
                '<div style="background:#eef0f3;border-radius:10px;height:14px;overflow:hidden">'
                f'<div style="background:{color};width:{avm_w}%;height:100%;border-radius:10px;transition:width .6s"></div>'
                '</div></div>'
                f'<div style="text-align:right;font-weight:700;color:{color};font-size:11.5px;margin-top:4px">'
                f'Diferencia: {sign}{diff_pct:.1f}%</div>'
                '</div>'
            )

    @api.depends('price', 'property_type_id', 'write_date')
    def _compute_similar_properties_html(self):
        for prop in self:
            if not prop.id or not prop.property_type_id or not (prop.price or 0):
                prop.similar_properties_html = '<p style="color:#aaa;font-size:12px;margin:0">Defina tipo y precio para ver similares.</p>'
                continue
            pmin = prop.price * 0.65
            pmax = prop.price * 1.45
            similar = self.env['estate.property'].sudo().search([
                ('id', '!=', prop.id),
                ('state', '=', 'available'),
                ('property_type_id', '=', prop.property_type_id.id),
                ('price', '>=', pmin),
                ('price', '<=', pmax),
            ], order='price asc', limit=5)
            if not similar:
                prop.similar_properties_html = '<p style="color:#aaa;font-size:12px;margin:0">No hay propiedades similares disponibles en este rango de precio.</p>'
                continue
            rows = ''
            for s in similar:
                diff = ((s.price - prop.price) / prop.price * 100) if prop.price else 0
                diff_clr = '#E53935' if diff > 5 else ('#00897B' if diff < -5 else '#888')
                sign = '+' if diff >= 0 else ''
                href = f'/odoo/estate-management/{s.id}'
                rows += (
                    f'<tr style="border-bottom:1px solid #f0f2f5">'
                    f'<td style="padding:6px 8px;font-size:11.5px"><a href="{href}" style="color:#004274;font-weight:600">{s.name or ""}</a>'
                    f'{"<br/><span style=\'color:#999;font-size:10.5px\'>" + s.title + "</span>" if s.title else ""}</td>'
                    f'<td style="padding:6px 8px;font-size:11px;color:#666">{s.city or ""}</td>'
                    f'<td style="padding:6px 8px;font-size:11.5px;text-align:right"><b style="color:#004274">${s.price:,.0f}</b></td>'
                    f'<td style="padding:6px 8px;font-size:11px;text-align:right;font-weight:700;color:{diff_clr}">{sign}{diff:.0f}%</td>'
                    f'<td style="padding:6px 8px;font-size:11px;color:#777">{s.area or 0}m&#178; · {s.bedrooms or 0}h · {s.bathrooms or 0}b</td>'
                    f'</tr>'
                )
            prop.similar_properties_html = (
                '<table style="width:100%;border-collapse:collapse;font-family:inherit">'
                '<tr style="background:#f8f9fb">'
                '<th style="padding:6px 8px;text-align:left;font-size:10.5px;color:#888;font-weight:700;text-transform:uppercase;letter-spacing:.4px">Propiedad</th>'
                '<th style="padding:6px 8px;text-align:left;font-size:10.5px;color:#888;font-weight:700;text-transform:uppercase;letter-spacing:.4px">Ciudad</th>'
                '<th style="padding:6px 8px;text-align:right;font-size:10.5px;color:#888;font-weight:700;text-transform:uppercase;letter-spacing:.4px">Precio</th>'
                '<th style="padding:6px 8px;text-align:right;font-size:10.5px;color:#888;font-weight:700;text-transform:uppercase;letter-spacing:.4px">Dif.</th>'
                '<th style="padding:6px 8px;text-align:left;font-size:10.5px;color:#888;font-weight:700;text-transform:uppercase;letter-spacing:.4px">Detalles</th>'
                f'</tr>{rows}</table>'
            )

    @api.depends('price', 'write_date')
    def _compute_interesting_leads_html(self):
        for prop in self:
            if not prop.id:
                prop.interesting_leads_html = False
                continue
            if 'target_property_id' not in self.env['crm.lead']._fields:
                prop.interesting_leads_html = '<p style="color:#aaa;font-size:12px;margin:0">M&#243;dulo CRM no disponible.</p>'
                continue
            temp_map = {
                'cold': ('Fr&#237;o', '#90A4AE'),
                'warm': ('Tibio', '#FF9800'),
                'hot': ('Caliente', '#E53935'),
                'boiling': ('Hirviendo!', '#B71C1C'),
            }
            direct = self.env['crm.lead'].sudo().search([
                ('target_property_id', '=', prop.id),
                ('active', '=', True),
            ], order='create_date desc', limit=8)
            potential = self.env['crm.lead']
            if prop.price and len(direct) < 4 and 'client_budget' in self.env['crm.lead']._fields:
                pmin = prop.price * 0.75
                pmax = prop.price * 1.30
                potential = self.env['crm.lead'].sudo().search([
                    ('target_property_id', '=', False),
                    ('active', '=', True),
                    ('type', '=', 'opportunity'),
                    ('client_budget', '>=', pmin),
                    ('client_budget', '<=', pmax),
                ], limit=4)
            if not direct and not potential:
                prop.interesting_leads_html = '<p style="color:#aaa;font-size:12px;margin:0">Sin leads asignados o compatibles con el precio.</p>'
                continue
            rows = ''
            for l in list(direct) + list(potential):
                is_direct = l in direct
                nombre = (l.partner_id.name if l.partner_id else None) or getattr(l, 'partner_name', None) or l.name or 'Sin nombre'
                budget_val = getattr(l, 'client_budget', 0) or 0
                budget_str = f'${budget_val:,.0f}' if budget_val else 'N/A'
                temp = getattr(l, 'lead_temperature', '') or ''
                temp_label, temp_clr = temp_map.get(temp, ('&#8212;', '#999'))
                stage = l.stage_id.name if l.stage_id else 'Sin etapa'
                badge_bg = '#e3f2fd' if is_direct else '#fff8e1'
                badge_txt = 'ASIGNADO' if is_direct else 'POTENCIAL'
                badge_clr = '#1565C0' if is_direct else '#E65100'
                rows += (
                    f'<tr style="border-bottom:1px solid #f0f2f5">'
                    f'<td style="padding:6px 8px;font-size:11.5px;font-weight:600;color:#333">{nombre}</td>'
                    f'<td style="padding:6px 8px;font-size:11px">'
                    f'<span style="background:{badge_bg};color:{badge_clr};border-radius:10px;padding:1px 7px;font-size:10px;font-weight:700">{badge_txt}</span></td>'
                    f'<td style="padding:6px 8px;font-size:11.5px;text-align:right;font-weight:600">{budget_str}</td>'
                    f'<td style="padding:6px 8px;font-size:11px;font-weight:700;color:{temp_clr}">{temp_label}</td>'
                    f'<td style="padding:6px 8px;font-size:11px;color:#777">{stage}</td>'
                    f'</tr>'
                )
            prop.interesting_leads_html = (
                f'<div style="font-size:11px;color:#888;margin-bottom:6px">'
                f'{len(direct)} asignado(s) directamente &#183; {len(potential)} potencial(es) por presupuesto</div>'
                '<table style="width:100%;border-collapse:collapse;font-family:inherit">'
                '<tr style="background:#f8f9fb">'
                '<th style="padding:6px 8px;text-align:left;font-size:10.5px;color:#888;font-weight:700;text-transform:uppercase;letter-spacing:.4px">Cliente</th>'
                '<th style="padding:6px 8px;text-align:left;font-size:10.5px;color:#888;font-weight:700;text-transform:uppercase;letter-spacing:.4px">Tipo</th>'
                '<th style="padding:6px 8px;text-align:right;font-size:10.5px;color:#888;font-weight:700;text-transform:uppercase;letter-spacing:.4px">Presupuesto</th>'
                '<th style="padding:6px 8px;text-align:left;font-size:10.5px;color:#888;font-weight:700;text-transform:uppercase;letter-spacing:.4px">Temp.</th>'
                '<th style="padding:6px 8px;text-align:left;font-size:10.5px;color:#888;font-weight:700;text-transform:uppercase;letter-spacing:.4px">Etapa</th>'
                f'</tr>{rows}</table>'
            )

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
