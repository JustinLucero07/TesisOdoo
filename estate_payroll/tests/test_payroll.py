from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'estate_payroll_smoke')
class TestPayrollLine(TransactionCase):
    """Pruebas de humo de la nómina (cómputos y flujo de estados)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env['hr.employee'].create(
            {'name': 'Empleado Nómina Test'})

    def _make_line(self, **vals):
        base = {
            'employee_id': self.employee.id,
            'period_month': '6',
            'period_year': 2026,
            'base_salary': 1000.0,
        }
        base.update(vals)
        return self.env['estate.payroll.line'].create(base)

    def test_computos_haberes_iess_neto(self):
        line = self._make_line(commission_bonus=200.0, transport_allowance=50.0)
        self.assertEqual(
            line.gross_salary, 1250.0,
            "Haberes = base + bono + transporte + otros")
        self.assertAlmostEqual(
            line.iess_personal, 94.5, places=2,
            msg="Aporte IESS personal = 9.45% del sueldo base")
        self.assertAlmostEqual(
            line.net_salary, line.gross_salary - line.total_deductions, places=2,
            msg="Neto = haberes - deducciones")

    def test_flujo_confirmar(self):
        line = self._make_line()
        self.assertEqual(line.state, 'draft')
        line.action_confirm()
        self.assertEqual(
            line.state, 'confirmed', "action_confirm debe pasar a 'confirmed'")
