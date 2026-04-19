from odoo import models, fields, api

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    @api.depends('partner_id')
    def _compute_completed_visits(self):
        """Sobrescribe la métrica base para usar el estado de visita definido en este módulo."""
        for lead in self:
            if lead.partner_id:
                # 'visit_state' está definido en calendar_event.py de este módulo
                lead.completed_visits_count = self.env['calendar.event'].sudo().search_count([
                    ('partner_id', '=', lead.partner_id.id),
                    ('visit_state', '=', 'done'),
                ])
            else:
                lead.completed_visits_count = 0
