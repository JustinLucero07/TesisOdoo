from odoo import models, fields, api
from odoo.exceptions import UserError

try:
    from google import genai
    from google.genai import types as genai_types
    NEW_GENAI_OK = True
except ImportError:
    NEW_GENAI_OK = False


class EstateAIContract(models.Model):
    _inherit = 'estate.contract'

    def action_generate_contract_ai(self):
        """Usa Gemini (v1 / gemini-1.5-flash) para redactar un borrador de contrato en HTML."""
        self.ensure_one()

        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param('estate_ai.active', 'True') != 'True':
            raise UserError("El Agente de IA está desactivado en Configuración > Agente IA.")

        api_key = ICP.get_param('estate_ai.api_key', '')
        if not api_key:
            raise UserError("No hay API Key configurada. Vaya a Configuración > Agente IA.")

        if not NEW_GENAI_OK:
            raise UserError("La librería google-genai no está instalada. Ejecute: pip install google-genai")

        client_partner = self.partner_id
        prop = self.property_id

        c_type = {
            'rent': 'de Arrendamiento',
            'sale': 'de Compraventa',
            'exclusivity': 'de Exclusividad Inmobiliaria',
        }.get(self.contract_type, 'Inmobiliario')

        prompt = f"""
Actúa como un abogado experto en bienes raíces corporativos en Ecuador.
Redacta un Borrador de Contrato {c_type} profesional y detallado.

DATOS DEL CONTRATO:
- Referencia: {self.name}
- Fecha de Inicio: {self.date_start}
- Fecha de Vencimiento: {self.date_end or 'No especificada'}
- Monto del Contrato: ${self.amount:,.2f}

DATOS DEL CLIENTE:
- Nombre: {client_partner.name}
- Cédula/RUC: {client_partner.vat or 'No especificado'}
- Dirección: {client_partner.street or ''}, {client_partner.city or 'Ecuador'}

DATOS DE LA PROPIEDAD:
- Título: {prop.title}
- Dirección: {prop.street or ''}, {prop.city or ''}
- Referencia Interna: {prop.name}
- Área (m²): {prop.area or 'No especificado'}
- Habitaciones: {prop.bedrooms or 'No aplica'}
- Piso: {prop.floor or 'No aplica'}

INSTRUCCIONES DE FORMATO:
1. Usa lenguaje legal formal propio del Ecuador.
2. Incluye cláusulas estándar: partes, objeto, obligaciones, pagos, penalidades, terminación.
3. Formatea ÚNICAMENTE en HTML válido con etiquetas <h2>, <h3>, <p>, <ul>, <li>, <b>, <br/>.
4. No incluyas bloques ```html — comienza directamente con la primera etiqueta HTML.
5. Termina con sección de firmas con espacios para firma/fecha.
"""

        try:
            # Use configured model with fallback
            model_name = ICP.get_param('estate_ai.model', 'gemini-2.5-flash')
            if not model_name or model_name in ['gemini-1.5-flash', 'gemini-2.0-flash', 'gemini-pro', 'gemini-flash-latest']:
                model_name = 'gemini-2.5-flash'
            
            if model_name.startswith('models/'):
                model_name = model_name.replace('models/', '')

            client = genai.Client(
                api_key=api_key,
                http_options=genai_types.HttpOptions(api_version='v1beta'),
            )
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=4096,
                ),
            )
            generated_html = (response.text or '').strip()
            generated_html = generated_html.replace('```html', '').replace('```', '').strip()

            self.write({'notes': generated_html})
            self.message_post(
                body='📄 Borrador de contrato redactado automáticamente por <strong>Gemini 1.5 Flash</strong>.',
                message_type='notification',
            )
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': '¡Contrato generado!',
                    'message': 'El borrador HTML fue redactado por IA y guardado en "Notas/Cláusulas".',
                    'type': 'success',
                    'sticky': False,
                },
            }
        except Exception as e:
            raise UserError(f"Error al conectar con Gemini: {str(e)}")
