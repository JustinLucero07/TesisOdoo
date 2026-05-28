from odoo import models, fields, api
from datetime import timedelta, date as _date
import calendar as _cal


class EstateDashboard(models.TransientModel):
    _name = 'estate.dashboard'
    _description = 'Dashboard Inmobiliario'
    _rec_name = 'display_title'

    display_title = fields.Char(
        string='Dashboard', compute='_compute_display_title')

    @api.depends()
    def _compute_display_title(self):
        for rec in self:
            rec.display_title = 'Dashboard General'

    # ── Banner HTML (KPI cards + header) ─────────────────────────────
    kpi_header_html = fields.Html(
        string='Resumen Ejecutivo', compute='_compute_kpi_header', sanitize=False)

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

    # Mapa de Propiedades
    map_html = fields.Html(
        string='Mapa Geográfico', compute='_compute_map_html', sanitize=False)

    # Sidebar derecho persistente
    sidebar_html = fields.Html(
        string='Panel Lateral', compute='_compute_sidebar', sanitize=False)

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
    avm_comparison_html = fields.Html(
        string='Comparativa AVM', compute='_compute_avm_comparison', sanitize=False)

    # ── Gráficos inline (sparklines) ───────────────────────────────
    sales_chart_html = fields.Html(
        string='Ventas del Período', compute='_compute_charts', sanitize=False)
    leads_chart_html = fields.Html(
        string='Leads por Fuente', compute='_compute_charts', sanitize=False)

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
        self._compute_kpi_header()
        self._compute_sidebar()
        self._compute_advisor_ranking()
        self._compute_funnel()
        self._compute_avm_comparison()
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

    @api.depends('filter_user_id', 'filter_period', 'filter_date_from', 'filter_date_to')
    def _compute_kpi_header(self):
        for rec in self:
            today = fields.Date.today()
            period_from, period_to = rec._get_period_dates()
            user_domain = [('user_id', '=', rec.filter_user_id.id)] if rec.filter_user_id else []

            Property = self.env['estate.property']
            total = Property.search_count(user_domain)
            avail = Property.search_count(user_domain + [('state', '=', 'available')])
            sold  = Property.search_count(user_domain + [('state', '=', 'sold')])

            sold_period = Property.search(user_domain + [
                ('state', '=', 'sold'),
                ('date_sold', '>=', period_from),
                ('date_sold', '<=', period_to),
            ])
            revenue = sum(sold_period.mapped('price'))
            commissions = sum(sold_period.mapped('commission_amount'))
            avg_price = (revenue / len(sold_period)) if sold_period else 0.0

            lead_count = self.env['crm.lead'].search_count([
                ('type', '=', 'opportunity'),
                ('probability', '>', 0), ('probability', '<', 100),
            ])

            period_label = dict([
                ('month', 'Mes Actual'), ('quarter', 'Trimestre'), ('year', 'Año'),
                ('last_month', 'Mes Anterior'), ('custom', 'Período Custom'),
            ]).get(rec.filter_period or 'month', 'Período')

            def kpi(icon, label, value, color):
                return (
                    f'<div style="flex:1;min-width:130px;background:#fff;border-radius:8px;'
                    f'padding:11px 13px;border:1px solid #e5e7eb;border-left:3px solid {color};">'
                    f'<div style="display:flex;align-items:center;gap:5px;margin-bottom:3px;">'
                    f'<i class="fa {icon}" style="font-size:13px;color:{color}"/>'
                    f'<span style="font-size:10px;color:#6b7280;font-weight:500;'
                    f'text-transform:uppercase;letter-spacing:.05em;">{label}</span>'
                    f'</div>'
                    f'<div style="font-size:20px;font-weight:700;color:#111827;">{value}</div>'
                    f'</div>'
                )

            rec.kpi_header_html = f'''
            <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;padding:0 0 12px;">
                <div style="display:flex;align-items:baseline;justify-content:space-between;
                            padding-bottom:8px;border-bottom:1px solid #e5e7eb;margin-bottom:12px;">
                    <div>
                        <span style="font-size:15px;font-weight:700;color:#111827;">Dashboard Inmobiliario</span>
                        <span style="font-size:12px;color:#6b7280;margin-left:8px;">
                            {period_label} · {today.strftime("%d/%m/%Y")}
                            {"&nbsp;·&nbsp;" + rec.filter_user_id.name if rec.filter_user_id else ""}
                        </span>
                    </div>
                    <span style="font-size:12px;color:#6b7280;white-space:nowrap;">
                        <strong style="color:#111827;">{len(sold_period)}</strong> ventas en período
                    </span>
                </div>
                <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:8px;">
                    {kpi("fa-home", "Total Propiedades", total, "#1e40af")}
                    {kpi("fa-check-circle", "Disponibles", avail, "#1e40af")}
                    {kpi("fa-handshake-o", "Vendidas", sold, "#1e40af")}
                    {kpi("fa-users", "Leads Activos", lead_count, "#1e40af")}
                </div>
                <div style="display:flex;flex-wrap:wrap;gap:8px;">
                    {kpi("fa-dollar", f"Ingresos ({period_label})", f"${revenue:,.0f}", "#1e40af")}
                    {kpi("fa-percent", f"Comisiones ({period_label})", f"${commissions:,.0f}", "#1e40af")}
                    {kpi("fa-bar-chart", "Precio Prom. Venta", f"${avg_price:,.0f}", "#1e40af")}
                </div>
            </div>
            '''

    @api.depends('filter_user_id', 'filter_period', 'filter_date_from', 'filter_date_to')
    def _compute_sidebar(self):
        for rec in self:
            today = fields.Date.today()
            period_from, period_to = rec._get_period_dates()
            user_domain = [('user_id', '=', rec.filter_user_id.id)] if rec.filter_user_id else []
            Property = self.env['estate.property']

            # ── Mini resumen de período ─────────────────────────────
            sold_period = Property.search(user_domain + [
                ('state', '=', 'sold'),
                ('date_sold', '>=', period_from),
                ('date_sold', '<=', period_to),
            ])
            revenue = sum(sold_period.mapped('price'))
            commissions = sum(sold_period.mapped('commission_amount'))
            avail = Property.search_count(user_domain + [('state', '=', 'available')])
            lead_count = self.env['crm.lead'].search_count([
                ('type', '=', 'opportunity'), ('probability', '>', 0), ('probability', '<', 100),
            ])
            visits_month = self.env['calendar.event'].search_count([
                ('property_id', '!=', False), ('visit_state', '=', 'done'),
                ('start', '>=', str(today.replace(day=1))),
            ])

            period_label = dict([
                ('month', 'Mes Actual'), ('quarter', 'Trimestre'), ('year', 'Año'),
                ('last_month', 'Mes Anterior'), ('custom', 'Personalizado'),
            ]).get(rec.filter_period or 'month', 'Período')

            def stat_row(icon, label, value, color='#374151'):
                return (
                    f'<div style="display:flex;align-items:center;justify-content:space-between;'
                    f'padding:7px 0;border-bottom:1px solid #f3f4f6;">'
                    f'<span style="display:flex;align-items:center;gap:6px;font-size:12px;color:#6b7280;">'
                    f'<i class="fa {icon}" style="color:{color};width:14px;text-align:center;"/>{label}</span>'
                    f'<span style="font-weight:700;font-size:13px;color:{color};">{value}</span>'
                    f'</div>'
                )

            # ── Alertas ─────────────────────────────────────────────
            overdue_count = self.env['estate.payment'].search_count([
                ('state', '=', 'pending'), ('date', '<', today),
            ])
            expiring_15 = Property.search_count([
                ('contract_end_date', '!=', False),
                ('contract_end_date', '<=', today + timedelta(days=15)),
                ('state', 'in', ('available', 'reserved')),
            ])
            hot_stale = self.env['crm.lead'].search_count([
                ('lead_temperature', 'in', ['hot', 'boiling']),
                ('write_date', '<=', str(fields.Datetime.now() - timedelta(days=7))),
                ('type', '=', 'opportunity'),
            ])

            alerts_html = ''
            if overdue_count:
                alerts_html += (
                    f'<div style="display:flex;align-items:center;gap:6px;padding:4px 8px;'
                    f'background:#fef2f2;border-radius:6px;margin-bottom:4px;">'
                    f'<i class="fa fa-exclamation-circle" style="color:#dc2626;"/>'
                    f'<span style="font-size:12px;color:#dc2626;font-weight:600;">'
                    f'{overdue_count} pago{"s" if overdue_count > 1 else ""} vencido{"s" if overdue_count > 1 else ""}</span></div>'
                )
            if expiring_15:
                alerts_html += (
                    f'<div style="display:flex;align-items:center;gap:6px;padding:4px 8px;'
                    f'background:#fffbeb;border-radius:6px;margin-bottom:4px;">'
                    f'<i class="fa fa-calendar-times-o" style="color:#d97706;"/>'
                    f'<span style="font-size:12px;color:#d97706;font-weight:600;">'
                    f'{expiring_15} contrato{"s" if expiring_15 > 1 else ""} por vencer</span></div>'
                )
            if hot_stale:
                alerts_html += (
                    f'<div style="display:flex;align-items:center;gap:6px;padding:4px 8px;'
                    f'background:#fffbeb;border-radius:6px;margin-bottom:4px;">'
                    f'<i class="fa fa-fire" style="color:#d97706;"/>'
                    f'<span style="font-size:12px;color:#d97706;font-weight:600;">'
                    f'{hot_stale} lead{"s" if hot_stale > 1 else ""} caliente{"s" if hot_stale > 1 else ""} inactivo{"s" if hot_stale > 1 else ""}</span></div>'
                )
            if not alerts_html:
                alerts_html = (
                    '<div style="display:flex;align-items:center;gap:6px;padding:4px 8px;'
                    'background:#f0fdf4;border-radius:6px;">'
                    '<i class="fa fa-check-circle" style="color:#16a34a;"/>'
                    '<span style="font-size:12px;color:#16a34a;font-weight:600;">Sin alertas críticas</span></div>'
                )

            # ── Visitas de hoy ───────────────────────────────────────
            today_visits = self.env['calendar.event'].search([
                ('property_id', '!=', False),
                ('start', '>=', str(today) + ' 00:00:00'),
                ('start', '<=', str(today) + ' 23:59:59'),
                ('visit_state', '!=', 'cancelled'),
            ], order='start asc', limit=5)

            visits_rows = ''
            for v in today_visits:
                time_str = v.start.strftime('%H:%M') if v.start else '—'
                prop_name = (v.property_id.title or v.property_id.name or v.name or '—')[:24]
                partner_name = (v.partner_id.name or '—')[:18]
                state_map = {'scheduled': ('fa-clock-o', '#d97706'), 'done': ('fa-check-circle', '#16a34a')}
                ic, ic_c = state_map.get(v.visit_state, ('fa-circle-o', '#9ca3af'))
                visits_rows += (
                    f'<div style="display:flex;gap:6px;padding:6px 0;border-bottom:1px solid #f3f4f6;">'
                    f'<i class="fa {ic}" style="color:{ic_c};font-size:11px;margin-top:2px;flex-shrink:0;"/>'
                    f'<div style="flex:1;min-width:0;">'
                    f'<div style="font-size:11px;font-weight:600;color:#111827;white-space:nowrap;'
                    f'overflow:hidden;text-overflow:ellipsis;">{time_str} · {prop_name}</div>'
                    f'<div style="font-size:10px;color:#9ca3af;">{partner_name}</div>'
                    f'</div></div>'
                )
            if not visits_rows:
                visits_rows = (
                    '<div style="padding:8px 0;color:#9ca3af;font-size:11px;font-style:italic;text-align:center;">'
                    'Sin visitas programadas hoy</div>'
                )

            # ── Resumen de propiedades disponibles ──────────────────
            top_available = Property.search(
                user_domain + [('state', '=', 'available')],
                order='price desc', limit=3
            )
            props_rows = ''
            for p in top_available:
                props_rows += (
                    f'<div style="padding:5px 0;border-bottom:1px solid #f3f4f6;">'
                    f'<div style="font-size:11px;font-weight:600;color:#111827;white-space:nowrap;'
                    f'overflow:hidden;text-overflow:ellipsis;">{(p.title or p.name or "—")[:24]}</div>'
                    f'<div style="display:flex;justify-content:space-between;margin-top:1px;">'
                    f'<span style="font-size:10px;color:#6b7280;">{p.city or "—"}</span>'
                    f'<span style="font-size:11px;font-weight:700;color:#2563eb;">${p.price:,.0f}</span>'
                    f'</div></div>'
                )
            if not props_rows:
                props_rows = '<div style="padding:6px 0;color:#9ca3af;font-size:11px;font-style:italic;text-align:center;">Sin propiedades disponibles</div>'

            def section(title, icon, color, content):
                return (
                    f'<div style="margin-bottom:14px;">'
                    f'<div style="font-size:10px;font-weight:700;color:#6b7280;text-transform:uppercase;'
                    f'letter-spacing:.06em;margin-bottom:6px;display:flex;align-items:center;gap:4px;">'
                    f'<i class="fa {icon}" style="color:{color};"/>{title}</div>'
                    f'{content}</div>'
                )

            def card(title, icon, color, content):
                return (
                    f'<div style="background:#fff;border:1px solid #e5e7eb;border-radius:8px;'
                    f'padding:14px;margin-bottom:12px;">'
                    f'<div style="font-size:10px;font-weight:700;color:{color};text-transform:uppercase;'
                    f'letter-spacing:.06em;margin-bottom:10px;display:flex;align-items:center;gap:5px;">'
                    f'<i class="fa {icon}"/>{title}</div>'
                    f'{content}'
                    f'</div>'
                )

            metrics_html = (
                stat_row("fa-handshake-o", "Ventas", len(sold_period), "#1e40af") +
                stat_row("fa-dollar", "Ingresos", f"${revenue:,.0f}", "#1e40af") +
                stat_row("fa-percent", "Comisiones", f"${commissions:,.0f}", "#1e40af") +
                stat_row("fa-home", "Disponibles", avail, "#1e40af") +
                stat_row("fa-users", "Leads Activos", lead_count, "#1e40af") +
                stat_row("fa-calendar-check-o", "Visitas (mes)", visits_month, "#1e40af")
            )

            rec.sidebar_html = (
                f'<div style="font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',sans-serif;">'
                + card(period_label, "fa-bar-chart", "#1e40af", metrics_html)
                + card("Alertas", "fa-bell", "#1e40af", alerts_html)
                + card("Visitas de Hoy", "fa-calendar-check-o", "#1e40af",
                       visits_rows + '<div style="margin-top:10px;font-size:10px;font-weight:700;'
                       f'color:#1e40af;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px;'
                       f'display:flex;align-items:center;gap:5px;"><i class="fa fa-star"/>Propiedades Destacadas</div>'
                       + props_rows)
                + '</div>'
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
                        <tr style="background:#1e40af;color:white;">
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

    def _compute_map_html(self):
        """Renders the property map via an iframe pointing to the dedicated map endpoint."""
        for rec in self:
            rec.map_html = (
                '<iframe src="/estate_reports/map/embed" '
                'style="width:100%;height:500px;border:none;border-radius:10px;" '
                'allow="fullscreen"></iframe>'
            )

    # ── Botones de navegación desde los stat buttons ──────────────────

    def _action_open_property_list(self, domain, name):
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': 'estate.property',
            'view_mode': 'list,form',
            'domain': domain,
            'target': 'current',
        }

    def action_open_all_properties(self):
        return self._action_open_property_list([], 'Todas las Propiedades')

    def action_open_available(self):
        return self._action_open_property_list([('state', '=', 'available')], 'Propiedades Disponibles')

    def action_open_sold(self):
        return self._action_open_property_list([('state', '=', 'sold')], 'Propiedades Vendidas')

    def action_open_stagnant(self):
        cutoff_45 = fields.Date.today() - timedelta(days=45)
        stagnant_ids = []
        available_old = self.env['estate.property'].search([
            ('state', '=', 'available'), ('date_listed', '<=', cutoff_45)
        ])
        CalEvent = self.env['calendar.event'].sudo()
        for prop in available_old:
            if not CalEvent.search_count([
                ('property_id', '=', prop.id),
                ('visit_state', '=', 'done'),
                ('start', '>=', fields.Datetime.to_datetime(cutoff_45)),
            ]):
                stagnant_ids.append(prop.id)
        return self._action_open_property_list([('id', 'in', stagnant_ids)], 'Propiedades Estancadas (+45 días)')

    def action_open_offers(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Ofertas Activas',
            'res_model': 'estate.property.offer',
            'view_mode': 'list,form',
            'domain': [('state', 'in', ('submitted', 'countered', 'accepted'))],
            'target': 'current',
        }

    def action_open_contracts(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Contratos Activos',
            'res_model': 'estate.contract',
            'view_mode': 'list,form',
            'domain': [('state', '=', 'active')],
            'target': 'current',
        }

    def action_open_sale_orders(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Órdenes de Venta',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [('property_id', '!=', False), ('state', 'in', ('sale', 'done'))],
            'target': 'current',
        }

    def action_open_opportunities(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Oportunidades Activas',
            'res_model': 'crm.lead',
            'view_mode': 'list,form',
            'domain': [('type', '=', 'opportunity'), ('probability', '>', 0), ('probability', '<', 100)],
            'target': 'current',
        }

    def action_open_appointments(self):
        today = fields.Date.today()
        first_day = today.replace(day=1)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Visitas Realizadas (Mes)',
            'res_model': 'calendar.event',
            'view_mode': 'list,form',
            'domain': [('property_id', '!=', False), ('visit_state', '=', 'done'), ('start', '>=', first_day)],
            'target': 'current',
        }

    def action_open_expiring_contracts(self):
        limit = fields.Date.today() + timedelta(days=30)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Contratos por Vencer (30 días)',
            'res_model': 'estate.property',
            'view_mode': 'list,form',
            'domain': [
                ('contract_end_date', '!=', False),
                ('contract_end_date', '<=', limit),
                ('state', 'in', ('available', 'reserved')),
            ],
            'target': 'current',
        }

    @api.model
    def get_dashboard_data(self):
        """Return dashboard data for client_side rendering."""
        dashboard = self.create({})
        Property = self.env['estate.property']

        # Propiedades por tipo
        self.env.cr.execute("""
            SELECT pt.name as type_name, COUNT(*) as count
            FROM estate_property p
            JOIN estate_property_type pt ON p.property_type_id = pt.id
            WHERE p.active = True
            GROUP BY pt.name
            ORDER BY count DESC
        """)
        properties_by_type = self.env.cr.dictfetchall()

        # Propiedades por ciudad
        self.env.cr.execute("""
            SELECT COALESCE(city, 'Sin ciudad') as city_name, COUNT(*) as count
            FROM estate_property
            WHERE active = True
            GROUP BY city
            ORDER BY count DESC
        """)
        properties_by_city = self.env.cr.dictfetchall()

        # Ventas por mes (últimos 6 meses)
        self.env.cr.execute("""
            SELECT TO_CHAR(date_sold, 'YYYY-MM') as month,
                   COUNT(*) as count,
                   SUM(price) as total
            FROM estate_property
            WHERE state = 'sold' AND date_sold IS NOT NULL
            GROUP BY TO_CHAR(date_sold, 'YYYY-MM')
            ORDER BY month DESC
            LIMIT 6
        """)
        sales_by_month = self.env.cr.dictfetchall()

        return {
            'total_properties': dashboard.total_properties,
            'available_properties': dashboard.available_properties,
            'sold_properties': dashboard.sold_properties,
            'total_clients': dashboard.total_clients,
            'active_clients': dashboard.active_clients,
            'avg_days_on_market': dashboard.avg_days_on_market,
            'appointments_done': dashboard.appointments_done,
            'contracts_expiring': dashboard.contracts_expiring,
            'properties_by_type': properties_by_type,
            'properties_by_city': properties_by_city,
            'sales_by_month': sales_by_month,
        }

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

            # Funnel visualization
            steps = [
                ('Leads Nuevos', total_new, '#3b82f6'),
                ('Visitas', visits_done, '#8b5cf6'),
                ('Ofertas', offers_made, '#f59e0b'),
                ('Ganados', won, '#16a34a'),
                ('Perdidos', lost, '#dc2626'),
            ]
            max_val = max(total_new, 1)
            bars = ''
            for label, val, color in steps:
                pct_of_max = max(val / max_val * 100, 3) if val else 3
                pct_of_leads = round(val / total_new * 100, 1) if total_new else 0
                bars += f'''
                <div style="margin-bottom:8px;">
                    <div style="display:flex;justify-content:space-between;margin-bottom:2px;">
                        <span style="font-weight:600;font-size:13px;">{label}</span>
                        <span style="font-weight:700;color:{color};font-size:14px;">{val}
                            <span style="font-size:11px;color:#9ca3af;">({pct_of_leads}%)</span>
                        </span>
                    </div>
                    <div style="background:#f1f5f9;border-radius:6px;height:28px;overflow:hidden;">
                        <div style="width:{pct_of_max}%;height:100%;background:{color};border-radius:6px;
                                    transition:width 0.5s;display:flex;align-items:center;justify-content:center;
                                    color:white;font-weight:700;font-size:12px;">
                            {val if val > 0 else ''}
                        </div>
                    </div>
                </div>'''
            rec.funnel_html = f'''
            <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;padding:8px;">
                <div style="display:flex;justify-content:space-between;margin-bottom:16px;">
                    <div style="background:#f9fafb;border:1px solid #e5e7eb;padding:12px 20px;border-radius:8px;text-align:center;flex:1;margin-right:8px;">
                        <div style="font-size:28px;font-weight:700;color:#1e40af;">{rec.funnel_conversion_pct}%</div>
                        <div style="font-size:12px;color:#6b7280;">Tasa de Conversión</div>
                    </div>
                    <div style="background:#f9fafb;border:1px solid #e5e7eb;padding:12px 20px;border-radius:8px;text-align:center;flex:1;margin-left:8px;">
                        <div style="font-size:28px;font-weight:700;color:#1e40af;">{won}</div>
                        <div style="font-size:12px;color:#6b7280;">Cerrados</div>
                    </div>
                </div>
                {bars}
            </div>'''


    # ──────────────────────────────────────────────────────────────────
    # NIVEL 2: Comparativa AVM masiva
    # ──────────────────────────────────────────────────────────────────
    def _compute_avm_comparison(self):
        for rec in self:
            props = self.env['estate.property'].sudo().search([
                ('state', '=', 'available'),
                ('avm_estimated_price', '>', 0),
            ], order='city, title', limit=25)

            rows = ''
            for p in props:
                diff = p.price - p.avm_estimated_price
                diff_pct = round(diff / p.avm_estimated_price * 100, 1) if p.avm_estimated_price else 0
                if diff_pct > 10:
                    badge_color = '#dc2626'
                    badge_text = 'Sobrevaluada'
                elif diff_pct < -10:
                    badge_color = '#16a34a'
                    badge_text = 'Oportunidad'
                else:
                    badge_color = '#2563eb'
                    badge_text = 'Justo'
                rows += f'''<tr>
                    <td style="padding:8px;border-bottom:1px solid #f1f5f9;">{p.name}</td>
                    <td style="padding:8px;border-bottom:1px solid #f1f5f9;">{p.title}</td>
                    <td style="padding:8px;border-bottom:1px solid #f1f5f9;">{p.city or '-'}</td>
                    <td style="padding:8px;border-bottom:1px solid #f1f5f9;text-align:right;">${p.price:,.0f}</td>
                    <td style="padding:8px;border-bottom:1px solid #f1f5f9;text-align:right;">${p.avm_estimated_price:,.0f}</td>
                    <td style="padding:8px;border-bottom:1px solid #f1f5f9;text-align:right;color:{badge_color};font-weight:600;">
                        {'+' if diff_pct > 0 else ''}{diff_pct}%
                    </td>
                    <td style="padding:8px;border-bottom:1px solid #f1f5f9;text-align:center;">
                        <span style="background:{badge_color};color:white;padding:2px 10px;border-radius:12px;font-size:11px;">{badge_text}</span>
                    </td>
                </tr>'''

            if not rows:
                rows = '<tr><td colspan="7" style="padding:20px;text-align:center;color:#9ca3af;">Sin datos AVM. Ejecuta el AVM desde las propiedades.</td></tr>'

            # Count summary
            over = sum(1 for p in props if p.price > p.avm_estimated_price * 1.1)
            under = sum(1 for p in props if p.price < p.avm_estimated_price * 0.9)
            fair = len(props) - over - under

            rec.avm_comparison_html = f'''
            <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
                <div style="display:flex;gap:12px;margin-bottom:16px;">
                    <div style="flex:1;background:#f9fafb;border:1px solid #e5e7eb;padding:14px;border-radius:8px;text-align:center;">
                        <div style="font-size:26px;font-weight:700;color:#dc2626;">{over}</div>
                        <div style="font-size:11px;color:#6b7280;">Sobrevaluadas (&gt;10%)</div>
                    </div>
                    <div style="flex:1;background:#f9fafb;border:1px solid #e5e7eb;padding:14px;border-radius:8px;text-align:center;">
                        <div style="font-size:26px;font-weight:700;color:#1e40af;">{fair}</div>
                        <div style="font-size:11px;color:#6b7280;">Precio Justo</div>
                    </div>
                    <div style="flex:1;background:#f9fafb;border:1px solid #e5e7eb;padding:14px;border-radius:8px;text-align:center;">
                        <div style="font-size:26px;font-weight:700;color:#15803d;">{under}</div>
                        <div style="font-size:11px;color:#6b7280;">Oportunidades (&lt;-10%)</div>
                    </div>
                </div>
                <table style="width:100%;border-collapse:collapse;background:white;border-radius:10px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.06);">
                    <thead><tr style="background:#1e40af;color:white;">
                        <th style="padding:10px;text-align:left;">Ref</th>
                        <th style="padding:10px;text-align:left;">Propiedad</th>
                        <th style="padding:10px;">Ciudad</th>
                        <th style="padding:10px;text-align:right;">Precio Lista</th>
                        <th style="padding:10px;text-align:right;">AVM Estimado</th>
                        <th style="padding:10px;text-align:right;">Diferencia</th>
                        <th style="padding:10px;text-align:center;">Estado</th>
                    </tr></thead>
                    <tbody>{rows}</tbody>
                </table>
            </div>'''

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
                    f'<div style="width:min(100%,44px);height:{h}px;background:#1e40af;border-radius:3px 3px 0 0;'
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

            # ── Leads by source — horizontal bars ────────────────────
            self.env.cr.execute("""
                SELECT COALESCE(lead_source, 'other') as source,
                       COUNT(*) as total
                FROM crm_lead
                WHERE create_date >= (CURRENT_DATE - INTERVAL '3 months')
                GROUP BY lead_source
                ORDER BY total DESC
                LIMIT 7
            """)
            lead_data = self.env.cr.dictfetchall()
            max_leads = max((r['total'] for r in lead_data), default=1) or 1
            source_labels = {
                'website': 'Web', 'wordpress': 'WordPress', 'whatsapp': 'WhatsApp',
                'instagram': 'Instagram', 'facebook': 'Facebook', 'google': 'Google',
                'referral': 'Referido', 'phone': 'Telefono', 'walk_in': 'Visita directa',
                'portal': 'Portal', 'ai_agent': 'Agente IA', 'other': 'Otro',
            }
            palette = ['#3b82f6', '#8b5cf6', '#f59e0b', '#10b981', '#ec4899', '#6366f1', '#f97316']
            hbars = ''
            for i, r in enumerate(lead_data):
                w = max(int(r['total'] / max_leads * 100), 4)
                color = palette[i % len(palette)]
                label = source_labels.get(r['source'], r['source'])
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
                    <thead><tr style="background:#1e40af;color:white;">
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

    # ── Botones de acción rápida desde dashboard ──────────────────────
    def action_open_ai(self):
        return {'type': 'ir.actions.client', 'tag': 'estate_ai_open_chat'}

    def action_open_report_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Generar Reporte',
            'res_model': 'estate.report.wizard',
            'view_mode': 'form',
            'target': 'new',
        }

    def action_open_funnel_leads(self):
        period_from, period_to = self._get_period_dates()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Leads del Período',
            'res_model': 'crm.lead',
            'view_mode': 'list,form,kanban',
            'domain': [
                ('create_date', '>=', str(period_from)),
                ('create_date', '<=', str(period_to) + ' 23:59:59'),
            ],
            'target': 'current',
        }

    def action_open_overdue_payments(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Pagos Vencidos',
            'res_model': 'estate.payment',
            'view_mode': 'list,form',
            'domain': [('state', '=', 'pending'), ('date', '<', fields.Date.today())],
            'target': 'current',
        }

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

        prompt = (
            "Eres un analista inmobiliario profesional. Responde la consulta sobre el "
            "dashboard usando los datos proporcionados. Se conciso, directo y practico.\n\n"
            f"DATOS DEL DASHBOARD:\n{context}\n"
            f"CONSULTA: {query}\n\n"
            "Responde en HTML simple (usa <p>, <ul>, <li>, <strong>). "
            "Sin CSS inline, sin markdown, sin bloques de codigo."
        )

        answer = None
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
            )
            answer = (response.text or '').replace('```html', '').replace('```', '').strip()
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

    def _reload_dashboard(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'estate.dashboard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_sales_graph(self):
        return self.env.ref('estate_reports.action_sales_by_month').read()[0]

    def action_open_advisor_graph(self):
        return self.env.ref('estate_reports.action_sales_by_user').read()[0]

    def action_open_commission_wizard(self):
        return self.env.ref('estate_reports.estate_commission_wizard_action').read()[0]

    @api.model
    def _reset_board_customizations(self):
        board_view = self.env.ref('estate_reports.estate_board_view', raise_if_not_found=False)
        if board_view:
            self.env['ir.ui.view.custom'].sudo().search([('ref_id', '=', board_view.id)]).unlink()
