from odoo import models, fields, api

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # --- Visitas a propiedades (no solo la de interés: cualquiera que haya visitado) ---
    visit_count = fields.Integer(string='Visitas', compute='_compute_visit_count')
    visit_ids = fields.One2many(
        'calendar.event', 'lead_id', string='Propiedades Visitadas')

    reminder_ids = fields.One2many('estate.reminder', 'lead_id', string='Recordatorios')
    reminder_count = fields.Integer(
        string='Recordatorios pendientes', compute='_compute_reminder_count')

    def _compute_reminder_count(self):
        data = self.env['estate.reminder']._read_group(
            [('lead_id', 'in', self.ids), ('state', '=', 'pending')],
            ['lead_id'], ['__count'])
        counts = {lead.id: count for lead, count in data}
        for lead in self:
            lead.reminder_count = counts.get(lead.id, 0)

    def _reminder_defaults(self):
        self.ensure_one()
        return {
            'default_lead_id': self.id,
            'default_partner_id': self.partner_id.id or False,
            'default_property_id': self.target_property_id.id or False,
            'default_user_id': (self.user_id or self.env.user).id,
        }

    def action_create_reminder(self):
        """Acceso directo: abre un recordatorio nuevo ya ligado al lead."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Nuevo recordatorio',
            'res_model': 'estate.reminder',
            'view_mode': 'form',
            'target': 'new',
            'context': self._reminder_defaults(),
        }

    def action_view_reminders(self):
        self.ensure_one()
        if not self.reminder_ids:
            return self.action_create_reminder()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Recordatorios — %s' % (self.partner_id.name or self.name),
            'res_model': 'estate.reminder',
            'view_mode': 'list,form,calendar',
            'domain': [('lead_id', '=', self.id)],
            'context': self._reminder_defaults(),
        }

    def _compute_visit_count(self):
        Event = self.env['calendar.event']
        for lead in self:
            lead.visit_count = Event.search_count([('lead_id', '=', lead.id)])

    def action_view_lead_visits(self):
        """Lista TODAS las visitas de este lead, sin importar a qué propiedad
        (no solo target_property_id): un mismo cliente puede visitar varias
        propiedades distintas durante su proceso, cada visita queda con su
        propia propiedad, fecha y calificación."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Visitas — {self.partner_id.name or self.name}',
            'res_model': 'calendar.event',
            'view_mode': 'list,calendar,form',
            'domain': [('lead_id', '=', self.id)],
            'context': {
                'default_lead_id': self.id,
                'default_appointment_type': 'visit',
                'default_property_id': self.target_property_id.id if self.target_property_id else False,
            },
        }

    @api.depends('partner_id')
    def _compute_completed_visits(self):
        """Sobrescribe la métrica base para usar el estado de visita definido en este módulo."""
        for lead in self:
            if lead.partner_id:
                # 'visit_state' está definido en calendar_event.py de este módulo
                lead.completed_visits_count = self.env['calendar.event'].sudo().search_count([
                    ('client_id', '=', lead.partner_id.id),
                    ('visit_state', '=', 'done'),
                ])
            else:
                lead.completed_visits_count = 0
