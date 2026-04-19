from odoo import models, fields, api
from datetime import timedelta, date as _date
import calendar as _cal


class EstateDashboard(models.TransientModel):
    _name = 'estate.dashboard'
    _description = 'Dashboard Inmobiliario'

    # KPIs Propiedades
    total_properties = fields.Integer(
        string='Total Propiedades', compute='_compute_kpis')
    available_properties = fields.Integer(
        string='Disponibles', compute='_compute_kpis')
    sold_properties = fields.Integer(
        string='Vendidas', compute='_compute_kpis')
    rented_properties = fields.Integer(
        string='Alquiladas', compute='_compute_kpis')

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
        string='Mapa Geográfico', compute='_compute_map_html')

    # Ranking de Asesores
    advisor_ranking_html = fields.Html(
        string='Ranking de Asesores', compute='_compute_advisor_ranking')
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
        string='Embudo de Conversión', compute='_compute_funnel')

    # ── Pestaña Arriendos — Ocupación ──────────────────────────────
    occupancy_html = fields.Html(
        string='Ocupación de Propiedades', compute='_compute_occupancy')
    total_rental_properties = fields.Integer(
        string='Propiedades en Arriendo', compute='_compute_occupancy')
    occupied_count = fields.Integer(
        string='Ocupadas', compute='_compute_occupancy')
    vacant_count = fields.Integer(
        string='Vacantes', compute='_compute_occupancy')
    occupancy_rate = fields.Float(
        string='Tasa de Ocupación %', compute='_compute_occupancy')

    # ── Pestaña Ventas — Comparativa AVM ───────────────────────────
    avm_comparison_html = fields.Html(
        string='Comparativa AVM', compute='_compute_avm_comparison')

    # ── Gráficos inline (sparklines) ───────────────────────────────
    sales_chart_html = fields.Html(
        string='Ventas del Período', compute='_compute_charts')
    leads_chart_html = fields.Html(
        string='Leads por Fuente', compute='_compute_charts')

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
        string='Tendencias', compute='_compute_trends')

    @api.onchange('filter_user_id', 'filter_period', 'filter_date_from', 'filter_date_to')
    def _onchange_filters(self):
        """Trigger all recomputations when filters change."""
        self._compute_kpis()
        self._compute_advisor_ranking()
        self._compute_funnel()
        self._compute_occupancy()
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
            rec.rented_properties = Property.search_count(
                user_domain + [('state', '=', 'rented')])

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
                ('state', 'in', ('available', 'rented', 'reserved')),
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

            medals = ['🥇', '🥈', '🥉']
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
                        <tr style="background:linear-gradient(135deg,#1a56db,#2E5AAC);color:white;">
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
        """Generates the Leaflet map HTML with property pins."""
        for rec in self:
            props = self.env['estate.property'].search([
                ('latitude', '!=', 0), 
                ('longitude', '!=', 0)
            ])
            
            pins_js = ""
            for p in props:
                color = 'blue'
                if p.state == 'sold': color = 'red'
                elif p.state == 'rented': color = 'green'
                elif p.state == 'available': color = 'blue'
                
                popup = f"<b>{p.title}</b><br/>{p.city}<br/>${p.price:,.2f}"
                pins_js += f"""
                    L.marker([{p.latitude}, {p.longitude}], {{
                        icon: L.divIcon({{
                            className: 'custom-div-icon',
                            html: "<div style='background-color:{color};' class='marker-pin'></div><i class='fa fa-home' style='color:white;position:absolute;top:3px;left:4.5px;font-size:10px;'></i>",
                            iconSize: [20, 30],
                            iconAnchor: [10, 30]
                        }})
                    }}).addTo(map).bindPopup("{popup}");
                """

            rec.map_html = f"""
                <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
                <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
                <style>
                    #estate_map {{ height: 400px; width: 100%; border-radius: 15px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }}
                    .marker-pin {{
                        width: 20px; height: 20px; border-radius: 50% 50% 50% 0;
                        position: absolute; transform: rotate(-45deg); left: 50%; top: 50%; margin: -10px 0 0 -10px;
                    }}
                </style>
                <div id="estate_map"></div>
                <script>
                    setTimeout(function() {{
                        var map = L.map('estate_map').setView([-2.897, -79.004], 13); // Default Cuenca
                        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(map);
                        {pins_js}
                        // Adjust view to fit all markers if any
                        var group = new L.featureGroup(map._layers);
                        if (Object.keys(map._layers).length > 2) {{
                            map.fitBounds(group.getBounds());
                        }}
                    }}, 500);
                </script>
            """

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

    def action_open_rented(self):
        return self._action_open_property_list([('state', '=', 'rented')], 'Propiedades Alquiladas')

    def action_open_sold(self):
        return self._action_open_property_list([('state', '=', 'sold')], 'Propiedades Vendidas')

    def action_open_stagnant(self):
        from datetime import timedelta
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
        from datetime import timedelta
        limit = fields.Date.today() + timedelta(days=30)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Contratos por Vencer (30 días)',
            'res_model': 'estate.property',
            'view_mode': 'list,form',
            'domain': [
                ('contract_end_date', '!=', False),
                ('contract_end_date', '<=', limit),
                ('state', 'in', ('available', 'rented', 'reserved')),
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
            'rented_properties': dashboard.rented_properties,
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
        """Genera y envía por email un reporte mensual al administrador."""
        from datetime import date, timedelta

        today = date.today()
        first_day = today.replace(day=1)
        last_month_last = first_day - timedelta(days=1)
        last_month_first = last_month_last.replace(day=1)

        Property = self.env['estate.property']
        Lead = self.env['crm.lead']

        sold_last_month = Property.search([
            ('state', '=', 'sold'),
            ('date_sold', '>=', last_month_first),
            ('date_sold', '<=', last_month_last),
        ])
        rented_last_month = Property.search([
            ('state', '=', 'rented'),
            ('date_sold', '>=', last_month_first),
            ('date_sold', '<=', last_month_last),
        ])
        won_leads = Lead.search([
            ('type', '=', 'opportunity'),
            ('stage_id.is_won', '=', True),
            ('date_closed', '>=', last_month_first),
            ('date_closed', '<=', last_month_last),
        ])
        lost_leads = Lead.search([
            ('active', '=', False),
            ('probability', '=', 0),
            ('date_closed', '>=', last_month_first),
            ('date_closed', '<=', last_month_last),
        ])

        total_commission = sum(sold_last_month.mapped('commission_amount'))
        total_revenue = sum(sold_last_month.mapped('price'))
        month_name = last_month_last.strftime('%B %Y')

        advisor_stats = {}
        for prop in sold_last_month:
            name = prop.user_id.name or 'Sin asignar'
            advisor_stats[name] = advisor_stats.get(name, 0) + 1
        top_advisors = sorted(advisor_stats.items(), key=lambda x: x[1], reverse=True)[:3]

        advisors_html = ''.join(
            f'<tr><td style="padding:8px">{i+1}. {n}</td>'
            f'<td style="padding:8px;text-align:center">{c}</td></tr>'
            for i, (n, c) in enumerate(top_advisors)
        ) or '<tr><td colspan="2" style="padding:8px;text-align:center;color:#6b7280">Sin ventas registradas</td></tr>'

        properties_html = ''.join(
            f'<tr>'
            f'<td style="padding:8px">{p.title}</td>'
            f'<td style="padding:8px">{p.city or "-"}</td>'
            f'<td style="padding:8px">${p.price:,.2f}</td>'
            f'<td style="padding:8px">${p.commission_amount:,.2f}</td>'
            f'</tr>'
            for p in sold_last_month[:10]
        ) or '<tr><td colspan="4" style="padding:8px;text-align:center;color:#6b7280">Sin ventas este mes</td></tr>'

        html_body = f"""
        <div style="font-family:Arial,sans-serif;max-width:700px;margin:0 auto;">
            <div style="background:#1a56db;color:white;padding:24px;border-radius:8px 8px 0 0;">
                <h1 style="margin:0;font-size:24px;">📊 Reporte Mensual Inmobiliario</h1>
                <p style="margin:8px 0 0;opacity:.85;">{month_name}</p>
            </div>
            <div style="background:#f8f9fa;padding:24px;border-radius:0 0 8px 8px;">
                <table style="width:100%;border-collapse:collapse;margin-bottom:24px;">
                    <tr>
                        <td style="padding:16px;text-align:center;background:white;border:1px solid #e5e7eb;">
                            <div style="font-size:32px;font-weight:bold;color:#16a34a;">{len(sold_last_month)}</div>
                            <div style="color:#6b7280;">Propiedades Vendidas</div>
                        </td>
                        <td style="padding:16px;text-align:center;background:white;border:1px solid #e5e7eb;">
                            <div style="font-size:32px;font-weight:bold;color:#2563eb;">{len(rented_last_month)}</div>
                            <div style="color:#6b7280;">Alquiladas</div>
                        </td>
                        <td style="padding:16px;text-align:center;background:white;border:1px solid #e5e7eb;">
                            <div style="font-size:32px;font-weight:bold;color:#7c3aed;">{len(won_leads)}</div>
                            <div style="color:#6b7280;">Leads Ganados</div>
                        </td>
                        <td style="padding:16px;text-align:center;background:white;border:1px solid #e5e7eb;">
                            <div style="font-size:32px;font-weight:bold;color:#dc2626;">{len(lost_leads)}</div>
                            <div style="color:#6b7280;">Leads Perdidos</div>
                        </td>
                    </tr>
                    <tr>
                        <td colspan="2" style="padding:16px;text-align:center;background:white;border:1px solid #e5e7eb;">
                            <div style="font-size:24px;font-weight:bold;color:#16a34a;">${total_revenue:,.2f}</div>
                            <div style="color:#6b7280;">Ingresos por Ventas</div>
                        </td>
                        <td colspan="2" style="padding:16px;text-align:center;background:white;border:1px solid #e5e7eb;">
                            <div style="font-size:24px;font-weight:bold;color:#d97706;">${total_commission:,.2f}</div>
                            <div style="color:#6b7280;">Comisiones Generadas</div>
                        </td>
                    </tr>
                </table>

                <h2 style="color:#1a56db;border-bottom:2px solid #1a56db;padding-bottom:8px;">Top 3 Asesores</h2>
                <table style="width:100%;border-collapse:collapse;background:white;margin-bottom:24px;">
                    <thead><tr style="background:#1a56db;color:white;">
                        <th style="padding:10px;text-align:left;">Asesor</th>
                        <th style="padding:10px;text-align:center;">Ventas</th>
                    </tr></thead>
                    <tbody>{advisors_html}</tbody>
                </table>

                <h2 style="color:#1a56db;border-bottom:2px solid #1a56db;padding-bottom:8px;">Propiedades Vendidas</h2>
                <table style="width:100%;border-collapse:collapse;background:white;margin-bottom:24px;">
                    <thead><tr style="background:#1a56db;color:white;">
                        <th style="padding:10px;text-align:left;">Propiedad</th>
                        <th style="padding:10px;">Ciudad</th>
                        <th style="padding:10px;">Precio</th>
                        <th style="padding:10px;">Comisión</th>
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
            ('groups_id', 'in', [self.env.ref('base.group_system').id]),
            ('email', '!=', False),
        ])
        if not admins:
            admins = self.env['res.users'].search([('email', '!=', False)], limit=3)

        for admin in admins:
            self.env['mail.mail'].sudo().create({
                'subject': f'📊 Reporte Mensual Inmobiliario — {month_name}',
                'email_to': admin.email,
                'body_html': html_body,
                'auto_delete': True,
            }).send()

        import logging
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
                    <div style="background:#eff6ff;padding:12px 20px;border-radius:10px;text-align:center;flex:1;margin-right:8px;">
                        <div style="font-size:28px;font-weight:700;color:#1d4ed8;">{rec.funnel_conversion_pct}%</div>
                        <div style="font-size:12px;color:#6b7280;">Tasa de Conversión</div>
                    </div>
                    <div style="background:#f0fdf4;padding:12px 20px;border-radius:10px;text-align:center;flex:1;margin-left:8px;">
                        <div style="font-size:28px;font-weight:700;color:#16a34a;">{won}</div>
                        <div style="font-size:12px;color:#6b7280;">Cerrados</div>
                    </div>
                </div>
                {bars}
            </div>'''

    # ──────────────────────────────────────────────────────────────────
    # NIVEL 2: Ocupación de Arriendos
    # ──────────────────────────────────────────────────────────────────
    def _compute_occupancy(self):
        for rec in self:
            Contract = self.env['estate.contract'].sudo()
            Property = self.env['estate.property'].sudo()
            today = fields.Date.today()

            # Properties with rental contracts (active or expired)
            rental_contracts = Contract.search([('contract_type', '=', 'rent')])
            rental_prop_ids = rental_contracts.mapped('property_id.id')
            # Also include properties with state=rented
            rented_props = Property.search([('state', '=', 'rented')])
            all_rental_ids = list(set(rental_prop_ids + rented_props.ids))

            rec.total_rental_properties = len(all_rental_ids)
            rec.occupied_count = Property.search_count([('id', 'in', all_rental_ids), ('state', '=', 'rented')])
            rec.vacant_count = rec.total_rental_properties - rec.occupied_count
            rec.occupancy_rate = round(rec.occupied_count / rec.total_rental_properties * 100, 1) if rec.total_rental_properties else 0

            rows = ''
            if all_rental_ids:
                props = Property.browse(all_rental_ids)
                for p in props[:15]:
                    active_contract = Contract.search([
                        ('property_id', '=', p.id),
                        ('contract_type', '=', 'rent'),
                        ('state', '=', 'active'),
                    ], limit=1)
                    status_color = '#16a34a' if p.state == 'rented' else '#dc2626'
                    status_text = 'Ocupada' if p.state == 'rented' else 'Vacante'
                    tenant = active_contract.partner_id.name if active_contract else '-'
                    end_date = str(active_contract.date_end) if active_contract and active_contract.date_end else '-'
                    amount = f"${active_contract.amount:,.0f}" if active_contract else '-'
                    rows += f'''<tr>
                        <td style="padding:8px;border-bottom:1px solid #f1f5f9;">{p.title}</td>
                        <td style="padding:8px;border-bottom:1px solid #f1f5f9;">{p.city or '-'}</td>
                        <td style="padding:8px;border-bottom:1px solid #f1f5f9;text-align:center;">
                            <span style="background:{status_color};color:white;padding:2px 10px;border-radius:12px;font-size:12px;">{status_text}</span>
                        </td>
                        <td style="padding:8px;border-bottom:1px solid #f1f5f9;">{tenant}</td>
                        <td style="padding:8px;border-bottom:1px solid #f1f5f9;text-align:right;">{amount}</td>
                        <td style="padding:8px;border-bottom:1px solid #f1f5f9;text-align:center;">{end_date}</td>
                    </tr>'''

            if not rows:
                rows = '<tr><td colspan="6" style="padding:20px;text-align:center;color:#9ca3af;">Sin propiedades en arriendo</td></tr>'

            rec.occupancy_html = f'''
            <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
                <div style="display:flex;gap:12px;margin-bottom:16px;">
                    <div style="flex:1;background:#eff6ff;padding:14px;border-radius:10px;text-align:center;">
                        <div style="font-size:26px;font-weight:700;color:#1d4ed8;">{rec.total_rental_properties}</div>
                        <div style="font-size:11px;color:#6b7280;">Total Arriendos</div>
                    </div>
                    <div style="flex:1;background:#f0fdf4;padding:14px;border-radius:10px;text-align:center;">
                        <div style="font-size:26px;font-weight:700;color:#16a34a;">{rec.occupied_count}</div>
                        <div style="font-size:11px;color:#6b7280;">Ocupadas</div>
                    </div>
                    <div style="flex:1;background:#fef2f2;padding:14px;border-radius:10px;text-align:center;">
                        <div style="font-size:26px;font-weight:700;color:#dc2626;">{rec.vacant_count}</div>
                        <div style="font-size:11px;color:#6b7280;">Vacantes</div>
                    </div>
                    <div style="flex:1;background:#fefce8;padding:14px;border-radius:10px;text-align:center;">
                        <div style="font-size:26px;font-weight:700;color:#d97706;">{rec.occupancy_rate}%</div>
                        <div style="font-size:11px;color:#6b7280;">Tasa Ocupación</div>
                    </div>
                </div>
                <table style="width:100%;border-collapse:collapse;background:white;border-radius:10px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.06);">
                    <thead><tr style="background:#1e40af;color:white;">
                        <th style="padding:10px;text-align:left;">Propiedad</th>
                        <th style="padding:10px;">Ciudad</th>
                        <th style="padding:10px;text-align:center;">Estado</th>
                        <th style="padding:10px;">Inquilino</th>
                        <th style="padding:10px;text-align:right;">Renta</th>
                        <th style="padding:10px;text-align:center;">Vence</th>
                    </tr></thead>
                    <tbody>{rows}</tbody>
                </table>
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
                    <div style="flex:1;background:#fef2f2;padding:14px;border-radius:10px;text-align:center;">
                        <div style="font-size:26px;font-weight:700;color:#dc2626;">{over}</div>
                        <div style="font-size:11px;color:#6b7280;">Sobrevaluadas (&gt;10%)</div>
                    </div>
                    <div style="flex:1;background:#eff6ff;padding:14px;border-radius:10px;text-align:center;">
                        <div style="font-size:26px;font-weight:700;color:#2563eb;">{fair}</div>
                        <div style="font-size:11px;color:#6b7280;">Precio Justo</div>
                    </div>
                    <div style="flex:1;background:#f0fdf4;padding:14px;border-radius:10px;text-align:center;">
                        <div style="font-size:26px;font-weight:700;color:#16a34a;">{under}</div>
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
    def _compute_charts(self):
        for rec in self:
            # Sales by month (last 6 months) — CSS bar chart
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
            for r in sales_data:
                h = max(int(r['total'] / max_sales * 120), 8)
                bars += f'''
                <div style="display:flex;flex-direction:column;align-items:center;flex:1;">
                    <div style="font-size:12px;font-weight:700;color:#1d4ed8;margin-bottom:4px;">{r['total']}</div>
                    <div style="width:32px;height:{h}px;background:linear-gradient(180deg,#3b82f6,#1d4ed8);border-radius:6px 6px 0 0;"></div>
                    <div style="font-size:11px;color:#6b7280;margin-top:4px;">{r['mes']}</div>
                </div>'''
            if not bars:
                bars = '<div style="padding:20px;text-align:center;color:#9ca3af;">Sin ventas en los últimos 6 meses</div>'

            rec.sales_chart_html = f'''
            <div style="font-family:-apple-system,sans-serif;background:white;border-radius:12px;padding:16px;box-shadow:0 1px 4px rgba(0,0,0,.06);">
                <div style="font-weight:600;font-size:14px;margin-bottom:12px;color:#374151;">Ventas (Últimos 6 meses)</div>
                <div style="display:flex;align-items:flex-end;justify-content:space-around;min-height:160px;padding-top:8px;">
                    {bars}
                </div>
            </div>'''

            # Leads by source — horizontal bars
            self.env.cr.execute("""
                SELECT COALESCE(lead_source, 'other') as source,
                       COUNT(*) as total
                FROM crm_lead
                WHERE create_date >= (CURRENT_DATE - INTERVAL '3 months')
                GROUP BY lead_source
                ORDER BY total DESC
                LIMIT 6
            """)
            lead_data = self.env.cr.dictfetchall()
            max_leads = max((r['total'] for r in lead_data), default=1) or 1
            source_labels = {
                'website': 'Web', 'wordpress': 'WordPress', 'whatsapp': 'WhatsApp',
                'instagram': 'Instagram', 'facebook': 'Facebook', 'google': 'Google',
                'referral': 'Referido', 'phone': 'Teléfono', 'walk_in': 'Visita',
                'portal': 'Portal', 'ai_agent': 'Agente IA', 'other': 'Otro',
            }
            colors = ['#3b82f6', '#8b5cf6', '#f59e0b', '#16a34a', '#ec4899', '#6366f1']
            hbars = ''
            for i, r in enumerate(lead_data):
                w = max(int(r['total'] / max_leads * 100), 5)
                color = colors[i % len(colors)]
                label = source_labels.get(r['source'], r['source'])
                hbars += f'''
                <div style="margin-bottom:6px;">
                    <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:2px;">
                        <span style="color:#374151;">{label}</span>
                        <span style="font-weight:700;color:{color};">{r['total']}</span>
                    </div>
                    <div style="background:#f1f5f9;border-radius:4px;height:16px;overflow:hidden;">
                        <div style="width:{w}%;height:100%;background:{color};border-radius:4px;"></div>
                    </div>
                </div>'''
            if not hbars:
                hbars = '<div style="padding:20px;text-align:center;color:#9ca3af;">Sin leads recientes</div>'

            rec.leads_chart_html = f'''
            <div style="font-family:-apple-system,sans-serif;background:white;border-radius:12px;padding:16px;box-shadow:0 1px 4px rgba(0,0,0,.06);">
                <div style="font-weight:600;font-size:14px;margin-bottom:12px;color:#374151;">Leads por Fuente (3 meses)</div>
                {hbars}
            </div>'''

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
