from datetime import date, timedelta

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'estate_sales_report')
class TestSalesReportWizard(TransactionCase):
    """Tests del cálculo de KPIs del reporte de promedio de ventas."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Wizard = cls.env['estate.sales.report.wizard']
        cls.Property = cls.env['estate.property']
        cls.prop_type = cls.env['estate.property.type'].create({'name': 'Tipo Sales Report'})

        # Dataset controlado: 4 propiedades vendidas con precios 100k/200k/300k/400k
        cls.props = cls.env['estate.property']
        prices = [100000.0, 200000.0, 300000.0, 400000.0]
        for i, price in enumerate(prices):
            p = cls.Property.create({
                'title': f'Casa {i + 1}',
                'price': price,
                'bottom_price': price * 0.85,
                'state': 'sold',
                'property_type_id': cls.prop_type.id,
                'city': 'Cuenca',
            })
            cls.props |= p

    def _make_wizard(self, **overrides):
        vals = {
            'period': 'custom',
            'date_from': date.today() - timedelta(days=365),
            'date_to': date.today() + timedelta(days=1),
            'operation_type': 'sale',
            'property_type_ids': [(6, 0, [self.prop_type.id])],
        }
        vals.update(overrides)
        return self.Wizard.create(vals)

    def test_avg_price_correct(self):
        wiz = self._make_wizard()
        # Promedio = (100k+200k+300k+400k)/4 = 250k
        self.assertEqual(wiz.kpi_avg_price, 250000.0)

    def test_count_correct(self):
        wiz = self._make_wizard()
        self.assertEqual(wiz.kpi_count, 4)

    def test_min_max_correct(self):
        wiz = self._make_wizard()
        self.assertEqual(wiz.kpi_min_price, 100000.0)
        self.assertEqual(wiz.kpi_max_price, 400000.0)

    def test_median_correct(self):
        wiz = self._make_wizard()
        # Mediana de 4 valores [100k, 200k, 300k, 400k] = (200k+300k)/2 = 250k
        self.assertEqual(wiz.kpi_median_price, 250000.0)

    def test_pct_vs_listed(self):
        wiz = self._make_wizard()
        # listed = bottom_price * 1.15 = (price * 0.85) * 1.15 = price * 0.9775
        # ratio = price / (price * 0.9775) = 1/0.9775 ~ 1.023 → ~102.3%
        self.assertAlmostEqual(wiz.kpi_pct_vs_listed, 102.30, places=1)

    def test_filter_by_city(self):
        # Crear 1 propiedad en otra ciudad
        self.Property.create({
            'title': 'Casa Quito',
            'price': 999999.0,
            'state': 'sold',
            'property_type_id': self.prop_type.id,
            'city': 'Quito',
        })
        wiz = self._make_wizard(city='Cuenca')
        self.assertEqual(wiz.kpi_count, 4)  # solo las de Cuenca
        self.assertEqual(wiz.kpi_avg_price, 250000.0)

    def test_no_data_handles_zero_division(self):
        wiz = self._make_wizard(city='CiudadInexistente')
        self.assertFalse(wiz.has_data)
        self.assertEqual(wiz.kpi_avg_price, 0.0)
        self.assertEqual(wiz.kpi_count, 0)

    def test_custom_period_validation(self):
        # date_to anterior a date_from → debe lanzar UserError
        wiz = self._make_wizard(date_from=date.today(), date_to=date.today() - timedelta(days=10))
        with self.assertRaises(UserError):
            wiz._get_period_range()

    def test_custom_period_missing_dates(self):
        wiz = self.Wizard.create({
            'period': 'custom',
            'operation_type': 'sale',
        })
        with self.assertRaises(UserError):
            wiz._get_period_range()

    def test_period_quarter(self):
        wiz = self._make_wizard(period='quarter')
        d_from, d_to = wiz._get_period_range()
        # date_from debe ser el primer día del trimestre actual
        today = date.today()
        expected_month = ((today.month - 1) // 3) * 3 + 1
        self.assertEqual(d_from.month, expected_month)
        self.assertEqual(d_from.day, 1)

    def test_previous_period_calculation(self):
        d_from = date(2026, 1, 1)
        d_to = date(2026, 3, 31)
        prev_from, prev_to = self.Wizard._get_previous_period_range(d_from, d_to)
        # El período anterior debe tener la misma duración
        self.assertEqual((d_to - d_from).days, (prev_to - prev_from).days)
        self.assertEqual(prev_to, date(2025, 12, 31))

    def test_chart_data_top_cities(self):
        import json
        wiz = self._make_wizard()
        cd = json.loads(wiz.chart_data)
        cities = dict(cd.get('top_cities', []))
        self.assertIn('Cuenca', cities)
        # Volumen total de Cuenca = 100k+200k+300k+400k = 1M
        self.assertEqual(cities['Cuenca'], 1000000.0)

    def test_action_open_detail_returns_action(self):
        wiz = self._make_wizard()
        action = wiz.action_open_detail()
        self.assertEqual(action['res_model'], 'estate.property')
        self.assertEqual(len(action['domain'][0][2]), 4)

    def test_xlsx_generation(self):
        wiz = self._make_wizard()
        try:
            content = wiz.generate_xlsx_bytes()
            self.assertTrue(content.startswith(b'PK'))  # XLSX = ZIP file (PK header)
            self.assertGreater(len(content), 1000)
        except UserError as e:
            # Si xlsxwriter no está instalado, el error es esperado
            self.assertIn('xlsxwriter', str(e))
