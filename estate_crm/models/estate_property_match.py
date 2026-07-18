import operator as _op

from odoo import api, models, fields


class EstatePropertyMatch(models.Model):
    _inherit = 'estate.property'

    crm_match_count = fields.Integer(
        string='Leads Interesados',
        compute='_compute_crm_match_count',
        search='_search_crm_match_count',
    )

    @api.model
    def _migrate_consolidate_allied_fields(self):
        """Los campos is_allied_listing/allied_agency_id (definidos antes en este
        módulo) se consolidaron en estate_management.is_allied_property/
        allied_agency_id. La columna is_allied_listing sigue físicamente en la
        tabla aunque el campo ya no existe en el modelo; se rescata su valor
        antes de que quede huérfana."""
        self.env.cr.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'estate_property' AND column_name = 'is_allied_listing'
        """)
        if not self.env.cr.fetchone():
            return
        self.env.cr.execute("""
            UPDATE estate_property
            SET is_allied_property = TRUE
            WHERE is_allied_listing IS TRUE
              AND (is_allied_property IS NULL OR is_allied_property = FALSE)
        """)

    def _search_crm_match_count(self, operator, value):
        """Permite usar el conteo (no almacenado) en dominios, ej:
        [('crm_match_count', '>', 0)] → solo inmuebles con clientes posibles."""
        ops = {'>': _op.gt, '>=': _op.ge, '<': _op.lt, '<=': _op.le,
               '=': _op.eq, '==': _op.eq, '!=': _op.ne}
        fn = ops.get(operator, _op.gt)
        matched = []
        for p in self.search([]):
            cnt = self.env['crm.lead'].search_count(p._get_lead_match_domain()) if p.price else 0
            if fn(cnt, value):
                matched.append(p.id)
        return [('id', 'in', matched)]

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
