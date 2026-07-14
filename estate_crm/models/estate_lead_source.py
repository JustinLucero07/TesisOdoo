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

    _unique_code = models.Constraint(
        'unique(code)',
        'Ya existe una fuente de lead con ese código técnico.',
    )

    @api.model
    def get_by_code(self, code):
        """Usado por las integraciones automáticas: busca la fuente por su
        código técnico y, si no la encuentra, cae en "Otro" (nunca falla)."""
        source = self.search([('code', '=', code)], limit=1)
        if not source:
            source = self.search([('code', '=', 'other')], limit=1)
        return source
