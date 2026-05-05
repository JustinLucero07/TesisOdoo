from odoo import http
from odoo.http import request


class SalesReportController(http.Controller):

    @http.route('/estate_reports/sales_report_xlsx/<int:wizard_id>',
                type='http', auth='user')
    def download_sales_report_xlsx(self, wizard_id, **kwargs):
        """Descarga el Excel del reporte de promedio de ventas."""
        wizard = request.env['estate.sales.report.wizard'].browse(wizard_id)
        if not wizard.exists():
            return request.not_found()
        wizard.check_access('read')
        content = wizard.generate_xlsx_bytes()
        d_from, d_to = wizard._get_period_range()
        filename = f'reporte_ventas_{d_from}_a_{d_to}.xlsx'
        return request.make_response(
            content,
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f'attachment; filename="{filename}"'),
                ('Content-Length', len(content)),
            ],
        )
