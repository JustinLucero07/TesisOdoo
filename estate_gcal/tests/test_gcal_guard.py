from datetime import datetime, timedelta

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'estate_gcal_guard')
class TestGcalGuard(TransactionCase):
    """Con Google Calendar desactivado, el calendario opera sin errores ni sync."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Aseguramos el modo 'none' (sin sincronización con Google).
        cls.env['ir.config_parameter'].sudo().set_param('estate_gcal.mode', 'none')
        ptype = cls.env['estate.property.type'].create({'name': 'Casa GCal Test'})
        cls.prop = cls.env['estate.property'].create({
            'title': 'Casa GCal', 'price': 70000.0, 'property_type_id': ptype.id,
        })

    def _event(self):
        start = datetime.now() + timedelta(days=1)
        return self.env['calendar.event'].create({
            'name': 'Visita Test',
            'start': start,
            'stop': start + timedelta(hours=1),
            'property_id': self.prop.id,
        })

    def test_crear_evento_sin_gcal_no_falla(self):
        ev = self._event()
        self.assertTrue(ev.exists())
        self.assertFalse(ev.gcal_event_id, "Sin sync no debe asignarse un ID de Google")

    def test_escribir_y_borrar_sin_gcal(self):
        ev = self._event()
        ev.write({'name': 'Visita Reprogramada'})
        self.assertEqual(ev.name, 'Visita Reprogramada')
        ev.unlink()
        self.assertFalse(ev.exists())

    def test_es_visita_con_propiedad(self):
        ev = self._event()
        self.assertTrue(ev._gcal_is_visit(), "Un evento con propiedad es una visita")
