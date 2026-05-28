from datetime import timedelta
from markupsafe import Markup
from odoo import models, fields, api


def _mk(s):
    """Convierte string con caracteres Unicode a Markup con entidades HTML numéricas."""
    if not s:
        return Markup('')
    return Markup(''.join(
        c if ord(c) < 128 else '&#{};'.format(ord(c))
        for c in s
    ))


class CalendarPrintWizard(models.TransientModel):
    _name = 'calendar.print.wizard'
    _description = 'Imprimir Agenda Semanal'

    date_from = fields.Date(
        string='Desde', required=True,
        default=lambda self: fields.Date.today() - timedelta(days=fields.Date.today().weekday()))
    date_to = fields.Date(
        string='Hasta', required=True,
        default=lambda self: fields.Date.today() - timedelta(days=fields.Date.today().weekday()) + timedelta(days=6))
    user_id = fields.Many2one(
        'res.users', string='Asesor',
        default=lambda self: self.env.user,
        help='Dejar vacío para mostrar todas las visitas')
    only_visits = fields.Boolean(string='Solo visitas inmobiliarias', default=True)

    def action_print(self):
        self.ensure_one()
        data = {
            'date_from': str(self.date_from),
            'date_to': str(self.date_to),
            'user_id': self.user_id.id if self.user_id else False,
            'user_name': self.user_id.name if self.user_id else 'Todos los asesores',
            'only_visits': self.only_visits,
        }
        return self.env.ref('estate_calendar.action_report_weekly_calendar').report_action(self, data=data)


class CalendarWeeklyReport(models.AbstractModel):
    _name = 'report.estate_calendar.report_weekly_calendar'
    _description = 'Reporte Semanal de Calendario'

    _DAY_NAMES = {
        0: 'Lunes', 1: 'Martes', 2: 'Miércoles',
        3: 'Jueves', 4: 'Viernes', 5: 'Sábado', 6: 'Domingo',
    }
    _MONTHS = {
        1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
        5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
        9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre',
    }
    _MONTHS_SHORT = {
        1: 'ENE', 2: 'FEB', 3: 'MAR', 4: 'ABR',
        5: 'MAY', 6: 'JUN', 7: 'JUL', 8: 'AGO',
        9: 'SEP', 10: 'OCT', 11: 'NOV', 12: 'DIC',
    }

    @api.model
    def _get_report_values(self, docids, data=None):
        date_from = fields.Date.from_string(data['date_from'])
        date_to = fields.Date.from_string(data['date_to'])
        user_id = data.get('user_id')

        domain = [
            ('start', '>=', str(date_from)),
            ('start', '<=', str(date_to + timedelta(days=1))),
        ]
        if data.get('only_visits'):
            domain.append(('property_id', '!=', False))
        if user_id:
            domain.append(('user_id', '=', user_id))

        events = self.env['calendar.event'].sudo().search(domain, order='start asc')

        days = {}
        current = date_from
        while current <= date_to:
            days[current] = []
            current += timedelta(days=1)

        for ev in events:
            day = fields.Datetime.context_timestamp(ev, ev.start).date()
            if day in days:
                days[day].append(ev)

        calendar_days = []
        for day_date in sorted(days.keys()):
            day_events = days[day_date]
            calendar_days.append({
                'date_str': '%02d/%02d/%d' % (day_date.day, day_date.month, day_date.year),
                'day_num': str(day_date.day),
                'month_short': self._MONTHS_SHORT[day_date.month],
                'year': str(day_date.year),
                'day_name': _mk(self._DAY_NAMES.get(day_date.weekday(), '')),
                'month_name': _mk(self._MONTHS[day_date.month].capitalize()),
                'events': day_events,
                'event_count': len(day_events),
            })

        def fmt_time(ev):
            try:
                local = fields.Datetime.context_timestamp(ev, ev.start)
                end = fields.Datetime.context_timestamp(ev, ev.stop) if ev.stop else None
                s = local.strftime('%H:%M')
                if end:
                    s += '-' + end.strftime('%H:%M')
                return s
            except Exception:
                return ''

        def fmt_type(t):
            return {
                'visit': _mk('Visita'),
                'signing': _mk('Firma'),
                'call': _mk('Llamada'),
                'meeting': _mk('Reunión'),
            }.get(t, _mk(t or '—'))

        def fmt_state(s):
            return {
                'scheduled': _mk('Programada'),
                'done': _mk('Realizada'),
                'cancelled': _mk('Cancelada'),
            }.get(s, _mk('—'))

        date_from_str = '%02d/%02d/%d' % (date_from.day, date_from.month, date_from.year)
        date_to_str = '%02d/%02d/%d' % (date_to.day, date_to.month, date_to.year)

        return {
            'doc_ids': docids,
            'data': data,
            'days': calendar_days,
            'date_from_str': date_from_str,
            'date_to_str': date_to_str,
            'user_name': _mk(data.get('user_name', '')),
            'total_events': len(events),
            'fmt_time': fmt_time,
            'fmt_type': fmt_type,
            'fmt_state': fmt_state,
        }
