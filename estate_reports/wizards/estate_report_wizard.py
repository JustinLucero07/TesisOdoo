import io
import base64
from datetime import timedelta
from odoo import models, fields

try:
    import xlsxwriter
    XLSXWRITER_AVAILABLE = True
except ImportError:
    XLSXWRITER_AVAILABLE = False


class EstateReportWizard(models.TransientModel):
    _name = 'estate.report.wizard'
    _description = 'Wizard de Reportes Inmobiliarios'

    report_type = fields.Selection([
        ('available_properties', ' Propiedades Disponibles'),
        ('active_clients', ' Clientes Activos'),
        ('sales_period', ' Ventas por Período'),
        ('time_to_sell', '⏱️ Tiempo de Venta'),
        ('visits_report', ' Visitas / Citas Realizadas'),
        ('contracts_expiring', ' Contratos por Vencer'),
        ('agent_commissions', ' Desempeño y Comisiones de Asesores'),
        ('geographic_avm', '️ Análisis Geográfico y Mercado (AVM)'),
        ('marketing_roi', ' Retorno de Marketing (Origen Leads)'),
    ], string='Tipo de Reporte', required=True, default='available_properties')

    date_from = fields.Date(string='Desde')
    date_to = fields.Date(string='Hasta')
    export_format = fields.Selection([
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
    ], string='Formato', required=True, default='excel')

    # For Excel download
    excel_file = fields.Binary(string='Archivo Excel', readonly=True)
    excel_filename = fields.Char(string='Nombre Archivo')

    def action_generate_report(self):
        """Generate report based on selected type and format."""
        self.ensure_one()
        if self.export_format == 'pdf':
            return self._generate_pdf()
        else:
            return self._generate_excel()

    def _get_report_data(self):
        """Get data for the selected report type."""
        data = {
            'report_type': self.report_type,
            'date_from': self.date_from,
            'date_to': self.date_to,
        }

        if self.report_type == 'available_properties':
            records = self.env['estate.property'].search([('state', '=', 'available')])
            data['records'] = records
            data['title'] = 'Propiedades Disponibles'

        elif self.report_type == 'active_clients':
            records = self.env['crm.lead'].search(
                [('type', '=', 'opportunity'), ('probability', '>', 0), ('probability', '<', 100)])
            data['records'] = records
            data['title'] = 'Clientes Activos (Oportunidades)'

        elif self.report_type == 'sales_period':
            domain = [('state', '=', 'sold')]
            if self.date_from:
                domain.append(('date_sold', '>=', self.date_from))
            if self.date_to:
                domain.append(('date_sold', '<=', self.date_to))
            records = self.env['estate.property'].search(domain, order='date_sold desc')
            data['records'] = records
            data['title'] = 'Ventas por Período'

        elif self.report_type == 'time_to_sell':
            domain = [('state', '=', 'sold'), ('date_listed', '!=', False)]
            if self.date_from:
                domain.append(('date_sold', '>=', self.date_from))
            if self.date_to:
                domain.append(('date_sold', '<=', self.date_to))
            records = self.env['estate.property'].search(domain, order='days_on_market desc')
            data['records'] = records
            data['title'] = 'Tiempo de Venta de Propiedades'

        elif self.report_type == 'visits_report':
            # Use calendar.event for visits
            domain = [('property_id', '!=', False)]
            if self.date_from:
                domain.append(('start', '>=', self.date_from))
            if self.date_to:
                # Add 1 day to date_to to include all events on that day
                domain.append(('start', '<=', fields.Date.to_date(self.date_to) + timedelta(days=1)))
            records = self.env['calendar.event'].search(domain, order='start desc')
            data['records'] = records
            data['title'] = 'Visitas y Citas Realizadas'

        elif self.report_type == 'contracts_expiring':
            today = fields.Date.today()
            limit_date = today + timedelta(days=60)
            records = self.env['estate.property'].search([
                ('contract_end_date', '!=', False),
                ('contract_end_date', '<=', limit_date),
                ('state', 'in', ('available', 'rented', 'reserved')),
            ], order='contract_end_date')
            data['records'] = records
            data['title'] = 'Contratos por Vencer (próximos 60 días)'

        elif self.report_type == 'agent_commissions':
            domain = [('state', '=', 'sold'), ('user_id', '!=', False)]
            if self.date_from:
                domain.append(('date_sold', '>=', self.date_from))
            if self.date_to:
                domain.append(('date_sold', '<=', self.date_to))
            records = self.env['estate.property'].search(domain, order='user_id, date_sold desc')
            data['records'] = records
            data['title'] = 'Desempeño y Comisiones de Asesores'

        elif self.report_type == 'geographic_avm':
            domain = [('state', '=', 'sold'), ('city', '!=', False)]
            if self.date_from:
                domain.append(('date_sold', '>=', self.date_from))
            if self.date_to:
                domain.append(('date_sold', '<=', self.date_to))
            records = self.env['estate.property'].search(domain, order='city')
            data['records'] = records
            data['title'] = 'Análisis Geográfico y Mercado (AVM)'

        elif self.report_type == 'marketing_roi':
            domain = [('type', '=', 'opportunity')]
            if self.date_from:
                domain.append(('create_date', '>=', self.date_from))
            if self.date_to:
                domain.append(('create_date', '<=', fields.Date.to_date(self.date_to) + timedelta(days=1)))
            records = self.env['crm.lead'].search(domain, order='source_id')
            data['records'] = records
            data['title'] = 'Retorno de Marketing (Orígenes)'

        return data

    def _generate_pdf(self):
        """Generate PDF report using QWeb."""
        data = self._get_report_data()
        report_data = {
            'title': data['title'],
            'date_from': self.date_from,
            'date_to': self.date_to,
            'report_type': self.report_type,
            'records': data['records'],
        }
        return self.env.ref(
            'estate_reports.action_report_estate_general'
        ).report_action(self, data={'form': report_data})

    def _generate_excel(self):
        """Generate Excel report with professional formatting."""
        if not XLSXWRITER_AVAILABLE:
            raise Exception('xlsxwriter no está instalado. Ejecute: pip install xlsxwriter')

        data = self._get_report_data()
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)

        # Common formats
        title_fmt = workbook.add_format({
            'bold': True, 'font_size': 16, 'align': 'center',
            'bg_color': '#1B4F72', 'font_color': 'white', 'border': 1,
        })
        subtitle_fmt = workbook.add_format({
            'bold': True, 'font_size': 11, 'align': 'center',
            'bg_color': '#2E86C1', 'font_color': 'white',
        })
        header_fmt = workbook.add_format({
            'bold': True, 'bg_color': '#D4E6F1', 'border': 1,
            'align': 'center', 'text_wrap': True,
        })
        cell_fmt = workbook.add_format({'border': 1, 'text_wrap': True})
        money_fmt = workbook.add_format({'border': 1, 'num_format': '$#,##0.00'})
        date_fmt = workbook.add_format({'border': 1, 'num_format': 'dd/mm/yyyy'})
        number_fmt = workbook.add_format({'border': 1, 'align': 'center'})
        total_fmt = workbook.add_format({
            'bold': True, 'bg_color': '#1B4F72', 'font_color': 'white',
            'border': 1, 'num_format': '$#,##0.00',
        })
        total_label_fmt = workbook.add_format({
            'bold': True, 'bg_color': '#1B4F72', 'font_color': 'white',
            'border': 1, 'align': 'right',
        })
        green_fmt = workbook.add_format({
            'border': 1, 'bg_color': '#D5F5E3', 'align': 'center',
        })
        red_fmt = workbook.add_format({
            'border': 1, 'bg_color': '#FADBD8', 'align': 'center',
        })
        yellow_fmt = workbook.add_format({
            'border': 1, 'bg_color': '#FEF9E7', 'align': 'center',
        })

        sheet_name = data['title'][:31]
        ws = workbook.add_worksheet(sheet_name)

        # --- Title ---
        col_count = 7
        ws.merge_range(0, 0, 0, col_count - 1, data['title'], title_fmt)
        date_info = ''
        if self.date_from:
            date_info += f"Desde: {self.date_from.strftime('%d/%m/%Y')}"
        if self.date_to:
            date_info += f"  Hasta: {self.date_to.strftime('%d/%m/%Y')}"
        if date_info:
            ws.merge_range(1, 0, 1, col_count - 1, date_info, subtitle_fmt)

        row = 3

        # ==============================
        # PROPIEDADES DISPONIBLES
        # ==============================
        if self.report_type == 'available_properties':
            headers = ['Ref.', 'Título', 'Tipo', 'Ciudad', 'Precio', 'Área (m²)', 'Habitaciones']
            col_count = len(headers)
            for col, h in enumerate(headers):
                ws.write(row, col, h, header_fmt)
            row += 1
            total_price = 0
            for rec in data['records']:
                ws.write(row, 0, rec.name or '', cell_fmt)
                ws.write(row, 1, rec.title or '', cell_fmt)
                ws.write(row, 2, rec.property_type_id.name or '', cell_fmt)
                ws.write(row, 3, rec.city or '', cell_fmt)
                ws.write(row, 4, rec.price or 0, money_fmt)
                ws.write(row, 5, rec.area or 0, number_fmt)
                ws.write(row, 6, rec.bedrooms or 0, number_fmt)
                total_price += rec.price or 0
                row += 1
            ws.write(row, 3, 'TOTAL:', total_label_fmt)
            ws.write(row, 4, total_price, total_fmt)
            row += 2
            ws.write(row, 0, f"Total: {len(data['records'])} propiedades disponibles", cell_fmt)

        # ==============================
        # CLIENTES ACTIVOS (Oportunidades)
        # ==============================
        elif self.report_type == 'active_clients':
            headers = ['Iniciativa', 'Contacto', 'Telef.', 'Email', 'Ingreso Esperado', 'Etapa', 'Asesor']
            col_count = len(headers)
            for col, h in enumerate(headers):
                ws.write(row, col, h, header_fmt)
            row += 1
            for rec in data['records']:
                ws.write(row, 0, rec.name or '', cell_fmt)
                ws.write(row, 1, rec.partner_name or rec.contact_name or '', cell_fmt)
                ws.write(row, 2, rec.phone or rec.mobile or '', cell_fmt)
                ws.write(row, 3, rec.email_from or '', cell_fmt)
                ws.write(row, 4, rec.expected_revenue or 0, money_fmt)
                ws.write(row, 5, rec.stage_id.name or 'Nuevo', cell_fmt)
                ws.write(row, 6, rec.user_id.name or '', cell_fmt)
                row += 1
            row += 1
            ws.write(row, 0, f"Total: {len(data['records'])} oportunidades activas", cell_fmt)

        # ==============================
        # VENTAS POR PERÍODO
        # ==============================
        elif self.report_type == 'sales_period':
            headers = ['Ref.', 'Título', 'Tipo', 'Ciudad', 'Precio Venta', 'Fecha Venta', 'Asesor', 'Quién Vendió', 'Días en Mercado']
            col_count = len(headers)
            ws.merge_range(0, 0, 0, col_count - 1, data['title'], title_fmt)
            for col, h in enumerate(headers):
                ws.write(row, col, h, header_fmt)
            row += 1
            total_sales = 0
            for rec in data['records']:
                ws.write(row, 0, rec.name or '', cell_fmt)
                ws.write(row, 1, rec.title or '', cell_fmt)
                ws.write(row, 2, rec.property_type_id.name or '', cell_fmt)
                ws.write(row, 3, rec.city or '', cell_fmt)
                ws.write(row, 4, rec.price or 0, money_fmt)
                if rec.date_sold:
                    ws.write_datetime(row, 5, fields.Datetime.to_datetime(rec.date_sold), date_fmt)
                else:
                    ws.write(row, 5, '', cell_fmt)
                ws.write(row, 6, rec.user_id.name or '', cell_fmt)
                sold_label = dict(rec._fields['sold_by'].selection).get(rec.sold_by, '') if rec.sold_by else ''
                ws.write(row, 7, sold_label, cell_fmt)
                ws.write(row, 8, rec.days_on_market or 0, number_fmt)
                total_sales += rec.price or 0
                row += 1
            ws.write(row, 3, 'TOTAL VENTAS:', total_label_fmt)
            ws.write(row, 4, total_sales, total_fmt)
            row += 2
            ws.write(row, 0, f"Total: {len(data['records'])} propiedades vendidas", cell_fmt)

            # --- Chart: Ventas por mes ---
            if len(data['records']) > 0:
                chart_ws = workbook.add_worksheet('Gráfico Ventas')
                chart_ws.write(0, 0, 'Mes', header_fmt)
                chart_ws.write(0, 1, 'Ventas ($)', header_fmt)
                chart_ws.write(0, 2, 'Cantidad', header_fmt)
                monthly = {}
                for rec in data['records']:
                    if rec.date_sold:
                        key = rec.date_sold.strftime('%Y-%m')
                        if key not in monthly:
                            monthly[key] = {'total': 0, 'count': 0}
                        monthly[key]['total'] += rec.price or 0
                        monthly[key]['count'] += 1
                chart_row = 1
                for month in sorted(monthly.keys()):
                    chart_ws.write(chart_row, 0, month, cell_fmt)
                    chart_ws.write(chart_row, 1, monthly[month]['total'], money_fmt)
                    chart_ws.write(chart_row, 2, monthly[month]['count'], number_fmt)
                    chart_row += 1

                if chart_row > 1:
                    chart = workbook.add_chart({'type': 'column'})
                    chart.add_series({
                        'name': 'Ventas ($)',
                        'categories': ['Gráfico Ventas', 1, 0, chart_row - 1, 0],
                        'values': ['Gráfico Ventas', 1, 1, chart_row - 1, 1],
                        'fill': {'color': '#2E86C1'},
                    })
                    chart.set_title({'name': 'Ventas por Mes'})
                    chart.set_x_axis({'name': 'Mes'})
                    chart.set_y_axis({'name': 'Monto ($)', 'num_format': '$#,##0'})
                    chart.set_size({'width': 720, 'height': 400})
                    chart_ws.insert_chart('E1', chart)

        # ==============================
        # TIEMPO DE VENTA
        # ==============================
        elif self.report_type == 'time_to_sell':
            headers = ['Ref.', 'Título', 'Tipo', 'Ciudad', 'Precio', 'Fecha Publicación', 'Fecha Venta', 'Días en Mercado', 'Quién Vendió']
            col_count = len(headers)
            ws.merge_range(0, 0, 0, col_count - 1, data['title'], title_fmt)
            for col, h in enumerate(headers):
                ws.write(row, col, h, header_fmt)
            row += 1
            total_days = 0
            for rec in data['records']:
                ws.write(row, 0, rec.name or '', cell_fmt)
                ws.write(row, 1, rec.title or '', cell_fmt)
                ws.write(row, 2, rec.property_type_id.name or '', cell_fmt)
                ws.write(row, 3, rec.city or '', cell_fmt)
                ws.write(row, 4, rec.price or 0, money_fmt)
                if rec.date_listed:
                    ws.write_datetime(row, 5, fields.Datetime.to_datetime(rec.date_listed), date_fmt)
                else:
                    ws.write(row, 5, '', cell_fmt)
                if rec.date_sold:
                    ws.write_datetime(row, 6, fields.Datetime.to_datetime(rec.date_sold), date_fmt)
                else:
                    ws.write(row, 6, '', cell_fmt)
                days = rec.days_on_market or 0
                # Color code days
                if days <= 30:
                    ws.write(row, 7, days, green_fmt)
                elif days <= 90:
                    ws.write(row, 7, days, yellow_fmt)
                else:
                    ws.write(row, 7, days, red_fmt)
                sold_label = dict(rec._fields['sold_by'].selection).get(rec.sold_by, '') if rec.sold_by else ''
                ws.write(row, 8, sold_label, cell_fmt)
                total_days += days
                row += 1

            avg_days = total_days / len(data['records']) if data['records'] else 0
            row += 1
            ws.write(row, 6, 'PROMEDIO:', total_label_fmt)
            ws.write(row, 7, round(avg_days, 1), workbook.add_format({
                'bold': True, 'bg_color': '#1B4F72', 'font_color': 'white',
                'border': 1, 'align': 'center',
            }))
            row += 2
            ws.write(row, 0, f"Total: {len(data['records'])} propiedades | Promedio: {round(avg_days, 1)} días", cell_fmt)

            # --- Chart: Tiempo por tipo ---
            if len(data['records']) > 0:
                chart_ws = workbook.add_worksheet('Gráfico Tiempo')
                chart_ws.write(0, 0, 'Tipo', header_fmt)
                chart_ws.write(0, 1, 'Promedio Días', header_fmt)
                by_type = {}
                for rec in data['records']:
                    t = rec.property_type_id.name or 'Sin tipo'
                    if t not in by_type:
                        by_type[t] = []
                    by_type[t].append(rec.days_on_market or 0)
                chart_row = 1
                for t_name, days_list in sorted(by_type.items()):
                    chart_ws.write(chart_row, 0, t_name, cell_fmt)
                    chart_ws.write(chart_row, 1, round(sum(days_list) / len(days_list), 1), number_fmt)
                    chart_row += 1

                if chart_row > 1:
                    chart = workbook.add_chart({'type': 'bar'})
                    chart.add_series({
                        'name': 'Promedio Días en Mercado',
                        'categories': ['Gráfico Tiempo', 1, 0, chart_row - 1, 0],
                        'values': ['Gráfico Tiempo', 1, 1, chart_row - 1, 1],
                        'fill': {'color': '#E74C3C'},
                    })
                    chart.set_title({'name': 'Tiempo Promedio de Venta por Tipo'})
                    chart.set_x_axis({'name': 'Tipo de Propiedad'})
                    chart.set_y_axis({'name': 'Días'})
                    chart.set_size({'width': 720, 'height': 400})
                    chart_ws.insert_chart('D1', chart)

        # ==============================
        # VISITAS / CITAS REALIZADAS
        # ==============================
        elif self.report_type == 'visits_report':
            headers = ['Título', 'Tipo', 'Cliente', 'Propiedad', 'Asesor', 'Fecha', 'Resultado', 'Valoración']
            col_count = len(headers)
            ws.merge_range(0, 0, 0, col_count - 1, data['title'], title_fmt)
            for col, h in enumerate(headers):
                ws.write(row, col, h, header_fmt)
            row += 1
            results_count = {}
            for rec in data['records']:
                ws.write(row, 0, rec.name or '', cell_fmt)
                type_label = dict(rec._fields['appointment_type'].selection).get(rec.appointment_type, '')
                ws.write(row, 1, type_label, cell_fmt)
                ws.write(row, 2, rec.partner_id.name if rec.partner_id else '', cell_fmt)
                ws.write(row, 3, rec.property_id.title if rec.property_id else '', cell_fmt)
                ws.write(row, 4, rec.user_id.name or '', cell_fmt)
                if rec.start:
                    ws.write_datetime(row, 5, rec.start, date_fmt)
                else:
                    ws.write(row, 5, '', cell_fmt)
                result_label = dict(rec._fields['visit_result'].selection).get(rec.visit_result, '') if rec.visit_result else ''
                # Color code results
                if rec.visit_result == 'offer_made':
                    ws.write(row, 6, result_label, green_fmt)
                elif rec.visit_result == 'interested':
                    ws.write(row, 6, result_label, workbook.add_format({'border': 1, 'bg_color': '#D6EAF8', 'align': 'center'}))
                elif rec.visit_result == 'not_interested':
                    ws.write(row, 6, result_label, red_fmt)
                else:
                    ws.write(row, 6, result_label, yellow_fmt)
                ws.write(row, 7, rec.visit_rating or '', number_fmt)
                res_key = rec.visit_result or 'sin_resultado'
                results_count[res_key] = results_count.get(res_key, 0) + 1
                row += 1

            row += 1
            ws.write(row, 0, f"Total: {len(data['records'])} citas realizadas", cell_fmt)

            # --- Chart: Resultados ---
            if len(data['records']) > 0:
                chart_ws = workbook.add_worksheet('Gráfico Resultados')
                chart_ws.write(0, 0, 'Resultado', header_fmt)
                chart_ws.write(0, 1, 'Cantidad', header_fmt)
                result_labels = {
                    'interested': 'Interesado', 'not_interested': 'No Interesado',
                    'follow_up': 'Seguimiento', 'offer_made': 'Oferta Realizada',
                    'sin_resultado': 'Sin Resultado',
                }
                chart_row = 1
                for key, count in sorted(results_count.items()):
                    chart_ws.write(chart_row, 0, result_labels.get(key, key), cell_fmt)
                    chart_ws.write(chart_row, 1, count, number_fmt)
                    chart_row += 1

                if chart_row > 1:
                    chart = workbook.add_chart({'type': 'pie'})
                    chart.add_series({
                        'name': 'Resultados',
                        'categories': ['Gráfico Resultados', 1, 0, chart_row - 1, 0],
                        'values': ['Gráfico Resultados', 1, 1, chart_row - 1, 1],
                    })
                    chart.set_title({'name': 'Distribución de Resultados'})
                    chart.set_size({'width': 600, 'height': 400})
                    chart_ws.insert_chart('D1', chart)

        # ==============================
        # CONTRATOS POR VENCER
        # ==============================
        elif self.report_type == 'contracts_expiring':
            today = fields.Date.today()
            headers = ['Ref.', 'Título', 'Tipo', 'Ciudad', 'Propietario', 'Asesor', 'Vencimiento', 'Días Restantes', 'Estado']
            col_count = len(headers)
            ws.merge_range(0, 0, 0, col_count - 1, data['title'], title_fmt)
            for col, h in enumerate(headers):
                ws.write(row, col, h, header_fmt)
            row += 1
            for rec in data['records']:
                ws.write(row, 0, rec.name or '', cell_fmt)
                ws.write(row, 1, rec.title or '', cell_fmt)
                ws.write(row, 2, rec.property_type_id.name or '', cell_fmt)
                ws.write(row, 3, rec.city or '', cell_fmt)
                ws.write(row, 4, rec.owner_id.name if rec.owner_id else '', cell_fmt)
                ws.write(row, 5, rec.user_id.name or '', cell_fmt)
                if rec.contract_end_date:
                    ws.write_datetime(row, 6, fields.Datetime.to_datetime(rec.contract_end_date), date_fmt)
                    days_left = (rec.contract_end_date - today).days
                    if days_left < 0:
                        ws.write(row, 7, days_left, red_fmt)
                        ws.write(row, 8, ' VENCIDO', red_fmt)
                    elif days_left <= 15:
                        ws.write(row, 7, days_left, red_fmt)
                        ws.write(row, 8, '⚠️ Urgente', red_fmt)
                    elif days_left <= 30:
                        ws.write(row, 7, days_left, yellow_fmt)
                        ws.write(row, 8, '⏰ Próximo', yellow_fmt)
                    else:
                        ws.write(row, 7, days_left, green_fmt)
                        ws.write(row, 8, ' OK', green_fmt)
                else:
                    ws.write(row, 6, '', cell_fmt)
                    ws.write(row, 7, '', cell_fmt)
                    ws.write(row, 8, '', cell_fmt)
                row += 1
            row += 1
            ws.write(row, 0, f"Total: {len(data['records'])} contratos por vencer", cell_fmt)

        # ==============================
        # COMISIONES POR ASESOR
        # ==============================
        elif self.report_type == 'agent_commissions':
            headers = ['Asesor', 'Propiedad Vendida', 'Fecha Venta', 'Precio Venta', '% Comisión', 'Monto Generado']
            col_count = len(headers)
            ws.merge_range(0, 0, 0, col_count - 1, data['title'], title_fmt)
            for col, h in enumerate(headers):
                ws.write(row, col, h, header_fmt)
            row += 1
            
            agent_totals = {}
            for rec in data['records']:
                agent_name = rec.user_id.name or 'Sin Asignar'
                ws.write(row, 0, agent_name, cell_fmt)
                ws.write(row, 1, rec.title or '', cell_fmt)
                if rec.date_sold:
                    ws.write_datetime(row, 2, rec.date_sold, date_fmt)
                else:
                    ws.write(row, 2, '', cell_fmt)
                ws.write(row, 3, rec.price, money_fmt)
                ws.write(row, 4, rec.commission_percentage / 100.0, workbook.add_format({'border': 1, 'num_format': '0.0%'}))
                ws.write(row, 5, rec.commission_amount, money_fmt)
                
                agent_totals[agent_name] = agent_totals.get(agent_name, 0) + rec.commission_amount
                row += 1
                
            # Chart Generation
            if len(agent_totals) > 0:
                chart_ws = workbook.add_worksheet('Gráfico Comisiones')
                chart_ws.write(0, 0, 'Asesor', header_fmt)
                chart_ws.write(0, 1, 'Comisión Total Generada', header_fmt)
                chart_row = 1
                for key, val in sorted(agent_totals.items(), key=lambda x: x[1], reverse=True):
                    chart_ws.write(chart_row, 0, key, cell_fmt)
                    chart_ws.write(chart_row, 1, val, money_fmt)
                    chart_row += 1
                    
                if chart_row > 1:
                    chart = workbook.add_chart({'type': 'pie'})
                    chart.add_series({
                        'name': 'Comisiones',
                        'categories': ['Gráfico Comisiones', 1, 0, chart_row - 1, 0],
                        'values': ['Gráfico Comisiones', 1, 1, chart_row - 1, 1],
                    })
                    chart.set_title({'name': 'Distribución de Ingresos Constantes (Asesores)'})
                    chart.set_size({'width': 600, 'height': 400})
                    chart_ws.insert_chart('D1', chart)

        # ==============================
        # ANÁLISIS GEOGRÁFICO Y AVM
        # ==============================
        elif self.report_type == 'geographic_avm':
            headers = ['Ciudad', 'Propiedades Vendidas', 'Precio Promedio de Venta', 'Área Promedio (m²)', 'Precio Promedio x m²', 'Tiempo Promedio (Días)']
            col_count = len(headers)
            ws.merge_range(0, 0, 0, col_count - 1, data['title'], title_fmt)
            for col, h in enumerate(headers):
                ws.write(row, col, h, header_fmt)
            row += 1
            
            city_data = {}
            for rec in data['records']:
                city = (rec.city or 'Desconocida').upper()
                if city not in city_data:
                    city_data[city] = {'count': 0, 'total_price': 0, 'total_area': 0, 'days_on_market': []}
                city_data[city]['count'] += 1
                city_data[city]['total_price'] += rec.price
                city_data[city]['total_area'] += rec.area or 0
                if rec.days_on_market:
                    city_data[city]['days_on_market'].append(rec.days_on_market)
                    
            for city, stats in sorted(city_data.items()):
                ws.write(row, 0, city, cell_fmt)
                ws.write(row, 1, stats['count'], number_fmt)
                avg_price = stats['total_price'] / stats['count'] if stats['count'] > 0 else 0
                ws.write(row, 2, avg_price, money_fmt)
                avg_area = stats['total_area'] / stats['count'] if stats['count'] > 0 else 0
                ws.write(row, 3, avg_area, number_fmt)
                price_m2 = avg_price / avg_area if avg_area > 0 else 0
                ws.write(row, 4, price_m2, money_fmt)
                avg_days = sum(stats['days_on_market']) / len(stats['days_on_market']) if stats['days_on_market'] else 0
                ws.write(row, 5, avg_days, number_fmt)
                row += 1
                
            if len(city_data) > 0:
                chart_ws = workbook.add_worksheet('Gráfico Mercado por Ciudad')
                chart_ws.write(0, 0, 'Ciudad', header_fmt)
                chart_ws.write(0, 1, 'Precio Promedio x m²', header_fmt)
                chart_row = 1
                for city, stats in sorted(city_data.items()):
                    avg_price = stats['total_price'] / stats['count'] if stats['count'] > 0 else 0
                    avg_area = stats['total_area'] / stats['count'] if stats['count'] > 0 else 0
                    price_m2 = avg_price / avg_area if avg_area > 0 else 0
                    chart_ws.write(chart_row, 0, city, cell_fmt)
                    chart_ws.write(chart_row, 1, price_m2, money_fmt)
                    chart_row += 1
                    
                if chart_row > 1:
                    chart = workbook.add_chart({'type': 'column'})
                    chart.add_series({
                        'categories': ['Gráfico Mercado por Ciudad', 1, 0, chart_row - 1, 0],
                        'values': ['Gráfico Mercado por Ciudad', 1, 1, chart_row - 1, 1],
                        'fill': {'color': '#2E86C1'},
                    })
                    chart.set_title({'name': 'Precio Promedio M² por Ciudad'})
                    chart.set_size({'width': 700, 'height': 400})
                    chart_ws.insert_chart('D1', chart)

        # ==============================
        # RETORNO DE MARKETING (ROI)
        # ==============================
        elif self.report_type == 'marketing_roi':
            headers = ['Origen (UTM Source)', 'Total Leads (Oportunidades)', 'Leads Exitosos (Ventas)', 'Tasa de Conversión', 'Ingresos Estimados Generados']
            col_count = len(headers)
            ws.merge_range(0, 0, 0, col_count - 1, data['title'], title_fmt)
            for col, h in enumerate(headers):
                ws.write(row, col, h, header_fmt)
            row += 1
            
            source_data = {}
            for rec in data['records']:
                source = rec.source_id.name if rec.source_id else 'Directo / Orgánico'
                if source not in source_data:
                    source_data[source] = {'total': 0, 'won': 0, 'revenue': 0}
                source_data[source]['total'] += 1
                if rec.stage_id.is_won:
                    source_data[source]['won'] += 1
                    source_data[source]['revenue'] += rec.expected_revenue or 0
                    
            for source, stats in sorted(source_data.items(), key=lambda x: x[1]['total'], reverse=True):
                ws.write(row, 0, source, cell_fmt)
                ws.write(row, 1, stats['total'], number_fmt)
                ws.write(row, 2, stats['won'], number_fmt)
                conversion = stats['won'] / stats['total'] if stats['total'] > 0 else 0
                ws.write(row, 3, conversion, workbook.add_format({'border': 1, 'align': 'center', 'num_format': '0.0%'}))
                ws.write(row, 4, stats['revenue'], money_fmt)
                row += 1

        # --- Auto-size columns ---
        for col_idx in range(col_count):
            ws.set_column(col_idx, col_idx, 18)

        workbook.close()
        output.seek(0)

        filename = f"reporte_{self.report_type}_{fields.Date.today()}.xlsx"
        self.write({
            'excel_file': base64.b64encode(output.read()),
            'excel_filename': filename,
        })
        output.close()

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/excel_file/{filename}?download=true',
            'target': 'new',
        }
