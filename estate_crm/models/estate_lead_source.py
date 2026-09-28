# -*- coding: utf-8 -*-
"""Fuente de Lead: catálogo editable (antes era una lista fija/Selection).

Permite al usuario elegir una fuente existente o crear una nueva directamente
desde el desplegable del lead, sin tocar código. El campo "code" es opcional y
solo lo usan las integraciones automáticas (webhooks, WhatsApp) para ubicar la
fuente correcta por su nombre técnico; las fuentes creadas a mano no lo usan.
"""
from odoo import api, fields, models


class EstateCrmLeadSource(models.Model):
    _name = 'estate.crm.lead.source'
    _description = 'Fuente de Lead'
    _order = 'sequence, name'

    name = fields.Char(string='Nombre', required=True)
    code = fields.Char(
        string='Código técnico', copy=False,
        help='Solo para integraciones automáticas (webhooks, WhatsApp/Meta). '
             'Las fuentes creadas manualmente no necesitan código.')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    lead_count = fields.Integer(string='N° Leads', compute='_compute_lead_count')

    _unique_code = models.Constraint(
        'unique(code)',
        'Ya existe una fuente de lead con ese código técnico.',
    )

    def _compute_lead_count(self):
        for rec in self:
            rec.lead_count = self.env['crm.lead'].search_count([('lead_source_id', '=', rec.id)])

    def action_view_leads(self):
        self.ensure_one()
        return {
            'name': f'Leads de {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'view_mode': 'kanban,list,form',
            'domain': [('lead_source_id', '=', self.id)],
            'context': {'default_lead_source_id': self.id},
        }

    def action_edit_source(self):
        self.ensure_one()
        return {
            'name': 'Editar Fuente de Lead',
            'type': 'ir.actions.act_window',
            'res_model': 'estate.crm.lead.source',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def action_delete_source(self):
        self.unlink()
        return True

    def unlink(self):
        for rec in self:
            leads = self.env['crm.lead'].search([('lead_source_id', '=', rec.id)])
            if leads:
                fallback = self.search([('code', '=', 'other'), ('id', 'not in', self.ids)], limit=1)
                if not fallback:
                    fallback = self.search([('id', 'not in', self.ids)], limit=1)
                if fallback:
                    leads.write({'lead_source_id': fallback.id})
        return super().unlink()

    @api.model
    def get_by_code(self, code):
        """Usado por las integraciones automáticas: busca la fuente por su
        código técnico y, si no la encuentra, cae en "Otro" (nunca falla)."""
        source = self.search([('code', '=', code)], limit=1)
        if not source:
            source = self.search([('code', '=', 'other')], limit=1)
        return source
