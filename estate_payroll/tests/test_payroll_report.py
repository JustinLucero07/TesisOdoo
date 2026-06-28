from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'estate_payroll_report')
class TestPayrollReport(TransactionCase):
    """Recibo PDF de nómina: render del HTML y compañía por defecto."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env['hr.employee'].create({'name': 'Empleado Recibo Test'})
        cls.line = cls.env['estate.payroll.line'].create({
            'employee_id': cls.employee.id,
            'period_month': '6',
            'period_year': 2026,
            'base_salary': 1200.0,
            'commission_bonus': 300.0,
        })

    def test_company_por_defecto(self):
        self.assertEqual(self.line.company_id, self.env.company,
                         "La nómina toma la compañía actual por defecto")

    def test_render_html_recibo(self):
        report = self.env.ref('estate_payroll.action_report_estate_payroll')
        html, _type = report._render_qweb_html(
            'estate_payroll.report_payroll_slip', self.line.ids)
        self.assertIn(b'Recibo de N', html, "El recibo debe titularse 'Recibo de Nómina'")
        self.assertIn(self.employee.name.encode(), html,
                      "El recibo debe incluir el nombre del empleado")
        self.assertIn(b'Neto a Pagar', html, "El recibo debe mostrar el neto a pagar")
