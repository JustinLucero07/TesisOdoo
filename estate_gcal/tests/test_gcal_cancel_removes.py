from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from odoo.tests.common import TransactionCase, tagged
from odoo.addons.estate_gcal.models.calendar_event import CalendarEvent


@tagged('post_install', '-at_install', 'estate_gcal_cancel')
class TestGcalCancelRemoves(TransactionCase):
    """Odoo -> Google: cancelar/eliminar una visita en Odoo borra el evento
    en el calendario compartido (sin llamadas reales a Google)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ptype = cls.env['estate.property.type'].create({'name': 'Casa Cancel Test'})
        cls.prop = cls.env['estate.property'].create({
            'title': 'Casa Cancel', 'price': 60000.0, 'property_type_id': cls.ptype.id,
        })
        start = datetime.now() + timedelta(days=1)
        cls.event = cls.env['calendar.event'].create({
            'name': 'Visita Cancel Test', 'start': start, 'stop': start + timedelta(hours=1),
            'property_id': cls.prop.id,
        })
        cls.event.with_context(gcal_skip=True).write({'gcal_event_id': 'gcal_fake_id_456'})

        ICP = cls.env['ir.config_parameter'].sudo()
        ICP.set_param('estate_gcal.mode', 'shared')
        ICP.set_param('estate_gcal.sa_json', '{"type": "service_account"}')
        ICP.set_param('estate_gcal.calendar_id', 'equipo@test.com')

    def test_cancelar_en_odoo_borra_en_google(self):
        fake_resp = MagicMock(ok=True, status_code=204)
        with patch.object(CalendarEvent, '_gcal_token', return_value='fake-token'), \
             patch('odoo.addons.estate_gcal.models.calendar_event.requests.delete',
                   return_value=fake_resp) as mocked_delete:
            self.event.write({'visit_state': 'cancelled'})
        mocked_delete.assert_called_once()
        self.assertIn('gcal_fake_id_456', mocked_delete.call_args[0][0])
        self.event.invalidate_recordset()
        self.assertFalse(self.event.gcal_event_id)

    def test_no_recrea_en_google_tras_cancelar(self):
        """Un cambio posterior sobre una visita ya cancelada no debe recrearla en Google."""
        fake_resp = MagicMock(ok=True, status_code=204)
        with patch.object(CalendarEvent, '_gcal_token', return_value='fake-token'), \
             patch('odoo.addons.estate_gcal.models.calendar_event.requests.delete',
                   return_value=fake_resp):
            self.event.write({'visit_state': 'cancelled'})

        with patch.object(CalendarEvent, '_gcal_token', return_value='fake-token'), \
             patch('odoo.addons.estate_gcal.models.calendar_event.requests.post') as mocked_post:
            self.event.write({'name': 'Visita Cancel Test (editada)'})
            mocked_post.assert_not_called()
