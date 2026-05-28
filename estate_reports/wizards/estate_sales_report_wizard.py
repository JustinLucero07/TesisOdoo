"""Wizard de Reporte de Promedio de Ventas.

Genera KPIs agregados sobre las propiedades vendidas en un período,
con comparación contra el período anterior y filtros por ciudad, tipo y asesor.
Exporta a PDF (QWeb) y Excel (xlsxwriter).
"""
import io
import json
import statistics
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api
from odoo.exceptions import UserError


PERIOD_SELECTION = [
    ('last_30',  'Últimos 30 días'),
    ('last_90',  'Últimos 90 días'),
    ('quarter',  'Trimestre actual'),
    ('year',     'Año actual'),
    ('custom',   'Personalizado'),
]

OPERATION_SELECTION = [
    ('sale',  'Ventas'),
]


class EstateSalesReportWizard(models.TransientModel):
    _name = 'estate.sales.report.wizard'
    _description = 'Wizard de Reporte de Promedio de Ventas'

    # ── Filtros ──────────────────────────────────────────────────────────────
    period = fields.Selection(
        PERIOD_SELECTION, string='Período', default='quarter', required=True)
    date_from = fields.Date(string='Desde')
    date_to = fields.Date(string='Hasta')
    operation_type = fields.Selection(
        OPERATION_SELECTION, string='Operación', default='sale', required=True)
    property_type_ids = fields.Many2many(
        'estate.property.type', string='Tipos de Propiedad',
        help='Vacío = todos los tipos.')
    city = fields.Char(string='Ciudad', help='Vacío = todas las ciudades.')
    user_ids = fields.Many2many(
        'res.users', string='Asesores',
        help='Vacío = todos los asesores.')

    # ── Resultados (computed para preview en el wizard) ──────────────────────
    has_data = fields.Boolean(compute='_compute_kpis', store=False)
    kpi_avg_price = fields.Float(string='Precio promedio', compute='_compute_kpis')
    kpi_avg_listed = fields.Float(string='Precio promedio listado', compute='_compute_kpis')
    kpi_pct_vs_listed = fields.Float(string='% logrado vs listado', compute='_compute_kpis')
    kpi_avg_days = fields.Float(string='Días promedio en mercado', compute='_compute_kpis')
    kpi_median_price = fields.Float(string='Mediana', compute='_compute_kpis')
    kpi_min_price = fields.Float(string='Mínimo', compute='_compute_kpis')
    kpi_max_price = fields.Float(string='Máximo', compute='_compute_kpis')
    kpi_close_rate = fields.Float(string='Tasa de cierre (%)', compute='_compute_kpis')
    kpi_count = fields.Integer(string='Operaciones', compute='_compute_kpis')

    # ── Comparativa con período anterior ─────────────────────────────────────
    prev_avg_price = fields.Float(string='Promedio anterior', compute='_compute_kpis')
    pct_change_avg = fields.Float(string='Variación %', compute='_compute_kpis')
    prev_avg_days = fields.Float(string='Días anteriores', compute='_compute_kpis')
    pct_change_days = fields.Float(string='Cambio en días', compute='_compute_kpis')

    # ── JSON con datos detallados (para gráficos del template) ───────────────
    chart_data = fields.Char(compute='_compute_kpis')

    # ── Gráficos inline SVG ───────────────────────────────────────────────────
    inline_chart_html = fields.Html(
        string='Gráficos de Tendencia',
        compute='_compute_inline_chart',
        sanitize=False,
    )

    # ────────────────────────────────────────────────────────────────────────
    # Compute principal
    # ────────────────────────────────────────────────────────────────────────
    @api.depends('period', 'date_from', 'date_to', 'operation_type',
                 'property_type_ids', 'city', 'user_ids')
    def _compute_kpis(self):
        for wiz in self:
            d_from, d_to = wiz._get_period_range()
            prev_from, prev_to = wiz._get_previous_period_range(d_from, d_to)

            # Datos del período actual
            sold = wiz._search_sold_properties(d_from, d_to)
            available_in_period = wiz._search_available_count(d_from, d_to)

            wiz.has_data = bool(sold)
            wiz.kpi_count = len(sold)

            if not sold:
                wiz.kpi_avg_price = 0.0
                wiz.kpi_avg_listed = 0.0
                wiz.kpi_pct_vs_listed = 0.0
                wiz.kpi_avg_days = 0.0
                wiz.kpi_median_price = 0.0
                wiz.kpi_min_price = 0.0
                wiz.kpi_max_price = 0.0
                wiz.kpi_close_rate = 0.0
                wiz.prev_avg_price = 0.0
                wiz.pct_change_avg = 0.0
                wiz.prev_avg_days = 0.0
                wiz.pct_change_days = 0.0
                wiz.chart_data = '{}'
                continue

            prices = sold.mapped('price')
            listed_prices = [p.bottom_price * 1.15 if p.bottom_price else p.price for p in sold]
            days = [p.days_on_market for p in sold if p.days_on_market]

            wiz.kpi_avg_price = sum(prices) / len(prices)
            wiz.kpi_avg_listed = sum(listed_prices) / len(listed_prices) if listed_prices else 0.0
            wiz.kpi_pct_vs_listed = (
                (sum(prices) / sum(listed_prices) * 100) if sum(listed_prices) else 0.0
            )
            wiz.kpi_avg_days = sum(days) / len(days) if days else 0.0
            wiz.kpi_median_price = statistics.median(prices)
            wiz.kpi_min_price = min(prices)
            wiz.kpi_max_price = max(prices)
            total_universe = len(sold) + available_in_period
            wiz.kpi_close_rate = (len(sold) / total_universe * 100) if total_universe else 0.0

            # Comparativa con período anterior
            prev_sold = wiz._search_sold_properties(prev_from, prev_to)
            if prev_sold:
                prev_prices = prev_sold.mapped('price')
                prev_days_list = [p.days_on_market for p in prev_sold if p.days_on_market]
                wiz.prev_avg_price = sum(prev_prices) / len(prev_prices)
                wiz.pct_change_avg = (
                    (wiz.kpi_avg_price - wiz.prev_avg_price) / wiz.prev_avg_price * 100
                    if wiz.prev_avg_price else 0.0
                )
                wiz.prev_avg_days = sum(prev_days_list) / len(prev_days_list) if prev_days_list else 0.0
                wiz.pct_change_days = wiz.kpi_avg_days - wiz.prev_avg_days
            else:
                wiz.prev_avg_price = 0.0
                wiz.pct_change_avg = 0.0
                wiz.prev_avg_days = 0.0
                wiz.pct_change_days = 0.0

            wiz.chart_data = json.dumps(wiz._build_chart_data(sold))

    # ────────────────────────────────────────────────────────────────────────
    # Helpers de búsqueda
    # ────────────────────────────────────────────────────────────────────────
    def _get_period_range(self):
        self.ensure_one()
        today = date.today()
        if self.period == 'last_30':
            return today - timedelta(days=30), today
        if self.period == 'last_90':
            return today - timedelta(days=90), today
        if self.period == 'quarter':
            month_start = ((today.month - 1) // 3) * 3 + 1
            return date(today.year, month_start, 1), today
        if self.period == 'year':
            return date(today.year, 1, 1), today
        # custom
        if not self.date_from or not self.date_to:
            raise UserError('En modo personalizado debe establecer "Desde" y "Hasta".')
        if self.date_to < self.date_from:
            raise UserError('La fecha "Hasta" no puede ser anterior a "Desde".')
        return self.date_from, self.date_to

    @staticmethod
    def _get_previous_period_range(d_from, d_to):
        delta = (d_to - d_from)
        prev_to = d_from - timedelta(days=1)
        prev_from = prev_to - delta
        return prev_from, prev_to

    def _build_target_states(self):
        return ['sold']

    def _search_sold_properties(self, d_from, d_to):
        """Busca propiedades vendidas dentro del período.
        Usa contract_end_date como proxy del cierre — aproximación pragmática
        sin necesidad de una tabla de auditoría dedicada."""
        Property = self.env['estate.property'].sudo()
        domain = [
            ('state', 'in', self._build_target_states()),
            ('write_date', '>=', d_from),
            ('write_date', '<=', d_to),
            ('price', '>', 0),
        ]
        if self.property_type_ids:
            domain.append(('property_type_id', 'in', self.property_type_ids.ids))
        if self.city:
            domain.append(('city', 'ilike', self.city))
        if self.user_ids:
            domain.append(('user_id', 'in', self.user_ids.ids))
        return Property.search(domain)

    def _search_available_count(self, d_from, d_to):
        """Cuenta propiedades disponibles que estuvieron en el mercado durante el período
        (usado para calcular tasa de cierre)."""
        Property = self.env['estate.property'].sudo()
        domain = [
            ('state', '=', 'available'),
            ('create_date', '<=', d_to),
        ]
        if self.property_type_ids:
            domain.append(('property_type_id', 'in', self.property_type_ids.ids))
        if self.city:
            domain.append(('city', 'ilike', self.city))
        if self.user_ids:
            domain.append(('user_id', 'in', self.user_ids.ids))
        return Property.search_count(domain)

    def _build_chart_data(self, sold):
        """Construye datos agregados para los gráficos del template."""
        # Top 5 ciudades por volumen
        cities = {}
        for p in sold:
            c = p.city or 'Sin ciudad'
            cities[c] = cities.get(c, 0) + p.price
        top_cities = sorted(cities.items(), key=lambda kv: kv[1], reverse=True)[:5]

        # Distribución por tipo
        types = {}
        for p in sold:
            t = p.property_type_id.name if p.property_type_id else 'Sin tipo'
            types[t] = types.get(t, 0) + 1

        # Ranking de asesores por monto
        users = {}
        for p in sold:
            u = p.user_id.name if p.user_id else 'Sin asignar'
            users[u] = users.get(u, 0) + p.price
        top_users = sorted(users.items(), key=lambda kv: kv[1], reverse=True)[:10]

        return {
            'top_cities': top_cities,
            'types': list(types.items()),
            'top_users': top_users,
            'total_volume': sum(sold.mapped('price')),
        }

    # ────────────────────────────────────────────────────────────────────────
    # Gráficos inline
    # ────────────────────────────────────────────────────────────────────────
    @api.depends('period', 'date_from', 'date_to', 'operation_type',
                 'property_type_ids', 'city', 'user_ids')
    def _compute_inline_chart(self):
        from collections import defaultdict
        from datetime import datetime as dt
        for wiz in self:
            try:
                d_from, d_to = wiz._get_period_range()
            except Exception:
                wiz.inline_chart_html = ''
                continue

            domain = [
                ('state', '=', 'sold'),
                ('date_sold', '!=', False),
                ('date_sold', '>=', d_from),
                ('date_sold', '<=', d_to),
                ('price', '>', 0),
            ]
            if wiz.property_type_ids:
                domain.append(('property_type_id', 'in', wiz.property_type_ids.ids))
            if wiz.city:
                domain.append(('city', 'ilike', wiz.city))
            if wiz.user_ids:
                domain.append(('user_id', 'in', wiz.user_ids.ids))

            sold = wiz.env['estate.property'].sudo().search(domain)
            if not sold:
                wiz.inline_chart_html = ''
                continue

            by_month = defaultdict(list)
            for p in sold:
                key = p.date_sold.strftime('%Y-%m')
                by_month[key].append(p.price)

            monthly = []
            for key in sorted(by_month.keys()):
                prices = by_month[key]
                monthly.append({
                    'key': key,
                    'label': dt.strptime(key, '%Y-%m').strftime('%b \'%y'),
                    'count': len(prices),
                    'avg_price': round(sum(prices) / len(prices)),
                    'total': round(sum(prices)),
                })

            price_svg = wiz._svg_line(monthly, 'avg_price', 'Precio Promedio de Venta', '#1e40af')
            count_svg = wiz._svg_bars(monthly, 'count', 'Ventas por Mes', '#1e40af')

            wiz.inline_chart_html = f'''
<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
    <div style="display:flex;gap:12px;flex-wrap:wrap;">
        <div style="flex:1;min-width:260px;background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:16px;">
            {price_svg}
        </div>
        <div style="flex:0 0 220px;background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:16px;">
            {count_svg}
        </div>
    </div>
</div>'''

    def _svg_line(self, monthly, field, title, color='#1e40af', w=520, h=180):
        PAD_L, PAD_R, PAD_T, PAD_B = 58, 14, 22, 32
        iw = w - PAD_L - PAD_R
        ih = h - PAD_T - PAD_B
        vals = [d[field] for d in monthly]
        if not vals:
            return ''
        max_v = max(vals) * 1.1 or 1
        min_v = min(vals) * 0.88 if min(vals) > 0 else 0
        rng = max_v - min_v or 1
        n = len(monthly)
        step = iw / (n - 1) if n > 1 else iw

        def px(i): return PAD_L + i * step
        def py(v): return PAD_T + ih - (v - min_v) / rng * ih

        grid = ''
        for level in [0, 0.25, 0.5, 0.75, 1.0]:
            v = min_v + rng * level
            y = py(v)
            grid += f'<line x1="{PAD_L}" y1="{y:.1f}" x2="{PAD_L+iw}" y2="{y:.1f}" stroke="#f3f4f6" stroke-width="1"/>'
            lbl = f'${v/1000:.0f}k' if v >= 1000 else f'${v:.0f}'
            grid += f'<text x="{PAD_L-5}" y="{y:.1f}" text-anchor="end" dominant-baseline="middle" font-size="8" fill="#9ca3af">{lbl}</text>'

        pts = ' '.join(f'{px(i):.1f},{py(d[field]):.1f}' for i, d in enumerate(monthly))
        area = f'{PAD_L:.1f},{PAD_T+ih:.1f} {pts} {px(n-1):.1f},{PAD_T+ih:.1f}'
        uid = abs(hash(title)) % 9999

        dots = ''
        xlbls = ''
        for i, d in enumerate(monthly):
            x, y = px(i), py(d[field])
            dots += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{color}" stroke="white" stroke-width="1.5"/>'
            if n <= 8 or i % max(1, n // 8) == 0:
                xlbls += f'<text x="{x:.1f}" y="{PAD_T+ih+16}" text-anchor="middle" font-size="7.5" fill="#9ca3af">{d["label"]}</text>'

        return f'''
<text x="{PAD_L}" y="12" font-size="9" font-weight="700" fill="#6b7280">{title.upper()}</text>
<svg viewBox="0 0 {w} {h}" style="width:100%;display:block;margin-top:4px;">
  <defs><linearGradient id="ag{uid}" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="{color}" stop-opacity="0.18"/>
    <stop offset="100%" stop-color="{color}" stop-opacity="0.02"/>
  </linearGradient></defs>
  {grid}
  <polygon points="{area}" fill="url(#ag{uid})"/>
  <polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>
  {dots}
  {xlbls}
</svg>'''

    def _svg_bars(self, monthly, field, title, color='#1e40af', w=200, h=180):
        PAD_L, PAD_R, PAD_T, PAD_B = 28, 10, 22, 32
        iw = w - PAD_L - PAD_R
        ih = h - PAD_T - PAD_B
        vals = [d[field] for d in monthly]
        if not vals:
            return ''
        max_v = max(vals) * 1.15 or 1
        n = len(monthly)
        gap = 4
        bar_w = max((iw - gap * (n - 1)) / n, 4)
        step = bar_w + gap

        bars = ''
        for i, d in enumerate(monthly):
            v = d[field]
            x = PAD_L + i * step
            bh = v / max_v * ih
            y = PAD_T + ih - bh
            bars += f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" fill="{color}" rx="2"/>'
            if v > 0:
                bars += f'<text x="{x+bar_w/2:.1f}" y="{y-3:.1f}" text-anchor="middle" font-size="8" fill="{color}" font-weight="600">{v}</text>'
            if n <= 6 or i % max(1, n // 5) == 0:
                bars += f'<text x="{x+bar_w/2:.1f}" y="{PAD_T+ih+14}" text-anchor="middle" font-size="7" fill="#9ca3af">{d["label"].split()[0]}</text>'

        return f'''
<text x="{PAD_L}" y="12" font-size="9" font-weight="700" fill="#6b7280">{title.upper()}</text>
<svg viewBox="0 0 {w} {h}" style="width:100%;display:block;margin-top:4px;">
  <line x1="{PAD_L}" y1="{PAD_T}" x2="{PAD_L}" y2="{PAD_T+ih}" stroke="#e5e7eb" stroke-width="1"/>
  <line x1="{PAD_L}" y1="{PAD_T+ih}" x2="{PAD_L+iw}" y2="{PAD_T+ih}" stroke="#e5e7eb" stroke-width="1"/>
  {bars}
</svg>'''

    # ────────────────────────────────────────────────────────────────────────
    # Acciones de exportación
    # ────────────────────────────────────────────────────────────────────────
    def action_open_graph(self):
        self.ensure_one()
        return self.env.ref('estate_reports.action_sales_avg_month').read()[0]

    def action_generate_pdf(self):
        self.ensure_one()
        return self.env.ref('estate_reports.action_report_avg_sales').report_action(self)

    def action_generate_xlsx(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/estate_reports/sales_report_xlsx/{self.id}',
            'target': 'self',
        }

    def action_open_detail(self):
        """Abre la lista de propiedades incluidas en el reporte."""
        self.ensure_one()
        d_from, d_to = self._get_period_range()
        sold = self._search_sold_properties(d_from, d_to)
        return {
            'type': 'ir.actions.act_window',
            'name': f'Operaciones del período ({len(sold)})',
            'res_model': 'estate.property',
            'view_mode': 'list,form',
            'domain': [('id', 'in', sold.ids)],
        }

    # ────────────────────────────────────────────────────────────────────────
    # Generación Excel (xlsxwriter)
    # ────────────────────────────────────────────────────────────────────────
    def generate_xlsx_bytes(self):
        """Genera el contenido binario del Excel del reporte."""
        self.ensure_one()
        try:
            import xlsxwriter
        except ImportError:
            raise UserError(
                'La librería xlsxwriter no está instalada. '
                'Instálela con: pip install xlsxwriter')

        d_from, d_to = self._get_period_range()
        sold = self._search_sold_properties(d_from, d_to)

        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {'in_memory': True})

        # Formatos
        f_title = wb.add_format({'bold': True, 'font_size': 14,
                                 'bg_color': '#1877F2', 'color': 'white',
                                 'align': 'center', 'valign': 'vcenter'})
        f_header = wb.add_format({'bold': True, 'bg_color': '#E4E6EB',
                                  'border': 1, 'align': 'center'})
        f_money = wb.add_format({'num_format': '"$"#,##0.00', 'border': 1})
        f_pct = wb.add_format({'num_format': '0.00"%"', 'border': 1})
        f_int = wb.add_format({'num_format': '#,##0', 'border': 1})
        f_text = wb.add_format({'border': 1})

        # ── Hoja 1: KPIs ──
        ws1 = wb.add_worksheet('KPIs')
        ws1.set_column('A:A', 32)
        ws1.set_column('B:B', 20)
        ws1.set_column('C:C', 20)

        ws1.merge_range('A1:C1', f'Reporte de Promedio de Ventas — {d_from} a {d_to}', f_title)
        ws1.write_row('A3', ['Métrica', 'Período actual', 'Período anterior'], f_header)

        kpis = [
            ('Operaciones',                self.kpi_count,        len(sold), f_int),
            ('Precio promedio',            self.kpi_avg_price,    self.prev_avg_price, f_money),
            ('Precio promedio listado',    self.kpi_avg_listed,   '-', f_money),
            ('% logrado vs listado',       self.kpi_pct_vs_listed, '-', f_pct),
            ('Días promedio en mercado',   self.kpi_avg_days,     self.prev_avg_days, f_int),
            ('Mediana',                    self.kpi_median_price, '-', f_money),
            ('Mínimo',                     self.kpi_min_price,    '-', f_money),
            ('Máximo',                     self.kpi_max_price,    '-', f_money),
            ('Tasa de cierre',             self.kpi_close_rate,   '-', f_pct),
            ('Variación promedio precio',  self.pct_change_avg,   '-', f_pct),
        ]
        for i, (label, current, prev, fmt) in enumerate(kpis, start=4):
            ws1.write(f'A{i}', label, f_text)
            ws1.write(f'B{i}', current, fmt)
            if isinstance(prev, (int, float)):
                ws1.write(f'C{i}', prev, fmt)
            else:
                ws1.write(f'C{i}', prev, f_text)

        # ── Hoja 2: detalle de propiedades ──
        ws2 = wb.add_worksheet('Detalle')
        ws2.set_column('A:A', 14)
        ws2.set_column('B:B', 35)
        ws2.set_column('C:C', 15)
        ws2.set_column('D:D', 18)
        ws2.set_column('E:F', 15)
        ws2.set_column('G:G', 18)
        ws2.set_column('H:H', 12)

        ws2.merge_range('A1:H1', 'Detalle de operaciones', f_title)
        headers = ['Referencia', 'Título', 'Tipo', 'Ciudad', 'Precio', 'Días en mercado', 'Asesor', 'Estado']
        ws2.write_row('A3', headers, f_header)

        for i, p in enumerate(sold, start=4):
            ws2.write(f'A{i}', p.name or '', f_text)
            ws2.write(f'B{i}', p.title or '', f_text)
            ws2.write(f'C{i}', p.property_type_id.name or '', f_text)
            ws2.write(f'D{i}', p.city or '', f_text)
            ws2.write(f'E{i}', p.price, f_money)
            ws2.write(f'F{i}', p.days_on_market or 0, f_int)
            ws2.write(f'G{i}', p.user_id.name or '', f_text)
            ws2.write(f'H{i}', p.state or '', f_text)

        wb.close()
        output.seek(0)
        return output.getvalue()
