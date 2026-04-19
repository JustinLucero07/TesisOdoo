import logging
import urllib.parse

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    partner_id = fields.Many2one(
        'res.partner', string='Cliente')
    property_id = fields.Many2one(
        'estate.property', string='Propiedad')

    appointment_type = fields.Selection([
        ('visit', 'Visita'),
        ('meeting', 'Reunión'),
        ('call', 'Llamada'),
        ('signing', 'Firma de Contrato'),
    ], string='Tipo de Cita', default='visit')

    visit_state = fields.Selection([
        ('scheduled', 'Programada'),
        ('done', 'Realizada'),
        ('cancelled', 'Cancelada'),
    ], string='Estado de la Visita', default='scheduled')

    # --- Resultado (se llena al marcar como Realizada) ---
    visit_result = fields.Selection([
        ('interested', 'Interesado'),
        ('not_interested', 'No Interesado'),
        ('follow_up', 'Seguimiento'),
        ('offer_made', 'Oferta Realizada'),
    ], string='Resultado de la Visita')

    visit_rating = fields.Selection([
        ('1', '1 - Muy malo'),
        ('2', '2 - Malo'),
        ('3', '3 - Regular'),
        ('4', '4 - Bueno'),
        ('5', '5 - Excelente'),
    ], string='Valoracion del Cliente')

    visit_notes = fields.Text(string='Notas / Observaciones de la Visita')

    # --- Lead CRM de origen ---
    lead_id = fields.Many2one(
        'crm.lead', string='Lead de Origen',
        help='Oportunidad CRM relacionada con esta visita.')

    # --- WhatsApp ---
    whatsapp_sent = fields.Boolean(
        string='Recordatorio WhatsApp Enviado', default=False,
        help='Se marca automáticamente cuando se envía el recordatorio.')
    # Mejora 9: Encuesta post-visita
    survey_sent = fields.Boolean(
        string='Encuesta Enviada', default=False,
        help='Marca cuando se envió la encuesta de satisfacción post-visita.')

    def _get_related_lead(self):
        """Busca el lead CRM relacionado con este evento (por lead_id o por partner+propiedad)."""
        self.ensure_one()
        if self.lead_id:
            return self.lead_id
        if self.partner_id:
            lead = self.env['crm.lead'].sudo().search([
                ('partner_id', '=', self.partner_id.id),
                ('stage_id.is_won', '=', False),
            ], limit=1)
            return lead
        return self.env['crm.lead']

    @api.model_create_multi
    def create(self, vals_list):
        events = super().create(vals_list)
        for event in events:
            if event.appointment_type in ('visit', 'signing') or event.property_id:
                lead = event._get_related_lead()
                if lead:
                    lead._advance_lead_to_stage('estate_crm.stage_lead3_estate')
        return events

    def action_done_visit(self):
        for event in self:
            event.write({'visit_state': 'done'})

            # Auto-avanzar lead a "Visita Realizada"
            lead = event._get_related_lead()
            if lead:
                lead._advance_lead_to_stage('estate_crm.stage_lead4_estate')

            # 1. Actualizar temperatura CRM si se hizo una oferta
            if event.visit_result == 'offer_made' and event.partner_id:
                leads = self.env['crm.lead'].sudo().search([
                    ('partner_id', '=', event.partner_id.id),
                    ('stage_id.is_won', '=', False),
                ], limit=1)
                if leads:
                    leads.write({'lead_temperature': 'boiling'})
                    leads.message_post(
                        body=f'🔥 Temperatura actualizada a HIRVIENDO: oferta realizada durante visita a "{event.property_id.title or ""}".')

            # 2. Crear actividad de seguimiento si la valoración fue baja
            if event.visit_rating and int(event.visit_rating) <= 2 and event.property_id:
                result_label = dict(self._fields['visit_result'].selection).get(event.visit_result, 'N/A')
                event.property_id.activity_schedule(
                    'mail.mail_activity_data_todo',
                    date_deadline=fields.Date.today(),
                    summary=f'⚠️ Visita con calificación baja ({event.visit_rating}/5) — {event.partner_id.name or "Cliente"}',
                    note=(
                        f'La visita a "{event.property_id.title}" recibió calificación {event.visit_rating}/5. '
                        f'Resultado: {result_label}. '
                        f'Notas: {event.visit_notes or "Sin notas"}. '
                        f'Se recomienda contactar al cliente para entender sus objeciones.'
                    ),
                    user_id=event.property_id.user_id.id or self.env.uid,
                )

            # 3. Enviar WhatsApp de seguimiento al cliente
            if event.partner_id and event.property_id:
                self._send_followup_whatsapp(event)

            # 4. Recomputar visitas completadas en leads relacionados para scoring preciso
            if event.partner_id:
                related_leads = self.env['crm.lead'].sudo().search([
                    ('partner_id', '=', event.partner_id.id),
                ])
                for lead in related_leads:
                    count = self.env['calendar.event'].sudo().search_count([
                        ('partner_id', '=', lead.partner_id.id),
                        ('visit_state', '=', 'done'),
                    ])
                    lead.completed_visits_count = count

    def _send_followup_whatsapp(self, event):
        """Envía WhatsApp de seguimiento post-visita al cliente via Meta Cloud API."""
        try:
            phone = event.partner_id.mobile or event.partner_id.phone
            if not phone:
                return
            prop_title = event.property_id.title or event.property_id.name
            client_name = event.partner_id.name or 'estimado/a cliente'
            msg = (
                f"Hola {client_name},\n"
                f"Gracias por visitar {prop_title}.\n"
                f"Que le parecio la propiedad? Estamos disponibles para cualquier consulta.\n"
                f"Saludos del equipo Inmobiliario."
            )
            self._send_whatsapp_text(phone, msg)
        except Exception as e:
            _logger.warning("Error en WhatsApp de seguimiento post-visita: %s", e)

    def action_send_whatsapp_followup(self):
        """Botón manual: envía WhatsApp de seguimiento post-visita al cliente."""
        self.ensure_one()
        if not self.partner_id or not (self.partner_id.mobile or self.partner_id.phone):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Sin teléfono',
                    'message': 'El cliente no tiene número de móvil configurado.',
                    'type': 'warning', 'sticky': False,
                }
            }
        self._send_followup_whatsapp(self)
        self.write({'whatsapp_sent': True})

    def action_cancel_visit(self):
        self.write({'visit_state': 'cancelled'})

    def action_schedule_visit(self):
        self.write({'visit_state': 'scheduled'})

    # --- Mejora 9: Encuesta post-visita por WhatsApp ---
    def action_send_survey_whatsapp(self):
        """Mejora 9: Envía encuesta de satisfacción post-visita por WhatsApp (wa.me link)."""
        self.ensure_one()
        if not self.partner_id or not (self.partner_id.mobile or self.partner_id.phone):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Sin teléfono',
                    'message': 'El cliente no tiene número de móvil configurado.',
                    'type': 'warning', 'sticky': False,
                }
            }
        import urllib.parse
        prop_title = self.property_id.title if self.property_id else 'la propiedad'
        client_name = self.partner_id.name or 'estimado cliente'
        asesor = self.user_id.name if self.user_id else 'nuestro asesor'
        msg = (
            f"¡Hola {client_name}! 🏠\n\n"
            f"Gracias por tu visita a *{prop_title}*.\n"
            f"Tu opinión nos importa mucho. ¿Podrías calificar tu experiencia?\n\n"
            f"⭐ 1 - Muy mala\n"
            f"⭐⭐ 2 - Mala\n"
            f"⭐⭐⭐ 3 - Regular\n"
            f"⭐⭐⭐⭐ 4 - Buena\n"
            f"⭐⭐⭐⭐⭐ 5 - Excelente\n\n"
            f"Solo responde con el número de estrellas (1-5).\n"
            f"Atendido por: {asesor}\n"
            f"¡Gracias! 🙏"
        )
        number = (self.partner_id.mobile or self.partner_id.phone or '').replace(' ', '').replace('-', '').replace('+', '')
        wa_url = f"https://wa.me/{number}?text={urllib.parse.quote(msg)}"
        self.write({'survey_sent': True})
        return {
            'type': 'ir.actions.act_url',
            'url': wa_url,
            'target': 'new',
        }
