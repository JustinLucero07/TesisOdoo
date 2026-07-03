from datetime import datetime, timedelta
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged
from odoo.addons.estate_gcal.models.calendar_event import CalendarEvent


@tagged('post_install', '-at_install', 'estate_gcal_pull')
class TestGcalPullSync(TransactionCase):
    """Sincronización Google -> Odoo: borrados y reprogramaciones detectados
    por la revisión periódica (_cron_gcal_pull), sin llamadas reales a Google."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ptype = cls.env['estate.property.type'].create({'name': 'Casa Pull Test'})
        cls.prop = cls.env['estate.property'].create({
            'title': 'Casa Pull', 'price': 50000.0, 'property_type_id': cls.ptype.id,
        })
        start = datetime.now() + timedelta(days=2)
        # Se crea con el modo aún en 'none' (no configurado) para que no intente
        # sincronizar de verdad; luego se le asigna un gcal_event_id "de mentira".
        cls.event = cls.env['calendar.event'].create({
            'name': 'Visita Pull Test', 'start': start, 'stop': start + timedelta(hours=1),
            'property_id': cls.prop.id,
        })
        cls.event.with_context(gcal_skip=True).write({'gcal_event_id': 'gcal_fake_id_123'})

        ICP = cls.env['ir.config_parameter'].sudo()
        ICP.set_param('estate_gcal.mode', 'shared')
        ICP.set_param('estate_gcal.sa_json', '{"type": "service_account"}')
        ICP.set_param('estate_gcal.calendar_id', 'equipo@test.com')
        ICP.set_param('estate_gcal.sync_token', '')

    def _run_pull(self, fake_events, next_token='next-token'):
        with patch.object(CalendarEvent, '_gcal_token', return_value='fake-token'), \
             patch.object(CalendarEvent, '_gcal_fetch_changes', return_value=(fake_events, next_token)):
            self.env['calendar.event']._cron_gcal_pull()

    def test_cancelacion_en_google_marca_cancelada_en_odoo(self):
        self._run_pull([{'id': 'gcal_fake_id_123', 'status': 'cancelled'}])
        self.event.invalidate_recordset()
        self.assertEqual(self.event.visit_state, 'cancelled')
        self.assertFalse(self.event.gcal_event_id, "Debe soltar el ID de Google tras la cancelación")

    def test_evento_ajeno_no_afecta_visitas_propias(self):
        self._run_pull([{'id': 'evento-que-no-existe-en-odoo', 'status': 'cancelled'}])
        self.event.invalidate_recordset()
        self.assertEqual(self.event.visit_state, 'scheduled')

    def test_reprogramacion_en_google_actualiza_horario(self):
        new_start = datetime.now() + timedelta(days=3)
        new_stop = new_start + timedelta(hours=2)
        self._run_pull([{
            'id': 'gcal_fake_id_123',
            'start': {'dateTime': new_start.isoformat() + 'Z'},
            'end': {'dateTime': new_stop.isoformat() + 'Z'},
        }])
        self.event.invalidate_recordset()
        self.assertAlmostEqual(self.event.start, new_start, delta=timedelta(seconds=5))
        self.assertAlmostEqual(self.event.stop, new_stop, delta=timedelta(seconds=5))

    def test_guarda_el_sync_token_recibido(self):
        self._run_pull([], next_token='token-guardado-xyz')
        token = self.env['ir.config_parameter'].sudo().get_param('estate_gcal.sync_token')
        self.assertEqual(token, 'token-guardado-xyz')

    def test_sin_configuracion_no_hace_nada(self):
        ICP = self.env['ir.config_parameter'].sudo()
        ICP.set_param('estate_gcal.mode', 'none')
        with patch.object(CalendarEvent, '_gcal_fetch_changes') as mocked:
            self.env['calendar.event']._cron_gcal_pull()
            mocked.assert_not_called()
        ICP.set_param('estate_gcal.mode', 'shared')
