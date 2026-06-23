# -*- coding: utf-8 -*-
"""Helper centralizado para Google Gemini.

Toda la lógica de cliente, reintentos, desactivación del "thinking" (que
consumía el presupuesto de tokens y truncaba respuestas) y extracción robusta
de texto vive aquí. Cualquier modelo lo usa vía:

    self.env['estate.genai.mixin']._genai_generate("mi prompt", ...)

Antes esta configuración estaba duplicada (y desincronizada) en
estate_property, estate_ai_contract, estate_document y estate_dashboard.
"""
import logging

from odoo import api, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    from google import genai
    GENAI_OK = True
except ImportError:
    GENAI_OK = False

# Modelos antiguos/deprecados que deben normalizarse al actual
_LEGACY_MODELS = {
    'gemini-1.5-flash', 'gemini-2.0-flash', 'gemini-pro',
    'gemini-flash-latest', 'gemini-1.5-pro',
}
_DEFAULT_MODEL = 'gemini-2.5-flash'


class EstateGenaiMixin(models.AbstractModel):
    _name = 'estate.genai.mixin'
    _description = 'Helper centralizado para Google Gemini'

    # ── Disponibilidad / credenciales ────────────────────────────────────────
    @api.model
    def _genai_available(self):
        return GENAI_OK

    @api.model
    def _genai_api_key(self):
        return self.env['ir.config_parameter'].sudo().get_param('estate_ai.api_key', '')

    @api.model
    def _genai_is_active(self):
        return self.env['ir.config_parameter'].sudo().get_param('estate_ai.active', 'True') == 'True'

    @api.model
    def _genai_model_name(self, override=None):
        """Devuelve el modelo a usar, normalizando nombres viejos."""
        name = override or self.env['ir.config_parameter'].sudo().get_param(
            'estate_ai.model', _DEFAULT_MODEL)
        if not name or name in _LEGACY_MODELS:
            name = _DEFAULT_MODEL
        if name.startswith('models/'):
            name = name.replace('models/', '')
        return name

    # ── Cliente ──────────────────────────────────────────────────────────────
    @api.model
    def _genai_client(self, with_retries=True):
        if not GENAI_OK:
            raise UserError(_(
                "La librería 'google-genai' no está instalada. "
                "Ejecute: pip install google-genai"))
        api_key = self._genai_api_key()
        if not api_key:
            raise UserError(_(
                "No se ha configurado la API Key de Gemini. "
                "Vaya a Configuración > Agente IA."))
        http_kwargs = {'api_version': 'v1beta'}
        if with_retries:
            http_kwargs['retry_options'] = genai.types.HttpRetryOptions(
                attempts=3, initial_delay=2.0, max_delay=30.0,
                http_status_codes=[429, 500, 502, 503, 504])
        return genai.Client(
            api_key=api_key,
            http_options=genai.types.HttpOptions(**http_kwargs))

    # ── Generación ───────────────────────────────────────────────────────────
    @api.model
    def _genai_generate(self, prompt, *, model=None, temperature=0.7,
                        max_output_tokens=8192, thinking=False,
                        image_bytes=None, image_mime='image/jpeg',
                        inline_data=None, system_instruction=None):
        """Genera texto con Gemini de forma robusta y centralizada.

        :param prompt: texto del prompt
        :param thinking: si False (por defecto) se desactiva el razonamiento de
            Gemini 2.5 (que consume tokens de salida y trunca respuestas)
        :param image_bytes: bytes crudos de una imagen para análisis visual
        :param inline_data: dict {'mime_type', 'data'} para documentos (PDF, etc.)
        :returns: str con el texto (nunca vacío)
        :raises UserError: con mensaje claro si la IA falla o no devuelve nada
        """
        client = self._genai_client()

        if image_bytes is not None:
            contents = [prompt, genai.types.Part.from_bytes(
                data=image_bytes, mime_type=image_mime)]
        elif inline_data is not None:
            contents = [{'parts': [
                {'inline_data': inline_data},
                {'text': prompt},
            ]}]
        else:
            contents = prompt

        cfg_kwargs = {
            'temperature': temperature,
            'max_output_tokens': max_output_tokens,
        }
        if not thinking:
            cfg_kwargs['thinking_config'] = genai.types.ThinkingConfig(thinking_budget=0)
        if system_instruction:
            cfg_kwargs['system_instruction'] = system_instruction

        try:
            response = client.models.generate_content(
                model=self._genai_model_name(model),
                contents=contents,
                config=genai.types.GenerateContentConfig(**cfg_kwargs),
            )
        except Exception as e:
            _logger.error("Gemini generate_content falló: %s", e)
            raise UserError(_("Error al conectar con la IA: %s") % str(e))

        text = (getattr(response, 'text', None) or '').strip()
        if not text:
            reason = ''
            try:
                reason = str(response.candidates[0].finish_reason)
            except Exception:
                _logger.debug("Excepcion ignorada (best-effort)", exc_info=True)
            raise UserError(_(
                "La IA no devolvió contenido%s. Intenta de nuevo o ajusta los datos."
            ) % (f" (motivo: {reason})" if reason else ""))
        return text

    # ── Utilidades ───────────────────────────────────────────────────────────
    @api.model
    def _genai_strip_fences(self, text):
        """Quita bloques markdown ```html / ```json que a veces añade Gemini."""
        t = (text or '').strip()
        for fence in ('```html', '```json', '```'):
            if t.startswith(fence):
                t = t[len(fence):].strip()
                break
        return t.replace('```', '').strip()
