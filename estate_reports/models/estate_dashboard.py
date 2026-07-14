from odoo import models, fields, api
from datetime import timedelta, date as _date
import calendar as _cal
import json


class EstateDashboard(models.TransientModel):
    _name = 'estate.dashboard'
    _description = 'Dashboard Inmobiliario'
    _rec_name = 'display_title'

    # Paleta de marca centralizada (espejo de brand_palette.scss --inmobi-*).
    # Única fuente de verdad para los colores del dashboard; cámbialos aquí.
    _PALETTE = {
        'primary': '#004274',   # azul de acentos/gráficos (--inmobi-primary-strong)
        'success': '#16a34a',   # variaciones positivas
        'danger':  '#dc2626',   # variaciones negativas / alertas
        'warning': '#f59e0b',
        'muted':   '#6b7280',
        'chart':   ['#004274', '#004274', '#004274', '#004274',
                    '#004274', '#004274', '#004274'],  # categórica
    }

    display_title = fields.Char(
        string='Dashboard', compute='_compute_display_title')

    @api.depends()
    def _compute_display_title(self):
        for rec in self:
            rec.display_title = 'Dashboard General'

    # ── Banner HTML (KPI cards + header) ─────────────────────────────

    # KPIs Propiedades
    total_properties = fields.Integer(
        string='Total Propiedades', compute='_compute_kpis')
    available_properties = fields.Integer(
        string='Disponibles', compute='_compute_kpis')
    sold_properties = fields.Integer(
        string='Vendidas', compute='_compute_kpis')

    # KPIs Clientes
    total_clients = fields.Integer(
        string='Total Clientes', compute='_compute_kpis')
    active_clients = fields.Integer(
        string='Clientes Activos', compute='_compute_kpis')

    # KPIs Extras
    avg_days_on_market = fields.Float(
        string='Promedio Días en Mercado', compute='_compute_kpis')
    appointments_done = fields.Integer(
        string='Citas Realizadas', compute='_compute_kpis')
    contracts_expiring = fields.Integer(
        string='Contratos por Vencer', compute='_compute_kpis')

    # KPIs Financieros Avanzados
    monthly_commissions = fields.Float(
        string='Comisiones del Mes', compute='_compute_kpis')
    won_revenue_month = fields.Float(
        string='Ingresos Cerrados (Mes)', compute='_compute_kpis')
    pending_revenue = fields.Float(
        string='Pipeline Pendiente', compute='_compute_kpis')

    # #1 KPIs vs Objetivo (metas)
    goal_count = fields.Integer(string='Meta de Cierres', compute='_compute_kpis')
    goal_revenue = fields.Float(string='Meta de Ingresos', compute='_compute_kpis')
    goal_commission = fields.Float(string='Meta de Comisiones', compute='_compute_kpis')
    goal_achievement_count = fields.Float(string='% Cumplimiento Cierres', compute='_compute_kpis')
    goal_achievement_revenue = fields.Float(string='% Cumplimiento Ingresos', compute='_compute_kpis')
    goals_html = fields.Html(string='Cumplimiento de Metas', compute='_compute_kpis', sanitize=False)

    # Mapa de Propiedades

    # Sidebar derecho persistente

    # Ranking de Asesores
    advisor_ranking_html = fields.Html(
        string='Ranking de Asesores', compute='_compute_advisor_ranking', sanitize=False)
    stagnant_properties = fields.Integer(
        string='Propiedades Estancadas', compute='_compute_kpis')

    # Pipeline comercial
    active_offers_count = fields.Integer(
        string='Ofertas Activas', compute='_compute_kpis')
    active_contracts_count = fields.Integer(
        string='Contratos Activos', compute='_compute_kpis')
    sale_orders_count = fields.Integer(
        string='Órdenes de Venta', compute='_compute_kpis')
    pending_invoices_amount = fields.Float(
        string='Facturas Pendientes ($)', compute='_compute_kpis')

    # ── Filtros globales ─────────────────────────────────────────────
    filter_user_id = fields.Many2one(
        'res.users', string='Filtrar por Asesor',
        help='Filtra todas las métricas por un asesor específico.')
    filter_period = fields.Selection([
        ('month', 'Mes Actual'),
        ('quarter', 'Trimestre Actual'),
        ('year', 'Año Actual'),
        ('last_month', 'Mes Anterior'),
        ('custom', 'Personalizado'),
    ], string='Período', default='month',
       help='Selecciona el período para los indicadores financieros y de ventas.')
    filter_date_from = fields.Date(string='Desde')
    filter_date_to = fields.Date(string='Hasta')

    # ── Pestaña CRM — Embudo de conversión ─────────────────────────
    funnel_leads_new = fields.Integer(
        string='Leads Nuevos', compute='_compute_funnel')
    funnel_visits_done = fields.Integer(
        string='Visitas Realizadas', compute='_compute_funnel')
    funnel_offers_made = fields.Integer(
        string='Ofertas Recibidas', compute='_compute_funnel')
    funnel_won = fields.Integer(
        string='Cerrados (Ganados)', compute='_compute_funnel')
    funnel_lost = fields.Integer(
        string='Perdidos', compute='_compute_funnel')
    funnel_conversion_pct = fields.Float(
        string='% Conversión', compute='_compute_funnel')
    funnel_html = fields.Html(
        string='Embudo de Conversión', compute='_compute_funnel', sanitize=False)

    # ── Pestaña Ventas — Comparativa AVM ───────────────────────────

    # ── Gráficos inline (sparklines) ───────────────────────────────
    sales_chart_html = fields.Html(
        string='Ventas del Período', compute='_compute_charts', sanitize=False)
    leads_chart_html = fields.Html(
        string='Leads por Fuente', compute='_compute_charts', sanitize=False)
    # A2: datos JSON para gráficos Chart.js (renderizados por widget OWL)
    sales_chart_data = fields.Char(
        string='Datos Ventas (JSON)', compute='_compute_charts')
    leads_chart_data = fields.Char(
        string='Datos Leads (JSON)', compute='_compute_charts')

    # ── Tendencia (comparativa mes actual vs anterior) ─────────────
    trend_sales_current = fields.Integer(
        string='Ventas Período', compute='_compute_trends')
    trend_sales_prev = fields.Integer(
        string='Ventas Período Anterior', compute='_compute_trends')
    trend_sales_pct = fields.Float(
        string='% Variación Ventas', compute='_compute_trends')
    trend_leads_current = fields.Integer(
        string='Leads Período', compute='_compute_trends')
    trend_leads_prev = fields.Integer(
        string='Leads Período Anterior', compute='_compute_trends')
    trend_leads_pct = fields.Float(
        string='% Variación Leads', compute='_compute_trends')
    trend_html = fields.Html(
        string='Tendencias', compute='_compute_trends', sanitize=False)

    # ── Asistente IA inline ───────────────────────────────────────────
    ai_query_text = fields.Char(string='Consulta al Asistente')
    ai_response_html = fields.Html(string='Respuesta IA', sanitize=False)

    @api.onchange('filter_user_id', 'filter_period', 'filter_date_from', 'filter_date_to')
    def _onchange_filters(self):
        """Trigger all recomputations when filters change."""
        self._compute_kpis()
        self._compute_advisor_ranking()
        self._compute_funnel()
        self._compute_charts()
        self._compute_trends()

    def _get_period_dates(self):
        """Return (date_from, date_to) based on selected period filter."""
        today = fields.Date.today()
        period = self.filter_period or 'month'
        if period == 'month':
            return today.replace(day=1), today
        elif period == 'quarter':
            q = (today.month - 1) // 3
            return today.replace(month=q * 3 + 1, day=1), today
        elif period == 'year':
            return today.replace(month=1, day=1), today
        elif period == 'last_month':
            last_day_prev = today.replace(day=1) - timedelta(days=1)
            return last_day_prev.replace(day=1), last_day_prev
        elif period == 'custom' and self.filter_date_from:
            return self.filter_date_from, self.filter_date_to or today
        return today.replace(day=1), today

    def _get_prev_period_dates(self):
        """Return previous period dates for trend comparison."""
        date_from, date_to = self._get_period_dates()
        duration = (date_to - date_from).days + 1
        prev_to = date_from - timedelta(days=1)
        prev_from = prev_to - timedelta(days=duration - 1)
        return prev_from, prev_to

    def _get_period_targets(self, period_from, period_to):
        """Suma las metas (estate.sales.target) que caen dentro del período del
        dashboard, para el asesor filtrado (o la agencia si no hay filtro)."""
        self.ensure_one()
        dom = [('user_id', '=', self.filter_user_id.id)] if self.filter_user_id \
            else [('user_id', '=', False)]
        targets = self.env['estate.sales.target'].sudo().search(dom)
        t_count = t_rev = t_com = 0
        for t in targets:
            t_from, t_to = t._period_bounds()
            # Solapa con el período del dashboard
            if t_from <= period_to and t_to >= period_from:
                t_count += t.target_count
                t_rev += t.target_revenue
                t_com += t.target_commission
        return t_count, t_rev, t_com

    def _render_goals_html(self, a_count, t_count, a_rev, t_rev, a_com, t_com):
        """Barras de progreso 'realizado vs meta' con semáforo de color."""
        P = self._PALETTE

        def bar(label, actual, target, money=False):
            if not target:
                return ''
            pct = min(actual / target, 1.5) if target else 0
            pct_disp = (actual / target * 100) if target else 0
            color = P['success'] if pct_disp >= 100 else (P['warning'] if pct_disp >= 70 else P['danger'])
            width = min(pct_disp, 100)
            fmt = (lambda v: f"${v:,.0f}") if money else (lambda v: f"{v:.0f}")
            return (
                f'<div style="margin-bottom:12px;">'
                f'<div style="display:flex;justify-content:space-between;font-size:12px;'
                f'color:{P["muted"]};margin-bottom:3px;">'
                f'<span><strong>{label}</strong></span>'
                f'<span>{fmt(actual)} / {fmt(target)} '
                f'<strong style="color:{color}">({pct_disp:.0f}%)</strong></span>'
                f'</div>'
                f'<div style="background:#eef1f5;border-radius:6px;height:14px;overflow:hidden;">'
                f'<div style="width:{width}%;height:100%;background:{color};border-radius:6px;'
                f'transition:width .5s;"></div>'
                f'</div></div>'
            )

        bars = (bar('Cierres', a_count, t_count) +
                bar('Ingresos', a_rev, t_rev, money=True) +
                bar('Comisiones', a_com, t_com, money=True))
        if not bars:
            return (f'<div style="text-align:center;color:{P["muted"]};padding:16px;font-size:13px;">'
                    f'Sin metas definidas para este período. '
                    f'Configúralas en <strong>Reportes → Ventas → Metas de Ventas</strong>.</div>')
        return f'<div>{bars}</div>'

    def _compute_kpis(self):
        Property = self.env['estate.property']
        Lead = self.env['crm.lead']

        for rec in self:
            user_domain = [('user_id', '=', rec.filter_user_id.id)] if rec.filter_user_id else []

            # Propiedades
            rec.total_properties = Property.search_count(user_domain)
            rec.available_properties = Property.search_count(
                user_domain + [('state', '=', 'available')])
            rec.sold_properties = Property.search_count(
                user_domain + [('state', '=', 'sold')])

            # Clientes (Leads)
            lead_domain = [('user_id', '=', rec.filter_user_id.id)] if rec.filter_user_id else []
            rec.total_clients = self.env['res.partner'].search_count([('active', '=', True)])
            rec.active_clients = Lead.search_count(
                lead_domain + [('type', '=', 'opportunity'), ('probability', '>', 0), ('probability', '<', 100)])

            # Promedio días en mercado (vendidas)
            sold_props = Property.search(
                user_domain + [('state', '=', 'sold'), ('date_listed', '!=', False)])
            if sold_props:
                total_days = sum(sold_props.mapped('days_on_market'))
                rec.avg_days_on_market = round(total_days / len(sold_props), 1)
            else:
                rec.avg_days_on_market = 0

            # Citas realizadas este mes (Usando calendar.event)
            Appointment = self.env['calendar.event']
            today = fields.Date.today()
            first_day = today.replace(day=1)
            appt_domain = [('property_id', '!=', False), ('visit_state', '=', 'done'), ('start', '>=', first_day)]
            if rec.filter_user_id:
                appt_domain.append(('user_id', '=', rec.filter_user_id.id))
            rec.appointments_done = Appointment.search_count(appt_domain)

            # Contratos por vencer (próximos 30 días)
            limit = fields.Date.today() + timedelta(days=30)
            rec.contracts_expiring = Property.search_count([
                ('contract_end_date', '!=', False),
                ('contract_end_date', '<=', limit),
                ('state', 'in', ('available', 'reserved')),
            ])

            # KPIs Financieros (Período seleccionado)
            period_from, period_to = rec._get_period_dates()
            sold_period = Property.search(
                user_domain + [('state', '=', 'sold'),
                               ('date_sold', '>=', period_from),
                               ('date_sold', '<=', period_to)])
            rec.monthly_commissions = sum(sold_period.mapped('commission_amount'))
            rec.won_revenue_month = sum(sold_period.mapped('price'))

            # #1 KPIs vs Objetivo: sumar metas que caen en el período
            t_count, t_rev, t_com = rec._get_period_targets(period_from, period_to)
            rec.goal_count = t_count
            rec.goal_revenue = t_rev
            rec.goal_commission = t_com
            actual_count = len(sold_period)
            rec.goal_achievement_count = (actual_count / t_count) if t_count else 0.0
            rec.goal_achievement_revenue = (rec.won_revenue_month / t_rev) if t_rev else 0.0
            rec.goals_html = rec._render_goals_html(
                actual_count, t_count, rec.won_revenue_month, t_rev,
                rec.monthly_commissions, t_com)

            # Pipeline de Oportunidades
            opportunities = Lead.search(lead_domain + [('type', '=', 'opportunity'), ('probability', '>', 0), ('probability', '<', 100)])
            rec.pending_revenue = sum(opportunities.mapped('expected_revenue'))

            # Pipeline comercial
            rec.active_offers_count = self.env['estate.property.offer'].search_count([
                ('state', 'in', ('submitted', 'countered', 'accepted')),
            ])
            rec.active_contracts_count = self.env['estate.contract'].search_count([
                ('state', '=', 'active'),
            ])
            rec.sale_orders_count = self.env['sale.order'].search_count([
                ('property_id', '!=', False),
                ('state', 'in', ('sale', 'done')),
            ])
            pending_invoices = self.env['account.move'].search([
                ('move_type', '=', 'out_invoice'),
                ('payment_state', 'not in', ('paid', 'in_payment')),
                ('state', '=', 'posted'),
                ('property_id', '!=', False),
            ])
            rec.pending_invoices_amount = sum(pending_invoices.mapped('amount_residual'))

            # Propiedades estancadas (45+ días sin visita)
            cutoff_45 = today - timedelta(days=45)
            available_old = Property.search([('state', '=', 'available'), ('date_listed', '<=', cutoff_45)])
            CalEvent = self.env['calendar.event'].sudo()
            rec.stagnant_properties = sum(
                1 for prop in available_old
                if not CalEvent.search_count([
                    ('property_id', '=', prop.id),
                    ('visit_state', '=', 'done'),
                    ('start', '>=', fields.Datetime.to_datetime(cutoff_45)),
                ])
            )

    def _compute_advisor_ranking(self):
        """Mejora 7: Ranking mensual de asesores por ventas y comisiones."""
        for rec in self:
            today = fields.Date.today()
            start_month = today.replace(day=1)
            Property = self.env['estate.property']

            sold_this_month = Property.search([
                ('state', '=', 'sold'),
                ('date_sold', '>=', start_month),
                ('user_id', '!=', False),
            ])

            advisor_data = {}
            for prop in sold_this_month:
                uid = prop.user_id.id
                name = prop.user_id.name or 'Sin nombre'
                if uid not in advisor_data:
                    advisor_data[uid] = {'name': name, 'sales': 0, 'revenue': 0.0, 'commission': 0.0}
                advisor_data[uid]['sales'] += 1
                advisor_data[uid]['revenue'] += prop.price or 0.0
                advisor_data[uid]['commission'] += prop.commission_amount or 0.0

            ranking = sorted(advisor_data.values(), key=lambda x: x['sales'], reverse=True)

            medals = ['1.', '2.', '3.']
            rows = ''
            for i, adv in enumerate(ranking[:10]):
                medal = medals[i] if i < 3 else f'{i+1}.'
                rows += (
                    f'<tr style="background:{"#fffbea" if i == 0 else "white"}">'
                    f'<td style="padding:10px;font-size:1.1em">{medal}</td>'
                    f'<td style="padding:10px;font-weight:{"bold" if i==0 else "normal"}">{adv["name"]}</td>'
                    f'<td style="padding:10px;text-align:center">{adv["sales"]}</td>'
                    f'<td style="padding:10px;text-align:right">${adv["revenue"]:,.0f}</td>'
                    f'<td style="padding:10px;text-align:right;color:#16a34a">${adv["commission"]:,.0f}</td>'
                    f'</tr>'
                )

            if not rows:
                rows = '<tr><td colspan="5" style="padding:20px;text-align:center;color:#9ca3af">Sin ventas registradas este mes</td></tr>'

            html = f'''
            <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
                <table style="width:100%;border-collapse:collapse;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
                    <thead>
                        <tr style="background:#004274;color:white;">
                            <th style="padding:12px 10px;text-align:left">#</th>
                            <th style="padding:12px 10px;text-align:left">Asesor</th>
                            <th style="padding:12px 10px;text-align:center">Ventas</th>
                            <th style="padding:12px 10px;text-align:right">Ingresos</th>
                            <th style="padding:12px 10px;text-align:right">Comisión</th>
                        </tr>
                    </thead>
                    <tbody>{rows}</tbody>
                </table>
            </div>
            '''
            rec.advisor_ranking_html = html

    @api.model
    def _cron_send_monthly_report(self):
        """Genera y envía por email un reporte mensual mejorado con comparativa."""
        from datetime import date, timedelta
        import logging

        today = date.today()
        first_day = today.replace(day=1)
        last_month_last = first_day - timedelta(days=1)
        last_month_first = last_month_last.replace(day=1)
        # Mes anterior al anterior (para comparativa)
        prev2_last = last_month_first - timedelta(days=1)
        prev2_first = prev2_last.replace(day=1)

        Property = self.env['estate.property']
        Lead = self.env['crm.lead']

        # ── Datos del mes reportado ──
        sold_last = Property.search([
            ('state', '=', 'sold'),
            ('date_sold', '>=', last_month_first),
            ('date_sold', '<=', last_month_last),
        ])
        won_leads = Lead.search([
            ('type', '=', 'opportunity'),
            ('stage_id.is_won', '=', True),
            ('date_closed', '>=', last_month_first),
            ('date_closed', '<=', last_month_last),
        ])
        lost_leads = Lead.with_context(active_test=False).search([
            ('active', '=', False),
            ('probability', '=', 0),
            ('date_closed', '>=', last_month_first),
            ('date_closed', '<=', last_month_last),
        ])
        new_leads = Lead.search([
            ('create_date', '>=', str(last_month_first)),
            ('create_date', '<=', str(last_month_last) + ' 23:59:59'),
        ])
        visits_done = self.env['calendar.event'].search_count([
            ('property_id', '!=', False),
            ('visit_state', '=', 'done'),
            ('start', '>=', str(last_month_first)),
            ('start', '<=', str(last_month_last) + ' 23:59:59'),
        ])

        # ── Datos del mes anterior (comparativa) ──
        sold_prev = Property.search_count([
            ('state', '=', 'sold'),
            ('date_sold', '>=', prev2_first),
            ('date_sold', '<=', prev2_last),
        ])
        new_leads_prev = Lead.search_count([
            ('create_date', '>=', str(prev2_first)),
            ('create_date', '<=', str(prev2_last) + ' 23:59:59'),
        ])
        prev_rev = sum(Property.search([
            ('state', '=', 'sold'),
            ('date_sold', '>=', prev2_first),
            ('date_sold', '<=', prev2_last),
        ]).mapped('price'))

        total_commission = sum(sold_last.mapped('commission_amount'))
        total_revenue = sum(sold_last.mapped('price'))
        month_name = last_month_last.strftime('%B %Y')

        # Variaciones
        def _var(cur, prev):
            if not prev:
                return '+∞' if cur else '—'
            pct = round((cur - prev) / prev * 100, 1)
            return f"{'▲' if pct > 0 else '▼'} {abs(pct)}%"

        var_sales = _var(len(sold_last), sold_prev)
        var_leads = _var(len(new_leads), new_leads_prev)
        var_rev = _var(total_revenue, prev_rev)

        # Top asesores
        advisor_stats = {}
        for prop in sold_last:
            name = prop.user_id.name or 'Sin asignar'
            if name not in advisor_stats:
                advisor_stats[name] = {'sales': 0, 'revenue': 0, 'commission': 0}
            advisor_stats[name]['sales'] += 1
            advisor_stats[name]['revenue'] += prop.price or 0
            advisor_stats[name]['commission'] += prop.commission_amount or 0
        top_advisors = sorted(advisor_stats.items(), key=lambda x: x[1]['sales'], reverse=True)[:5]
        medals = ['1.', '2.', '3.', '4.', '5.']

        advisors_html = ''.join(
            f'<tr><td style="padding:10px">{medals[i]} {n}</td>'
            f'<td style="padding:10px;text-align:center;font-weight:bold">{d["sales"]}</td>'
            f'<td style="padding:10px;text-align:right">${d["revenue"]:,.0f}</td>'
            f'<td style="padding:10px;text-align:right;color:#16a34a">${d["commission"]:,.0f}</td></tr>'
            for i, (n, d) in enumerate(top_advisors)
        ) or '<tr><td colspan="4" style="padding:10px;text-align:center;color:#6b7280">Sin ventas registradas</td></tr>'

        properties_html = ''.join(
            f'<tr><td style="padding:8px">{p.title}</td>'
            f'<td style="padding:8px">{p.city or "-"}</td>'
            f'<td style="padding:8px;text-align:right">${p.price:,.0f}</td>'
            f'<td style="padding:8px;text-align:right;color:#16a34a">${p.commission_amount:,.0f}</td></tr>'
            for p in sold_last[:10]
        ) or '<tr><td colspan="4" style="padding:8px;text-align:center;color:#6b7280">Sin ventas</td></tr>'

        # Alertas críticas
        alerts = []
        overdue_count = self.env['estate.payment'].search_count([
            ('state', '=', 'pending'), ('date', '<', today)])
        if overdue_count:
            alerts.append(f'{overdue_count} pagos vencidos pendientes')
        expiring = Property.search_count([
            ('contract_end_date', '!=', False),
            ('contract_end_date', '<=', today + timedelta(days=30)),
            ('state', 'in', ('reserved',)),
        ])
        if expiring:
            alerts.append(f'{expiring} contratos vencen en 30 días')
        hot_stale = Lead.search_count([
            ('lead_temperature', 'in', ['hot', 'boiling']),
            ('write_date', '<=', str(fields.Datetime.now() - timedelta(days=7))),
            ('type', '=', 'opportunity'),
        ])
        if hot_stale:
            alerts.append(f'{hot_stale} leads calientes sin actividad en 7+ días')

        alerts_html = ''
        if alerts:
            alerts_items = ''.join(f'<li style="padding:4px 0;">{a}</li>' for a in alerts)
            alerts_html = f'''
            <div style="background:#fef2f2;border-left:4px solid #dc2626;padding:16px;border-radius:0 8px 8px 0;margin-bottom:24px;">
                <div style="font-weight:bold;color:#dc2626;margin-bottom:8px;">Alertas Críticas</div>
                <ul style="margin:0;padding-left:20px;color:#374151;">{alerts_items}</ul>
            </div>'''

        html_body = f"""
        <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;max-width:700px;margin:0 auto;">
            <div style="background:linear-gradient(135deg,#1a56db,#2E5AAC);color:white;padding:28px;border-radius:12px 12px 0 0;">
                <h1 style="margin:0;font-size:24px;">Reporte Mensual Inmobiliario</h1>
                <p style="margin:8px 0 0;opacity:.85;font-size:16px;">{month_name}</p>
            </div>
            <div style="background:#f8f9fa;padding:24px;border-radius:0 0 12px 12px;">

                {alerts_html}

                <!-- KPIs principales -->
                <table style="width:100%;border-collapse:collapse;margin-bottom:24px;">
                    <tr>
                        <td style="padding:16px;text-align:center;background:white;border:1px solid #e5e7eb;border-radius:8px;">
                            <div style="font-size:32px;font-weight:bold;color:#16a34a;">{len(sold_last)}</div>
                            <div style="color:#6b7280;font-size:13px;">Vendidas</div>
                            <div style="font-size:12px;color:#6b7280;margin-top:4px;">{var_sales}</div>
                        </td>
                        <td style="padding:16px;text-align:center;background:white;border:1px solid #e5e7eb;">
                            <div style="font-size:32px;font-weight:bold;color:#8b5cf6;">{len(new_leads)}</div>
                            <div style="color:#6b7280;font-size:13px;">Leads Nuevos</div>
                            <div style="font-size:12px;color:#6b7280;margin-top:4px;">{var_leads}</div>
                        </td>
                        <td style="padding:16px;text-align:center;background:white;border:1px solid #e5e7eb;">
                            <div style="font-size:32px;font-weight:bold;color:#f59e0b;">{visits_done}</div>
                            <div style="color:#6b7280;font-size:13px;">Visitas</div>
                        </td>
                    </tr>
                    <tr>
                        <td colspan="2" style="padding:16px;text-align:center;background:white;border:1px solid #e5e7eb;">
                            <div style="font-size:24px;font-weight:bold;color:#16a34a;">${total_revenue:,.0f}</div>
                            <div style="color:#6b7280;font-size:13px;">Ingresos por Ventas</div>
                            <div style="font-size:12px;color:#6b7280;margin-top:4px;">{var_rev}</div>
                        </td>
                        <td colspan="2" style="padding:16px;text-align:center;background:white;border:1px solid #e5e7eb;">
                            <div style="font-size:24px;font-weight:bold;color:#d97706;">${total_commission:,.0f}</div>
                            <div style="color:#6b7280;font-size:13px;">Comisiones</div>
                        </td>
                    </tr>
                    <tr>
                        <td colspan="2" style="padding:16px;text-align:center;background:white;border:1px solid #e5e7eb;">
                            <div style="font-size:24px;font-weight:bold;color:#16a34a;">{len(won_leads)}</div>
                            <div style="color:#6b7280;font-size:13px;">Leads Ganados</div>
                        </td>
                        <td colspan="2" style="padding:16px;text-align:center;background:white;border:1px solid #e5e7eb;">
                            <div style="font-size:24px;font-weight:bold;color:#dc2626;">{len(lost_leads)}</div>
                            <div style="color:#6b7280;font-size:13px;">Leads Perdidos</div>
                        </td>
                    </tr>
                </table>

                <!-- Top Asesores -->
                <h2 style="color:#1a56db;border-bottom:2px solid #1a56db;padding-bottom:8px;">Top Asesores</h2>
                <table style="width:100%;border-collapse:collapse;background:white;margin-bottom:24px;border-radius:8px;overflow:hidden;">
                    <thead><tr style="background:#1a56db;color:white;">
                        <th style="padding:10px;text-align:left;">Asesor</th>
                        <th style="padding:10px;text-align:center;">Ventas</th>
                        <th style="padding:10px;text-align:right;">Ingresos</th>
                        <th style="padding:10px;text-align:right;">Comisión</th>
                    </tr></thead>
                    <tbody>{advisors_html}</tbody>
                </table>

                <!-- Propiedades Vendidas -->
                <h2 style="color:#1a56db;border-bottom:2px solid #1a56db;padding-bottom:8px;">Propiedades Vendidas</h2>
                <table style="width:100%;border-collapse:collapse;background:white;margin-bottom:24px;border-radius:8px;overflow:hidden;">
                    <thead><tr style="background:#1a56db;color:white;">
                        <th style="padding:10px;text-align:left;">Propiedad</th>
                        <th style="padding:10px;">Ciudad</th>
                        <th style="padding:10px;text-align:right;">Precio</th>
                        <th style="padding:10px;text-align:right;">Comisión</th>
                    </tr></thead>
                    <tbody>{properties_html}</tbody>
                </table>

                <p style="color:#9ca3af;font-size:12px;text-align:center;margin-top:16px;">
                    Generado automáticamente · Sistema de Gestión Inmobiliaria · {today.strftime('%d/%m/%Y')}
                </p>
            </div>
        </div>
        """

        admins = self.env['res.users'].search([
            ('group_ids', 'in', [self.env.ref('base.group_system').id]),
            ('email', '!=', False),
        ])
        if not admins:
            admins = self.env['res.users'].search([('email', '!=', False)], limit=3)

        for admin in admins:
            self.env['mail.mail'].sudo().create({
                'subject': f'Reporte Mensual Inmobiliario — {month_name}',
                'email_to': admin.email,
                'body_html': html_body,
                'auto_delete': True,
            }).send()

        logging.getLogger(__name__).info(
            "Reporte mensual enviado para %s a %d destinatarios.", month_name, len(admins))

    # ──────────────────────────────────────────────────────────────────
    # NIVEL 2: Embudo de Conversión
    # ──────────────────────────────────────────────────────────────────
    def _compute_funnel(self):
        for rec in self:
            period_from, period_to = rec._get_period_dates()
            Lead = self.env['crm.lead'].sudo()

            total_new = Lead.search_count([
                ('create_date', '>=', str(period_from)),
                ('create_date', '<=', str(period_to) + ' 23:59:59'),
            ])
            # Visitas completadas en el período
            visits_done = self.env['calendar.event'].sudo().search_count([
                ('property_id', '!=', False),
                ('visit_state', '=', 'done'),
                ('start', '>=', str(period_from)),
                ('start', '<=', str(period_to) + ' 23:59:59'),
            ])
            offers_made = self.env['estate.property.offer'].sudo().search_count([
                ('create_date', '>=', str(period_from)),
                ('create_date', '<=', str(period_to) + ' 23:59:59'),
            ])
            won = Lead.search_count([
                ('stage_id.is_won', '=', True),
                ('date_closed', '>=', str(period_from)),
                ('date_closed', '<=', str(period_to) + ' 23:59:59'),
            ])
            lost = Lead.with_context(active_test=False).search_count([
                ('active', '=', False),
                ('probability', '=', 0),
                ('date_closed', '>=', str(period_from)),
                ('date_closed', '<=', str(period_to) + ' 23:59:59'),
            ])

            rec.funnel_leads_new = total_new
            rec.funnel_visits_done = visits_done
            rec.funnel_offers_made = offers_made
            rec.funnel_won = won
            rec.funnel_lost = lost
            rec.funnel_conversion_pct = round(won / total_new * 100, 1) if total_new else 0

            # Embudo visual real: etapas centradas que se estrechan, con la
            # conversión de etapa a etapa entre cada paso.
            P = rec._PALETTE
            stages = [
                ('Leads Nuevos', total_new, P['chart'][0]),
                ('Visitas', visits_done, P['chart'][1]),
                ('Ofertas', offers_made, P['warning']),
                ('Ganados', won, P['success']),
            ]
            max_val = max(total_new, 1)
            funnel = ''
            prev_val = None
            for i, (label, val, color) in enumerate(stages):
                width = max(val / max_val * 100, 8) if val else 8
                # Conversión respecto a la etapa anterior
                step_conv = ''
                if prev_val is not None:
                    conv = round(val / prev_val * 100) if prev_val else 0
                    arrow_color = P['success'] if conv >= 50 else (P['warning'] if conv >= 25 else P['danger'])
                    step_conv = (
                        f'<div style="text-align:center;color:{arrow_color};font-size:11px;'
                        f'font-weight:700;margin:1px 0;">&#8595; {conv}%</div>')
                funnel += step_conv + (
                    f'<div style="display:flex;justify-content:center;margin-bottom:2px;">'
                    f'<div style="width:{width}%;min-width:90px;background:{color};color:#fff;'
                    f'border-radius:6px;padding:9px 6px;text-align:center;transition:width .5s;'
                    f'box-shadow:0 1px 3px rgba(0,0,0,.12);">'
                    f'<div style="font-size:12px;font-weight:600;opacity:.95;">{label}</div>'
                    f'<div style="font-size:18px;font-weight:800;line-height:1.1;">{val}</div>'
                    f'</div></div>')
                prev_val = val

            rec.funnel_html = (
                f'<div style="font-family:inherit;padding:8px;">'
                f'<div style="display:flex;gap:10px;margin-bottom:14px;">'
                f'<div style="flex:1;background:{P["muted"]}14;border-radius:8px;padding:10px;text-align:center;">'
                f'<div style="font-size:26px;font-weight:800;color:{P["primary"]};">{rec.funnel_conversion_pct}%</div>'
                f'<div style="font-size:12px;color:{P["muted"]};">Conversión total</div></div>'
                f'<div style="flex:1;background:{P["success"]}14;border-radius:8px;padding:10px;text-align:center;">'
                f'<div style="font-size:26px;font-weight:800;color:{P["success"]};">{won}</div>'
                f'<div style="font-size:12px;color:{P["muted"]};">Ganados</div></div>'
                f'<div style="flex:1;background:{P["danger"]}14;border-radius:8px;padding:10px;text-align:center;">'
                f'<div style="font-size:26px;font-weight:800;color:{P["danger"]};">{lost}</div>'
                f'<div style="font-size:12px;color:{P["muted"]};">Perdidos</div></div>'
                f'</div>{funnel}</div>')


    # ──────────────────────────────────────────────────────────────────
    # NIVEL 2: Comparativa AVM masiva
    # ──────────────────────────────────────────────────────────────────
    # ──────────────────────────────────────────────────────────────────
    # NIVEL 3: Gráficos inline (ventas por mes, leads por fuente)
    # ──────────────────────────────────────────────────────────────────
    _CHART_ANIM_CSS = """
<style>
@keyframes barUp {
    from { transform: scaleY(0); }
    to   { transform: scaleY(1); }
}
@keyframes barRight {
    from { transform: scaleX(0); }
    to   { transform: scaleX(1); }
}
</style>"""

    def _compute_charts(self):
        for rec in self:
            # ── Sales by month — vertical bars ───────────────────────
            self.env.cr.execute("""
                SELECT TO_CHAR(date_sold, 'Mon') as mes,
                       COUNT(*) as total,
                       COALESCE(SUM(price), 0) as revenue
                FROM estate_property
                WHERE state = 'sold' AND date_sold IS NOT NULL
                  AND date_sold >= (CURRENT_DATE - INTERVAL '6 months')
                GROUP BY TO_CHAR(date_sold, 'YYYY-MM'), TO_CHAR(date_sold, 'Mon')
                ORDER BY TO_CHAR(date_sold, 'YYYY-MM')
            """)
            sales_data = self.env.cr.dictfetchall()
            max_sales = max((r['total'] for r in sales_data), default=1) or 1

            bars = ''
            for i, r in enumerate(sales_data):
                h = max(int(r['total'] / max_sales * 140), 6)
                delay = round(i * 0.08, 2)
                bars += (
                    f'<div style="display:flex;flex-direction:column;align-items:center;flex:1;min-width:0;padding:0 3px;">'
                    f'<div style="font-size:11px;font-weight:600;color:#374151;margin-bottom:4px;">{r["total"]}</div>'
                    f'<div style="width:min(100%,44px);height:{h}px;background:#004274;border-radius:3px 3px 0 0;'
                    f'transform-origin:bottom;animation:barUp .55s ease-out {delay}s both;"></div>'
                    f'<div style="font-size:10px;color:#9ca3af;margin-top:4px;text-align:center;">{r["mes"]}</div>'
                    f'</div>'
                )
            if not bars:
                bars = '<div style="padding:24px;text-align:center;color:#9ca3af;font-size:13px;">Sin ventas en los últimos 6 meses</div>'

            rec.sales_chart_html = (
                self._CHART_ANIM_CSS +
                f'<div style="display:flex;align-items:flex-end;justify-content:space-between;'
                f'min-height:170px;width:100%;padding-top:8px;border-bottom:1px solid #f3f4f6;">'
                f'{bars}'
                f'</div>'
            )

            # A2: datos JSON para Chart.js
            rec.sales_chart_data = json.dumps({
                'type': 'bar',
                'label': 'Ventas',
                'labels': [r['mes'] for r in sales_data],
                'values': [r['total'] for r in sales_data],
                'revenues': [float(r['revenue']) for r in sales_data],
                'color': self._PALETTE['primary'],
            })

            # ── Leads by source — horizontal bars ────────────────────
            self.env.cr.execute("""
                SELECT COALESCE(s.name, 'Otro') as source,
                       COUNT(*) as total
                FROM crm_lead l
                LEFT JOIN estate_crm_lead_source s ON s.id = l.lead_source_id
                WHERE l.create_date >= (CURRENT_DATE - INTERVAL '3 months')
                GROUP BY s.name
                ORDER BY total DESC
                LIMIT 7
            """)
            lead_data = self.env.cr.dictfetchall()
            max_leads = max((r['total'] for r in lead_data), default=1) or 1
            palette = self._PALETTE['chart']
            hbars = ''
            for i, r in enumerate(lead_data):
                w = max(int(r['total'] / max_leads * 100), 4)
                color = palette[i % len(palette)]
                label = r['source']
                delay = round(i * 0.09, 2)
                hbars += (
                    f'<div style="margin-bottom:10px;">'
                    f'<div style="display:flex;justify-content:space-between;'
                    f'font-size:12px;color:#374151;margin-bottom:3px;">'
                    f'<span>{label}</span>'
                    f'<span style="font-weight:600;color:{color};">{r["total"]}</span>'
                    f'</div>'
                    f'<div style="background:#f3f4f6;border-radius:3px;height:10px;overflow:hidden;">'
                    f'<div style="width:{w}%;height:100%;background:{color};border-radius:3px;'
                    f'transform-origin:left;animation:barRight .6s ease-out {delay}s both;"></div>'
                    f'</div>'
                    f'</div>'
                )
            if not hbars:
                hbars = '<div style="padding:24px;text-align:center;color:#9ca3af;font-size:13px;">Sin leads recientes</div>'

            rec.leads_chart_html = (
                self._CHART_ANIM_CSS +
                f'<div style="width:100%;">{hbars}</div>'
            )

            # A2: datos JSON para Chart.js
            rec.leads_chart_data = json.dumps({
                'type': 'bar',
                'horizontal': True,
                'label': 'Leads',
                'labels': [r['source'] for r in lead_data],
                'values': [r['total'] for r in lead_data],
                'colors': [palette[i % len(palette)] for i in range(len(lead_data))],
            })

    # ──────────────────────────────────────────────────────────────────
    # NIVEL 3: Tendencias comparativas
    # ──────────────────────────────────────────────────────────────────
    def _compute_trends(self):
        for rec in self:
            cur_from, cur_to = rec._get_period_dates()
            prev_from, prev_to = rec._get_prev_period_dates()
            Property = self.env['estate.property'].sudo()
            Lead = self.env['crm.lead'].sudo()

            # Sales
            cur_sales = Property.search_count([
                ('state', '=', 'sold'),
                ('date_sold', '>=', cur_from),
                ('date_sold', '<=', cur_to)])
            prev_sales = Property.search_count([
                ('state', '=', 'sold'),
                ('date_sold', '>=', prev_from),
                ('date_sold', '<=', prev_to)])
            rec.trend_sales_current = cur_sales
            rec.trend_sales_prev = prev_sales
            rec.trend_sales_pct = round((cur_sales - prev_sales) / prev_sales * 100, 1) if prev_sales else 0

            # Leads
            cur_leads = Lead.search_count([
                ('create_date', '>=', str(cur_from)),
                ('create_date', '<=', str(cur_to) + ' 23:59:59')])
            prev_leads = Lead.search_count([
                ('create_date', '>=', str(prev_from)),
                ('create_date', '<=', str(prev_to) + ' 23:59:59')])
            rec.trend_leads_current = cur_leads
            rec.trend_leads_prev = prev_leads
            rec.trend_leads_pct = round((cur_leads - prev_leads) / prev_leads * 100, 1) if prev_leads else 0

            # Revenue
            cur_rev = sum(Property.search([
                ('state', '=', 'sold'),
                ('date_sold', '>=', cur_from),
                ('date_sold', '<=', cur_to)]).mapped('price'))
            prev_rev = sum(Property.search([
                ('state', '=', 'sold'),
                ('date_sold', '>=', prev_from),
                ('date_sold', '<=', prev_to)]).mapped('price'))
            rev_pct = round((cur_rev - prev_rev) / prev_rev * 100, 1) if prev_rev else 0

            def _arrow(pct, invert=False):
                good = pct > 0 if not invert else pct < 0
                color = '#16a34a' if good else '#dc2626' if pct != 0 else '#6b7280'
                arrow = '▲' if pct > 0 else '▼' if pct < 0 else '—'
                return f'<span style="color:{color};font-weight:700;">{arrow} {abs(pct)}%</span>'

            rec.trend_html = f'''
            <div style="font-family:-apple-system,sans-serif;">
                <table style="width:100%;border-collapse:collapse;background:white;border-radius:10px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.06);">
                    <thead><tr style="background:#004274;color:white;">
                        <th style="padding:12px;text-align:left;">Métrica</th>
                        <th style="padding:12px;text-align:center;">Período Actual</th>
                        <th style="padding:12px;text-align:center;">Período Anterior</th>
                        <th style="padding:12px;text-align:center;">Variación</th>
                    </tr></thead>
                    <tbody>
                        <tr style="border-bottom:1px solid #f1f5f9;">
                            <td style="padding:12px;font-weight:600;">Ventas</td>
                            <td style="padding:12px;text-align:center;font-size:18px;font-weight:700;">{cur_sales}</td>
                            <td style="padding:12px;text-align:center;color:#6b7280;">{prev_sales}</td>
                            <td style="padding:12px;text-align:center;">{_arrow(rec.trend_sales_pct)}</td>
                        </tr>
                        <tr style="border-bottom:1px solid #f1f5f9;">
                            <td style="padding:12px;font-weight:600;">Leads Nuevos</td>
                            <td style="padding:12px;text-align:center;font-size:18px;font-weight:700;">{cur_leads}</td>
                            <td style="padding:12px;text-align:center;color:#6b7280;">{prev_leads}</td>
                            <td style="padding:12px;text-align:center;">{_arrow(rec.trend_leads_pct)}</td>
                        </tr>
                        <tr>
                            <td style="padding:12px;font-weight:600;">Ingresos</td>
                            <td style="padding:12px;text-align:center;font-size:18px;font-weight:700;">${cur_rev:,.0f}</td>
                            <td style="padding:12px;text-align:center;color:#6b7280;">${prev_rev:,.0f}</td>
                            <td style="padding:12px;text-align:center;">{_arrow(rev_pct)}</td>
                        </tr>
                    </tbody>
                </table>
            </div>'''

    # ── API para el Dashboard OWL (pantalla a medida, sin formulario) ──
    @api.model
    def get_dashboard_data(self, user_id=False, period='month'):
        """Devuelve los DATOS CRUDOS del dashboard (KPIs, embudo, tendencia,
        gráficos y ranking) para renderizarlos NATIVO en OWL (limpio y lineal).
        Reutiliza toda la lógica de cálculo del modelo."""
        import json as _json
        rec = self.create({
            'filter_user_id': user_id or False,
            'filter_period': period or 'month',
        })
        num_fields = [
            'display_title', 'total_properties', 'available_properties', 'sold_properties',
            'stagnant_properties', 'total_clients', 'active_clients', 'appointments_done',
            'active_offers_count', 'active_contracts_count', 'contracts_expiring',
            'avg_days_on_market', 'monthly_commissions', 'won_revenue_month',
            'pending_revenue', 'pending_invoices_amount',
            'funnel_leads_new', 'funnel_visits_done', 'funnel_offers_made',
            'funnel_won', 'funnel_lost', 'funnel_conversion_pct',
            'trend_sales_current', 'trend_sales_prev', 'trend_sales_pct',
            'trend_leads_current', 'trend_leads_prev', 'trend_leads_pct',
            'sales_chart_data', 'leads_chart_data',
        ]
        vals = rec.read(num_fields)[0]
        vals.pop('id', None)

        def _parse(s):
            try:
                return _json.loads(s) if s else {}
            except Exception:
                return {}
        sales_chart = _parse(vals.pop('sales_chart_data', ''))
        leads_chart = _parse(vals.pop('leads_chart_data', ''))

        # Ranking de asesores en el período (ventas, ingresos, comisión est.)
        date_from, date_to = rec._get_period_dates()
        self.env.cr.execute("""
            SELECT COALESCE(pp.name, u.login) AS name,
                   COUNT(p.id) AS sales,
                   COALESCE(SUM(p.price), 0) AS revenue
            FROM estate_property p
            JOIN res_users u ON u.id = p.user_id
            LEFT JOIN res_partner pp ON pp.id = u.partner_id
            WHERE p.state IN ('sold', 'rented')
              AND p.date_sold >= %s AND p.date_sold <= %s
            GROUP BY pp.name, u.login
            ORDER BY sales DESC, revenue DESC
            LIMIT 10
        """, (date_from, date_to))
        ranking = self.env.cr.dictfetchall()
        for r in ranking:
            r['commission'] = round((r['revenue'] or 0) * 0.05, 2)

        advisors = self.env['res.users'].search(
            [('share', '=', False), ('active', '=', True)], order='name').read(['id', 'name'])
        periods = [{'value': v, 'label': l} for v, l in rec._fields['filter_period'].selection]
        return {
            'kpis': vals,
            'salesChart': sales_chart,
            'leadsChart': leads_chart,
            'ranking': ranking,
            'advisors': advisors,
            'periods': periods,
        }

    @api.model
    def dashboard_ask_ai(self, query, user_id=False, period='month'):
        """Consulta a la IA desde el dashboard OWL y devuelve la respuesta HTML."""
        rec = self.create({
            'filter_user_id': user_id or False,
            'filter_period': period or 'month',
            'ai_query_text': (query or '').strip(),
        })
        rec.action_ask_ai_dashboard()
        return rec.ai_response_html or ''

    # ── Botones de acción rápida desde dashboard ──────────────────────
    def action_ask_ai_dashboard(self):
        """Query the AI about the current dashboard data."""
        self.ensure_one()
        import logging
        _logger = logging.getLogger(__name__)

        query = (self.ai_query_text or '').strip()
        if not query:
            self.write({'ai_response_html': '<p style="color:#6b7280">Escribe una consulta primero.</p>'})
            return self._reload_dashboard()

        ICP = self.env['ir.config_parameter'].sudo()
        api_key = ICP.get_param('estate_ai.api_key', '')
        if not api_key:
            self.write({'ai_response_html': '<p style="color:#dc2626">No hay API Key configurada. Ve a Configuracion &gt; Agente IA.</p>'})
            return self._reload_dashboard()

        period_from, period_to = self._get_period_dates()
        context = (
            f"Período analizado: {period_from} al {period_to}\n"
            f"Propiedades totales: {self.total_properties}\n"
            f"Propiedades disponibles: {self.available_properties}\n"
            f"Propiedades vendidas (período): {self.sold_properties}\n"
            f"Propiedades estancadas (+90 días): {self.stagnant_properties}\n"
            f"Clientes activos: {self.active_clients}\n"
            f"Ofertas activas: {self.active_offers_count}\n"
            f"Contratos activos: {self.active_contracts_count}\n"
            f"Contratos por vencer: {self.contracts_expiring}\n"
            f"Visitas realizadas: {self.appointments_done}\n"
            f"Comisiones del período: ${self.monthly_commissions:,.2f}\n"
            f"Ingresos cerrados: ${self.won_revenue_month:,.2f}\n"
            f"Pipeline pendiente: ${self.pending_revenue:,.2f}\n"
            f"Facturas pendientes: ${self.pending_invoices_amount:,.2f}\n"
            f"Promedio días en mercado: {self.avg_days_on_market:.1f}\n"
        )

        # ── Datos granulares (ranking de asesores y desglose) para que la IA
        #    pueda responder preguntas como "el mejor asesor" o "ventas por tipo". ──
        from collections import defaultdict
        Property = self.env['estate.property']
        ufilter = [('user_id', '=', self.filter_user_id.id)] if self.filter_user_id else []

        def _ranking(d_from, d_to):
            sold = Property.search(ufilter + [
                ('state', '=', 'sold'),
                ('date_sold', '>=', d_from), ('date_sold', '<=', d_to)])
            agg = defaultdict(lambda: {'n': 0, 'rev': 0.0, 'com': 0.0})
            for p in sold:
                k = p.user_id.name or 'Sin asignar'
                agg[k]['n'] += 1
                agg[k]['rev'] += p.price or 0.0
                agg[k]['com'] += p.commission_amount or 0.0
            return sorted(agg.items(), key=lambda kv: kv[1]['rev'], reverse=True)

        def _fmt_ranking(rk):
            if not rk:
                return "  (sin ventas en el rango)\n"
            return ''.join(
                f"  {i}. {name}: {d['n']} ventas, ${d['rev']:,.0f} ingresos, "
                f"${d['com']:,.0f} comisiones\n"
                for i, (name, d) in enumerate(rk[:10], 1))

        today = fields.Date.today()
        year_start = today.replace(month=1, day=1)
        context += "\nRANKING DE ASESORES — PERÍODO SELECCIONADO (ordenado por ingresos):\n"
        context += _fmt_ranking(_ranking(period_from, period_to))
        context += "\nRANKING DE ASESORES — AÑO EN CURSO (ordenado por ingresos):\n"
        context += _fmt_ranking(_ranking(year_start, today))

        type_agg = defaultdict(int)
        for p in Property.search(ufilter):
            type_agg[p.property_type_id.name or 'Sin tipo'] += 1
        if type_agg:
            context += "\nPROPIEDADES POR TIPO:\n"
            context += ''.join(
                f"  {t}: {n}\n"
                for t, n in sorted(type_agg.items(), key=lambda kv: kv[1], reverse=True))

        prompt = (
            "Eres un analista inmobiliario profesional. Responde la consulta usando TODOS los "
            "datos proporcionados, incluido el RANKING DE ASESORES. Si te preguntan por el mejor "
            "asesor o por desempeño individual, USA el ranking (no digas que no tienes esos datos). "
            "Indica el rango temporal cuando sea relevante. Se conciso, directo y practico.\n\n"
            f"DATOS DEL DASHBOARD:\n{context}\n"
            f"CONSULTA: {query}\n\n"
            "Responde en HTML simple (usa <p>, <ul>, <li>, <strong>). "
            "Sin CSS inline, sin markdown, sin bloques de codigo."
        )

        answer = None
        try:
            answer = self.env['estate.genai.mixin']._genai_generate(
                prompt, temperature=0.4, max_output_tokens=4096,
            )
            answer = self.env['estate.genai.mixin']._genai_strip_fences(answer)
        except Exception as e_gemini:
            try:
                import openai as _openai
                oa = _openai.OpenAI(api_key=api_key)
                resp = oa.chat.completions.create(
                    model='gpt-4o-mini',
                    messages=[{'role': 'user', 'content': prompt}],
                )
                answer = (resp.choices[0].message.content or '').replace('```html', '').replace('```', '').strip()
            except Exception as e_openai:
                _logger.error("Dashboard AI error — Gemini: %s | OpenAI: %s", e_gemini, e_openai)
                answer = f'<p style="color:#dc2626">Error al consultar la IA: {e_gemini}</p>'

        self.write({'ai_response_html': answer or '<p>Sin respuesta.</p>'})
        return self._reload_dashboard()

