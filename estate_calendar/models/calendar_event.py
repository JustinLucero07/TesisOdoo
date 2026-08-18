import logging
import urllib.parse

from odoo import models, fields, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

# Unidades para elegir la anticipación del recordatorio (cita / asesor / general).
REMINDER_UNITS = [
    ('minutes', 'Minutos'),
    ('hours', 'Horas'),
    ('days', 'Días'),
]
_UNIT_MULTIPLIER = {'minutes': 1, 'hours': 60, 'days': 1440}


def reminder_to_minutes(value, unit):
    """Convierte (valor, unidad) a minutos. Único punto de conversión."""
    return int(value or 0) * _UNIT_MULTIPLIER.get(unit or 'minutes', 1)


class CalendarEvent(models.Model):
    _name = 'calendar.event'
    _inherit = ['calendar.event', 'estate.phone.mixin']

    client_id = fields.Many2one(
        'res.partner', string='Cliente',
        help='Contacto/cliente asociado a esta visita.')
    property_id = fields.Many2one(
        'estate.property', string='Propiedad', ondelete='set null')

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

    visit_color = fields.Integer(string='Color', compute='_compute_visit_color', store=True)

    @api.depends('visit_state', 'appointment_type')
    def _compute_visit_color(self):
        color_map = {
            'done': 10,       # verde
            'cancelled': 1,   # rojo
            'scheduled': 4,   # azul
        }
        type_map = {
            'signing': 7,     # violeta
            'call': 3,        # amarillo
            'meeting': 2,     # naranja
        }
        for rec in self:
            if rec.visit_state in ('done', 'cancelled'):
                rec.visit_color = color_map[rec.visit_state]
            elif rec.appointment_type in type_map:
                rec.visit_color = type_map[rec.appointment_type]
            else:
                rec.visit_color = 4

    # --- Datos rápidos de propiedad y cliente (para no tener que navegar) ---
    property_price = fields.Float(
        related='property_id.price', string='Precio', readonly=True)
    property_type_name = fields.Char(
        related='property_id.property_type_id.name', string='Tipo de Propiedad', readonly=True)
    property_owner_name = fields.Char(
        related='property_id.owner_id.name', string='Propietario', readonly=True)
    property_owner_phone = fields.Char(
        related='property_id.owner_id.phone', string='Tel. Propietario', readonly=True)
    client_phone = fields.Char(
        related='client_id.phone', string='Tel. Cliente', readonly=True)
    client_mobile = fields.Char(
        related='client_id.mobile', string='Cel. Cliente', readonly=True)

    # --- Lead CRM de origen ---
    lead_id = fields.Many2one(
        'crm.lead', string='Lead de Origen',
        help='Oportunidad CRM relacionada con esta visita.')

    # --- WhatsApp ---
    whatsapp_sent = fields.Boolean(
        string='Recordatorio WhatsApp Enviado', default=False,
        help='Se marca automáticamente cuando se envía el recordatorio.')
    whatsapp_reminder_value = fields.Integer(
        string='Recordar antes de',
        help='Con cuánta anticipación recordar ESTA cita (por WhatsApp y en Google '
             'Calendar). Vacío o 0 = usa el tiempo del asesor responsable, o el '
             'general de Ajustes si el asesor no configuró el suyo.')
    whatsapp_reminder_unit = fields.Selection(
        REMINDER_UNITS, string='Unidad', default='minutes')
    whatsapp_reminder_minutes = fields.Integer(
        string='Recordatorio (minutos)', store=True, readonly=True,
        compute='_compute_whatsapp_reminder_minutes',
        help='Equivalente en minutos de la anticipación elegida (uso interno).')

    @api.depends('whatsapp_reminder_value', 'whatsapp_reminder_unit')
    def _compute_whatsapp_reminder_minutes(self):
        for rec in self:
            rec.whatsapp_reminder_minutes = reminder_to_minutes(
                rec.whatsapp_reminder_value, rec.whatsapp_reminder_unit)

    @api.model
    def _global_reminder_minutes(self):
        """Anticipación general de Ajustes, en minutos."""
        ICP = self.env['ir.config_parameter'].sudo()
        value = ICP.get_param('estate_calendar.whatsapp_reminder_default_value')
        unit = ICP.get_param('estate_calendar.whatsapp_reminder_default_unit')
        if value:
            return reminder_to_minutes(int(value or 0), unit or 'minutes') or 60
        # Compatibilidad con la configuración anterior (solo minutos)
        return int(ICP.get_param('estate_calendar.whatsapp_reminder_default_minutes', '60') or 60)

    def _effective_reminder_minutes(self):
        """Minutos de anticipación efectivos para recordar esta cita, con esta
        prioridad: 1) lo configurado en la cita, 2) lo del asesor responsable,
        3) el valor general de Ajustes. Un único punto de verdad para que el
        recordatorio de WhatsApp y el de Google Calendar usen el MISMO tiempo."""
        self.ensure_one()
        if self.whatsapp_reminder_minutes:
            return self.whatsapp_reminder_minutes
        if self.user_id and self.user_id.whatsapp_reminder_minutes:
            return self.user_id.whatsapp_reminder_minutes
        return self._global_reminder_minutes()

    def _sync_reminder_alarm(self):
        """Pone en la cita el recordatorio NATIVO de Odoo con el mismo tiempo
        configurado, para que además del WhatsApp salte el aviso dentro de Odoo.

        Solo gestiona las alarmas creadas por nosotros (las que empiezan por
        'Inmobi:'), así que si el usuario añade las suyas a mano no se tocan."""
        Alarm = self.env['calendar.alarm'].sudo()
        for event in self:
            minutes = event._effective_reminder_minutes()
            # Quitar la alarma nuestra anterior (si el tiempo cambió)
            ours = event.alarm_ids.filtered(lambda a: (a.name or '').startswith('Inmobi:'))
            cmds = [(3, a.id) for a in ours]
            if minutes > 0:
                name = f'Inmobi: {minutes} min antes'
                alarm = Alarm.search([('name', '=', name)], limit=1)
                if not alarm:
                    alarm = Alarm.create({
                        'name': name,
                        'alarm_type': 'notification',
                        'interval': 'minutes',
                        'duration': minutes,
                    })
                if alarm not in ours:
                    cmds.append((4, alarm.id))
                else:
                    cmds = [c for c in cmds if c[1] != alarm.id]  # ya la tiene: no tocar
            if cmds:
                event.with_context(no_gcal_sync=True).write({'alarm_ids': cmds})

    # Mejora 9: Encuesta post-visita
    survey_sent = fields.Boolean(
        string='Encuesta Enviada', default=False,
        help='Marca cuando se envió la encuesta de satisfacción post-visita.')

    @api.constrains('start', 'user_id', 'property_id', 'appointment_type')
    def _check_advisor_availability(self):
        """Impide agendar una visita para un asesor en un día que marcó como
        no disponible (modelo estate.advisor.unavailability)."""
        Unavail = self.env['estate.advisor.unavailability'].sudo()
        for ev in self:
            # Solo aplica a visitas inmobiliarias con asesor y fecha
            if not ev.start or not ev.user_id:
                continue
            if 'property_id' in ev._fields and not ev.property_id \
                    and ev.appointment_type not in ('visit', 'signing'):
                continue
            day = fields.Datetime.context_timestamp(ev, ev.start).date()
            if Unavail.search_count([
                ('user_id', '=', ev.user_id.id),
                ('date_from', '<=', day),
                ('date_to', '>=', day),
            ]):
                raise ValidationError(
                    f"El asesor {ev.user_id.name} marcó el "
                    f"{day.strftime('%d/%m/%Y')} como día NO disponible. "
                    f"Elige otra fecha u otro asesor para esta cita."
                )

    def _get_related_lead(self):
        """Busca el lead CRM relacionado con este evento (por lead_id o por partner+propiedad)."""
        self.ensure_one()
        if self.lead_id:
            return self.lead_id
        if self.client_id:
            lead = self.env['crm.lead'].sudo().search([
                ('partner_id', '=', self.client_id.id),
                ('stage_id.is_won', '=', False),
            ], limit=1)
            return lead
        return self.env['crm.lead']

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'name' in fields_list and not res.get('name'):
            prop_id = res.get('property_id')
            if prop_id:
                prop = self.env['estate.property'].browse(prop_id)
                res['name'] = f"Visita: {prop.title or prop.name}" if prop.exists() else "Visita a Propiedad"
            else:
                res['name'] = 'Visita a Propiedad'
        return res

    @api.onchange('property_id')
    def _onchange_property_id_set_name(self):
        if self.property_id:
            prop_title = self.property_id.title or self.property_id.name
            if not self.name or self.name in ('Visita a Propiedad', 'Visita', 'Reunión', 'Nueva Cita'):
                self.name = f"Visita: {prop_title}"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name'):
                prop_id = vals.get('property_id')
                lead_id = vals.get('lead_id')
                name = 'Visita a Propiedad'
                if prop_id:
                    prop = self.env['estate.property'].browse(prop_id)
                    if prop.exists():
                        name = f"Visita: {prop.title or prop.name}"
                elif lead_id:
                    lead = self.env['crm.lead'].browse(lead_id)
                    if lead.exists():
                        name = f"Visita - {lead.name}"
                vals['name'] = name
        events = super().create(vals_list)
        for event in events:
            if event.appointment_type in ('visit', 'signing') or event.property_id:
                lead = event._get_related_lead()
                if lead and lead.stage_id.name != 'Oportunidades Bot':
                    lead._advance_lead_to_stage('estate_crm.stage_lead3b_estate_seguimiento')
        events._sync_reminder_alarm()
        return events

    def write(self, vals):
        res = super().write(vals)
        # Si cambió la anticipación (o el asesor, que puede tener la suya),
        # se re-sincroniza el recordatorio nativo de Odoo.
        if {'whatsapp_reminder_value', 'whatsapp_reminder_unit', 'user_id'} & set(vals):
            self._sync_reminder_alarm()
        return res

    def action_done_visit(self):
        for event in self:
            event.write({'visit_state': 'done'})

            # Auto-avanzar lead a "Visita Realizada" (excepto si está en "Oportunidades Bot")
            lead = event._get_related_lead()
            if lead and lead.stage_id.name != 'Oportunidades Bot':
                lead._advance_lead_to_stage('estate_crm.stage_lead3b_estate_seguimiento')

            # 1. Actualizar temperatura CRM si se hizo una oferta
            if event.visit_result == 'offer_made' and event.client_id:
                leads = self.env['crm.lead'].sudo().search([
                    ('partner_id', '=', event.client_id.id),
                    ('stage_id.is_won', '=', False),
                ], limit=1)
                if leads:
                    leads.write({'lead_temperature': 'boiling'})
                    leads.message_post(
                        body=f'Temperatura actualizada a HIRVIENDO: oferta realizada durante visita a "{event.property_id.title or ""}".')

            # 2. Crear actividad de seguimiento si la valoración fue baja
            if event.visit_rating and int(event.visit_rating) <= 2 and event.property_id:
                result_label = dict(self._fields['visit_result'].selection).get(event.visit_result, 'N/A')
                event.property_id.activity_schedule(
                    'mail.mail_activity_data_todo',
                    date_deadline=fields.Date.today(),
                    summary=f'Visita con calificación baja ({event.visit_rating}/5) — {event.client_id.name or "Cliente"}',
                    note=(
                        f'La visita a "{event.property_id.title}" recibió calificación {event.visit_rating}/5. '
                        f'Resultado: {result_label}. '
                        f'Notas: {event.visit_notes or "Sin notas"}. '
                        f'Se recomienda contactar al cliente para entender sus objeciones.'
                    ),
                    user_id=event.property_id.user_id.id or self.env.uid,
                )

            # 3. Enviar WhatsApp de seguimiento al cliente
            if event.client_id and event.property_id:
                self._send_followup_whatsapp(event)

            # 4. Recomputar visitas completadas en leads relacionados para scoring preciso
            if event.client_id:
                related_leads = self.env['crm.lead'].sudo().search([
                    ('partner_id', '=', event.client_id.id),
                ])
                for lead in related_leads:
                    count = self.env['calendar.event'].sudo().search_count([
                        ('client_id', '=', lead.partner_id.id),
                        ('visit_state', '=', 'done'),
                    ])
                    lead.completed_visits_count = count

    def _send_followup_whatsapp(self, event):
        """Envía WhatsApp de seguimiento post-visita al cliente via Meta Cloud API."""
        try:
            phone = event.client_id.mobile or event.client_id.phone
            if not phone:
                return
            prop_title = event.property_id.title or event.property_id.name
            client_name = event.client_id.name or 'estimado/a cliente'
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
        if not self.client_id or not (self.client_id.mobile or self.client_id.phone):
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
        if not self.client_id or not (self.client_id.mobile or self.client_id.phone):
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
        client_name = self.client_id.name or 'estimado cliente'
        asesor = self.user_id.name if self.user_id else 'nuestro asesor'
        msg = (
            f"Hola {client_name},\n\n"
            f"Gracias por tu visita a *{prop_title}*.\n"
            f"Tu opinion nos importa mucho. Podrias calificar tu experiencia?\n\n"
            f"1 - Muy mala\n"
            f"2 - Mala\n"
            f"3 - Regular\n"
            f"4 - Buena\n"
            f"5 - Excelente\n\n"
            f"Solo responde con el numero (1-5).\n"
            f"Atendido por: {asesor}\n"
            f"Gracias!"
        )
        number = (self.client_id.mobile or self.client_id.phone or '').replace(' ', '').replace('-', '').replace('+', '')
        wa_url = f"https://wa.me/{number}?text={urllib.parse.quote(msg)}"
        self.write({'survey_sent': True})
        return {
            'type': 'ir.actions.act_url',
            'url': wa_url,
            'target': 'new',
        }
