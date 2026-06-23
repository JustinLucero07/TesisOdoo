import operator as _op

from odoo import models, fields


class EstatePropertyMatch(models.Model):
    _inherit = 'estate.property'

    crm_match_count = fields.Integer(
        string='Leads Interesados',
        compute='_compute_crm_match_count',
        search='_search_crm_match_count',
    )

    # ── Inventario de aliados ────────────────────────────────────────────────
    is_allied_listing = fields.Boolean(
        string='Inmueble de aliado',
        help='Marca este inmueble como parte del inventario de una agencia aliada '
             '(para ofrecerlo a tus clientes sin ser captación propia).')
    allied_agency_id = fields.Many2one(
        'res.partner', string='Agencia aliada',
        domain=[('is_allied_agency', '=', True)],
        help='Agencia aliada origen de este inmueble.')

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
