from odoo import models, fields, api
from odoo.exceptions import UserError


class EstateAIContract(models.Model):
    _inherit = 'estate.contract'

    def action_generate_contract_ai(self):
        """Usa Gemini para redactar un borrador de contrato en HTML."""
        self.ensure_one()

        if not self.env['estate.genai.mixin']._genai_is_active():
            raise UserError("El Agente de IA está desactivado en Configuración > Agente IA.")

        client_partner = self.partner_id
        prop = self.property_id

        c_type = {
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
            # Los contratos legales SÍ se benefician del razonamiento (thinking=True)
            generated_html = self.env['estate.genai.mixin']._genai_generate(
                prompt, temperature=0.3, max_output_tokens=8192, thinking=True,
            )
            generated_html = self.env['estate.genai.mixin']._genai_strip_fences(generated_html)

            self.write({'notes': generated_html})
            self.message_post(
                body='Borrador de contrato redactado automáticamente por <strong>Gemini</strong>.',
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
