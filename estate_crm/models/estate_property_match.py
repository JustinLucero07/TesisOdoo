from odoo import models, fields


class EstatePropertyMatch(models.Model):
    _inherit = 'estate.property'

    crm_match_count = fields.Integer(
        string='Leads Interesados',
        compute='_compute_crm_match_count'
    )

    def _get_lead_match_domain(self):
        """Dominio para buscar leads cuyo presupuesto cubra al menos 70% del precio."""
        self.ensure_one()
        return [
            ('type', '=', 'opportunity'),
            ('stage_id.is_won', '=', False),
            ('client_budget', '>=', self.price * 0.70),
            ('client_budget', '<=', self.price * 1.30),
        ]

    def _compute_crm_match_count(self):
        for rec in self:
            count = 0
            if rec.price:
                count = self.env['crm.lead'].search_count(rec._get_lead_match_domain())
            rec.crm_match_count = count

    def action_view_lead_matches(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Leads interesados — {self.title}',
            'res_model': 'crm.lead',
            'view_mode': 'list,kanban,form',
            'domain': self._get_lead_match_domain(),
        }
