from odoo import models, fields, api

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # --- Visitas a propiedades (no solo la de interés: cualquiera que haya visitado) ---
    visit_count = fields.Integer(string='Visitas', compute='_compute_visit_count')
    visit_ids = fields.One2many(
        'calendar.event', 'lead_id', string='Propiedades Visitadas')

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
