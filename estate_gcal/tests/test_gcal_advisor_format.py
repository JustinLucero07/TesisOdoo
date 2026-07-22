from datetime import datetime, timedelta

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'estate_gcal_format')
class TestGcalAdvisorFormat(TransactionCase):
    """Formato del evento en Google Calendar: iniciales, color y título."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.advisor = cls.env['res.users'].create({
            'name': 'Ricardo Molina', 'login': 'ricardo.gcal.test',
            'gcal_initials': 'RM', 'gcal_color_id': '9',
        })
        cls.ptype = cls.env['estate.property.type'].create({'name': 'Casa GcalFmt Test'})
        cls.prop = cls.env['estate.property'].create({
            'title': 'Casa Cascada 85', 'price': 90000.0, 'property_type_id': cls.ptype.id,
        })
        cls.client = cls.env['res.partner'].create({'name': 'Edisson Quinde'})

    def _event(self, **extra):
        start = datetime.now() + timedelta(days=1)
        vals = {
            'name': 'Visita Test', 'start': start, 'stop': start + timedelta(hours=1),
            'property_id': self.prop.id, 'client_id': self.client.id, 'user_id': self.advisor.id,
        }
        vals.update(extra)
        return self.env['calendar.event'].create(vals)

    def test_titulo_con_iniciales_y_cliente(self):
        ev = self._event()
        body = ev._gcal_body()
        self.assertEqual(body['summary'], '(RM) Casa Cascada 85 / Edisson Quinde')

    def test_color_del_asesor_se_incluye(self):
        ev = self._event()
        body = ev._gcal_body()
        self.assertEqual(body.get('colorId'), '9')

    def test_iniciales_automaticas_si_no_configuradas(self):
        advisor2 = self.env['res.users'].create({'name': 'Elena Paredes', 'login': 'elena.gcal.test'})
        ev = self._event(user_id=advisor2.id)
        self.assertEqual(ev._gcal_advisor_initials(), 'EP')

    def test_sin_cliente_no_agrega_barra(self):
        ev = self._event(client_id=False)
        body = ev._gcal_body()
        self.assertNotIn('/', body['summary'])
        self.assertTrue(body['summary'].startswith('(RM)'))

    def test_sin_color_configurado_usa_color_automatico_estable(self):
        """Si el asesor no configuró un color a mano, se le asigna uno
        automático (no queda sin color, y siempre es el mismo para él)."""
        advisor3 = self.env['res.users'].create({'name': 'Sin Color', 'login': 'sincolor.gcal.test'})
        ev = self._event(user_id=advisor3.id)
        body = ev._gcal_body()
        self.assertIn('colorId', body)
        self.assertEqual(body['colorId'], advisor3._gcal_default_color_id())
        # Estable: se repite el mismo cálculo en una segunda llamada
        self.assertEqual(ev._gcal_body()['colorId'], body['colorId'])
