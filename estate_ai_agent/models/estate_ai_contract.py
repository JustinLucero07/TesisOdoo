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
        seller = (prop.owner_id.name if prop and prop.owner_id else self.env.company.name)

        c_type = {
            'sale': 'de Compraventa',
            'exclusivity': 'de Exclusividad Inmobiliaria',
        }.get(self.contract_type, 'Inmobiliario')

        # Generar-o-mejorar: si ya hay un borrador, lo mejora coherentemente.
        existing = (self.notes or '').strip()
        if existing:
            modo = (
                "El contrato YA tiene un borrador. MEJÓRALO y complétalo de forma COHERENTE: "
                "no repitas cláusulas, no te contradigas y mantén la numeración continua.\n\n"
                f"--- BORRADOR ACTUAL ---\n{existing}\n--- FIN DEL BORRADOR ---\n"
            )
        else:
            modo = "Redacta el contrato completo desde cero."

        prompt = f"""
Actúa como un abogado experto en bienes raíces en Ecuador.
{modo}
Redacta un Contrato {c_type} profesional, COHERENTE y SIN cláusulas repetidas.

PARTES:
- VENDEDOR/ARRENDADOR: {seller}
- COMPRADOR/ARRENDATARIO: {client_partner.name or 'No especificado'} (Cédula/RUC: {client_partner.vat or 'No especificado'})
  Dirección: {client_partner.street or ''}, {client_partner.city or 'Ecuador'}

DATOS DEL CONTRATO:
- Referencia: {self.name}
- Monto: ${self.amount:,.2f}
- Vigencia: {self.date_start} a {self.date_end or 'No especificada'}

PROPIEDAD:
- {prop.title if prop else '-'} — {prop.street or ''}, {prop.city or ''}
- Área: {prop.area or 'N/D'} m² · Habitaciones: {prop.bedrooms or 'N/A'} · Piso: {prop.floor or 'N/A'}
- Referencia interna: {prop.name if prop else '-'}

INSTRUCCIONES:
1. Lenguaje legal formal ecuatoriano.
2. Cláusulas numeradas y ordenadas (PRIMERA: Comparecientes/Partes, SEGUNDA: Objeto,
   TERCERA: Precio y forma de pago, CUARTA: Obligaciones, QUINTA: Plazo, SEXTA: Penalidades,
   SÉPTIMA: Terminación...). Cada cláusula trata UN solo tema, sin repetir ni contradecir.
3. Usa los datos reales de arriba; donde falte un dato deja un marcador entre corchetes
   (ej: [Forma de pago a convenir]) — NO inventes cifras ni nombres.
4. Formato HTML válido: <h2>, <h3>, <p>, <ul>, <li>, <b>, <br/>. Sin bloques ```html.
5. Termina con una sección de FIRMAS (Vendedor / Comprador) con líneas para firma y fecha.
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
