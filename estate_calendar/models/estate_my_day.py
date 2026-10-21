# -*- coding: utf-8 -*-
"""Pantalla "Mi día": lo que cada asesor tiene que atender hoy, en un vistazo."""
from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models


class EstateMyDay(models.AbstractModel):
    _name = 'estate.my.day'
    _description = 'Mi día'

    def _local_day_bounds(self):
        tz = pytz.timezone(self.env.user.tz or 'America/Guayaquil')
        today = datetime.now(tz).date()
        start = tz.localize(datetime.combine(today, time.min)).astimezone(pytz.utc).replace(tzinfo=None)
        end = tz.localize(datetime.combine(today, time.max)).astimezone(pytz.utc).replace(tzinfo=None)
        return tz, today, start, end

    @api.model
    def get_data(self):
        user = self.env.user
        tz, today, day_start, day_end = self._local_day_bounds()
        is_manager = user.has_group('estate_management.estate_group_manager')

        # Citas de hoy (como organizador o invitado)
        Event = self.env['calendar.event']
        events = Event.search([
            ('start', '>=', day_start), ('start', '<=', day_end),
            '|', ('user_id', '=', user.id), ('partner_ids', 'in', user.partner_id.ids),
        ], order='start asc', limit=20)
        citas = [{
            'id': e.id,
            'hour': pytz.utc.localize(e.start).astimezone(tz).strftime('%H:%M') if not e.allday else 'Todo el día',
            'name': e.name,
            'client': e.client_id.name or '',
            'property': e.property_id.title or e.property_id.display_name or '',
            'state': e.visit_state or 'scheduled',
            'type': dict(e._fields['appointment_type'].selection).get(e.appointment_type, ''),
        } for e in events]

        # Recordatorios vencidos o de los próximos 7 días
        Reminder = self.env['estate.reminder']
        rems = Reminder.search([
            ('user_id', '=', user.id), ('state', '=', 'pending'),
            ('date', '<=', today + timedelta(days=7)),
        ], order='deadline asc', limit=12)
        recordatorios = [{
            'id': r.id,
            'name': r.name,
            'client': r.partner_id.name or '',
            'date': r.date.strftime('%d/%m') if r.date else '',
            'days_left': r.days_left,
            'urgency': r.urgency,
        } for r in rems]

        # Leads calientes que piden atención
        Lead = self.env['crm.lead']
        leads = Lead.search([
            ('user_id', '=', user.id), ('type', '=', 'opportunity'),
            ('lead_temperature', 'in', ('hot', 'boiling')),
            ('won_status', '=', 'pending'),
        ], order='lead_temperature desc, write_date asc', limit=8)
        leads_data = [{
            'id': l.id,
            'name': l.partner_id.name or l.contact_name or l.name,
            'property': l.target_property_id.title or '',
            'temperature': l.lead_temperature,
            'temperature_label': dict(l._fields['lead_temperature'].selection).get(l.lead_temperature, ''),
            'next': l.activity_date_deadline.strftime('%d/%m') if l.activity_date_deadline else '',
        } for l in leads]

        # Actividades vencidas o de hoy
        Activity = self.env['mail.activity']
        acts = Activity.search([
            ('user_id', '=', user.id), ('date_deadline', '<=', today),
        ], order='date_deadline asc', limit=8)
        actividades = [{
            'id': a.id,
            'summary': a.summary or a.activity_type_id.name or 'Actividad',
            'record': a.res_name or '',
            'model': a.res_model,
            'res_id': a.res_id,
            'late': a.date_deadline < today,
        } for a in acts]

        cobros = False
        if is_manager:
            Sale = self.env['sale.order']
            domain = [('property_id', '!=', False), ('state', '=', 'sale'),
                      ('amount_total', '>', 0), ('estate_commission_collected', '=', False)]
            pending = Sale.search(domain)
            cobros = {'count': len(pending), 'amount': sum(pending.mapped('amount_total'))}

        hour = datetime.now(tz).hour
        saludo = 'Buenos días' if hour < 12 else ('Buenas tardes' if hour < 19 else 'Buenas noches')
        meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto',
                 'septiembre', 'octubre', 'noviembre', 'diciembre']
        dias = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
        return {
            'greeting': '%s, %s' % (saludo, (user.name or '').split(' ')[0]),
            'date_label': '%s %d de %s' % (dias[today.weekday()].capitalize(), today.day, meses[today.month - 1]),
            'is_manager': is_manager,
            'citas': citas,
            'recordatorios': recordatorios,
            'leads': leads_data,
            'actividades': actividades,
            'activities_late': Activity.search_count([('user_id', '=', user.id), ('date_deadline', '<', today)]),
            'cobros': cobros,
        }

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
