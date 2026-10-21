# -*- coding: utf-8 -*-
"""Búsqueda rápida de la paleta de comandos (Ctrl+K)."""
from odoo import api, models


class EstateMyDay(models.AbstractModel):
    _name = 'estate.my.day'
    _description = 'Búsqueda rápida (Ctrl+K)'

    @api.model
    def global_search(self, term, limit=5):
        """Búsqueda rápida (Ctrl+K): propiedades, oportunidades y contactos."""
        term = (term or '').strip()
        if len(term) < 2:
            return []
        out = []
        Prop = self.env['estate.property']
        for p in Prop.search(['|', '|', '|', ('name', 'ilike', term), ('title', 'ilike', term),
                              ('street', 'ilike', term), ('city', 'ilike', term)], limit=limit):
            out.append({'model': 'estate.property', 'id': p.id, 'category': 'estate_props',
                        'name': '%s · %s' % (p.name, p.title or ''),
                        'sub': ', '.join(x for x in [p.city, dict(p._fields['state'].selection).get(p.state)] if x)})
        Lead = self.env['crm.lead']
        for l in Lead.search(['|', '|', '|', '|', ('name', 'ilike', term), ('partner_id.name', 'ilike', term),
                              ('contact_name', 'ilike', term), ('phone', 'ilike', term),
                              ('email_from', 'ilike', term)], limit=limit):
            out.append({'model': 'crm.lead', 'id': l.id, 'category': 'estate_leads',
                        'name': l.partner_id.name or l.contact_name or l.name,
                        'sub': ' · '.join(x for x in [l.stage_id.name, l.target_property_id.title] if x)})
        Partner = self.env['res.partner']
        for c in Partner.search(['|', '|', '|', ('name', 'ilike', term), ('phone', 'ilike', term),
                                 ('mobile', 'ilike', term), ('email', 'ilike', term)], limit=limit):
            out.append({'model': 'res.partner', 'id': c.id, 'category': 'estate_contacts',
                        'name': c.name or '', 'sub': c.phone or c.mobile or c.email or ''})
        return out
