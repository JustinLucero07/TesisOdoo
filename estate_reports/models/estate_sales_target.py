# -*- coding: utf-8 -*-
"""#1: Metas / cuotas de ventas por asesor y período.

Permite comparar lo realizado contra un objetivo (KPIs vs meta), que es lo
que distingue un sistema ejecutivo de un simple listado de datos.
"""
from datetime import date
from odoo import api, fields, models


class EstateSalesTarget(models.Model):
    _name = 'estate.sales.target'
    _description = 'Meta de Ventas'
    _order = 'year desc, month desc, user_id'
    _rec_name = 'display_name'

    display_name = fields.Char(compute='_compute_display_name')
    user_id = fields.Many2one(
        'res.users', string='Asesor',
        help='Déjalo vacío para una meta global de la agencia.')
    year = fields.Integer(string='Año', required=True, default=lambda s: date.today().year)
    month = fields.Selection(
        [('0', 'Todo el año')] + [(str(i), n) for i, n in enumerate(
            ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio',
             'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'], start=1)],
        string='Mes', required=True, default=lambda s: str(date.today().month))

    target_count = fields.Integer(string='Meta de Cierres (#)')
    target_revenue = fields.Float(string='Meta de Ingresos ($)')
    target_commission = fields.Float(string='Meta de Comisiones ($)')

    actual_count = fields.Integer(string='Cierres Reales', compute='_compute_actuals')
    actual_revenue = fields.Float(string='Ingresos Reales', compute='_compute_actuals')
    actual_commission = fields.Float(string='Comisiones Reales', compute='_compute_actuals')

    # Ratios 0-1 (para widget percentage)
    achievement_count = fields.Float(string='% Cumplimiento Cierres', compute='_compute_actuals')
    achievement_revenue = fields.Float(string='% Cumplimiento Ingresos', compute='_compute_actuals')
    achievement_commission = fields.Float(string='% Cumplimiento Comisiones', compute='_compute_actuals')

    _sql_constraints = [
        ('unique_target', 'unique(user_id, year, month)',
         'Ya existe una meta para ese asesor, año y mes.'),
    ]

    @api.depends('user_id', 'year', 'month')
    def _compute_display_name(self):
        meses = dict(self._fields['month'].selection)
        for rec in self:
            who = rec.user_id.name if rec.user_id else 'Agencia'
            rec.display_name = f"{who} · {meses.get(rec.month, '')} {rec.year}"

    def _period_bounds(self):
        """(date_from, date_to) según año/mes (mes 0 = año completo)."""
        self.ensure_one()
        y = self.year or date.today().year
        if self.month and self.month != '0':
            m = int(self.month)
            date_from = date(y, m, 1)
            date_to = date(y + (m // 12), (m % 12) + 1, 1) if m < 12 else date(y + 1, 1, 1)
            from datetime import timedelta
            date_to = date_to - timedelta(days=1)
        else:
            date_from, date_to = date(y, 1, 1), date(y, 12, 31)
        return date_from, date_to

    @api.depends('user_id', 'year', 'month', 'target_count', 'target_revenue', 'target_commission')
    def _compute_actuals(self):
        for rec in self:
            date_from, date_to = rec._period_bounds()
            dom = [('state', '=', 'sold'),
                   ('date_sold', '>=', date_from), ('date_sold', '<=', date_to)]
            if rec.user_id:
                dom.append(('user_id', '=', rec.user_id.id))
            sold = self.env['estate.property'].sudo().search(dom)
            rec.actual_count = len(sold)
            rec.actual_revenue = sum(sold.mapped('price'))

            com_dom = [('type', '=', 'sale'),
                       ('date', '>=', date_from), ('date', '<=', date_to),
                       ('state', '!=', 'cancelled')]
            if rec.user_id:
                com_dom.append(('user_id', '=', rec.user_id.id))
            commissions = self.env['estate.commission'].sudo().search(com_dom)
            rec.actual_commission = sum(commissions.mapped('amount'))

            rec.achievement_count = (rec.actual_count / rec.target_count) if rec.target_count else 0.0
            rec.achievement_revenue = (rec.actual_revenue / rec.target_revenue) if rec.target_revenue else 0.0
            rec.achievement_commission = (rec.actual_commission / rec.target_commission) if rec.target_commission else 0.0
