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
        """Mejora 3: Genera descripcion comercial de marketing con IA (3 tonos)."""
        self.ensure_one()
        if not GOOGLE_GENAI_AVAILABLE:
            raise UserError(_("La libreria 'google-genai' no esta instalada."))

        ICP = self.env['ir.config_parameter'].sudo()
        api_key = ICP.get_param('estate_ai.api_key', '')
        if not api_key:
            raise UserError(_("No se ha configurado la API Key. Vaya a Configuracion > Agente IA."))

        prop = self
        detalles = (
            f"Tipo: {prop.property_type_id.name if prop.property_type_id else 'Inmueble'}\n"
            f"Ciudad: {prop.city or ''} | Sector: {prop.street or ''}\n"
            f"Area: {prop.area or 0} m2 | Habitaciones: {prop.bedrooms or 0} | Banos: {prop.bathrooms or 0}\n"
            f"Precio: ${prop.price:,.2f}\n"
            f"Estado: {'En venta' if prop.offer_type == 'sale' else 'En arriendo'}\n"
            f"Caracteristicas adicionales: {prop.description or 'No especificadas'}"
        )

        prompt = f"""
Eres un experto en marketing inmobiliario de alto nivel. Con los datos de esta propiedad,
genera una descripcion comercial en TRES versiones, cada una para un publico distinto.
Responde UNICAMENTE en JSON valido con esta estructura:

{{
  "formal": "Descripcion de 3-4 oraciones para inversores o instituciones bancarias. Tono profesional, menciona rentabilidad y plusvalia.",
  "emocional": "Descripcion de 3-4 oraciones para familias. Evoca el hogar, la seguridad, el futuro.",
  "directo": "Descripcion de 2-3 oraciones para compradores rapidos. Destaca el valor y la urgencia.",
  "headline_1": "Titular corto y potente (max 8 palabras) -- version A",
  "headline_2": "Titular corto y potente (max 8 palabras) -- version B",
  "headline_3": "Titular corto y potente (max 8 palabras) -- version C"
}}

DATOS DE LA PROPIEDAD:
{detalles}
"""
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
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=genai.types.GenerateContentConfig(temperature=0.8, max_output_tokens=1500),
            )
            import json
            import re
            raw = response.text.strip().replace('```json', '').replace('```', '').strip()

            # Robust JSON parsing: try direct parse first, then attempt repairs
            result = None
            try:
                result = json.loads(raw)
            except json.JSONDecodeError:
                _logger.warning("JSON directo fallo, intentando reparar respuesta truncada de Gemini...")
                # Attempt 1: fix unterminated strings and unclosed braces
                repaired = raw
                # If odd number of quotes, close the last open string
                if repaired.count('"') % 2 != 0:
                    repaired = repaired.rstrip().rstrip(',') + '"'
                # Close any unclosed braces
                open_braces = repaired.count('{') - repaired.count('}')
                if open_braces > 0:
                    repaired = repaired.rstrip().rstrip(',') + '}' * open_braces
                try:
                    result = json.loads(repaired)
                    _logger.info("JSON reparado exitosamente (cierre de llaves/comillas).")
                except json.JSONDecodeError:
                    pass

            # Attempt 2: regex extraction of individual fields
            if result is None:
                _logger.warning("Reparacion JSON fallo, extrayendo campos con regex...")
                result = {}
                for field_name in ('formal', 'emocional', 'directo', 'headline_1', 'headline_2', 'headline_3'):
                    match = re.search(
                        r'"' + field_name + r'"\s*:\s*"((?:[^"\\]|\\.)*)"',
                        raw, re.DOTALL
                    )
                    if match:
                        result[field_name] = match.group(1).replace('\\n', '\n').replace('\\"', '"')
                if not any(result.values()):
                    raise UserError(_("La IA devolvio una respuesta que no se pudo interpretar. Intente de nuevo."))

            formal = result.get('formal', '')
            emocional = result.get('emocional', '')
            directo = result.get('directo', '')
            h1 = result.get('headline_1', '')
            h2 = result.get('headline_2', '')
            h3 = result.get('headline_3', '')

            combined = (
                f"--- VERSION FORMAL (Inversores/Banco) ---\n{formal}\n\n"
                f"--- VERSION EMOCIONAL (Familias) ---\n{emocional}\n\n"
                f"--- VERSION DIRECTA (Cierre rapido) ---\n{directo}\n\n"
                f"--- TITULARES PARA WORDPRESS/REDES ---\n"
                f"A: {h1}\nB: {h2}\nC: {h3}"
            )

            prop.ai_marketing_description = combined

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Descripcion generada!',
                    'message': 'La descripcion comercial IA fue creada. Revisala en la pestana Inteligencia Artificial.',
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.error("Error en generador de descripcion IA: %s", str(e))
            raise UserError(_("Error al generar descripcion: %s") % str(e))
