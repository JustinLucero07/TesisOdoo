from datetime import timedelta
from odoo import models, fields, api


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

        # Group by day
        days = {}
        current = date_from
        while current <= date_to:
            days[current] = []
            current += timedelta(days=1)

        for ev in events:
            day = fields.Datetime.context_timestamp(ev, ev.start).date()
            if day in days:
                days[day].append(ev)

        day_names = {
            0: 'Lunes', 1: 'Martes', 2: 'Miércoles',
            3: 'Jueves', 4: 'Viernes', 5: 'Sábado', 6: 'Domingo',
        }

        calendar_days = []
        for day_date in sorted(days.keys()):
            calendar_days.append({
                'date': day_date,
                'day_name': day_names.get(day_date.weekday(), ''),
                'events': days[day_date],
            })

        return {
            'doc_ids': docids,
            'data': data,
            'days': calendar_days,
            'date_from': date_from,
            'date_to': date_to,
            'user_name': data.get('user_name', ''),
            'total_events': len(events),
        }
