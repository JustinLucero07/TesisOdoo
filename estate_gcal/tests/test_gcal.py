from datetime import datetime, timedelta

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'estate_gcal_smoke')
class TestGcalSync(TransactionCase):
    """Pruebas de humo de la extensión de Google Calendar.

    Sin cuenta de servicio configurada, los overrides de create/write/unlink
    deben degradar a no-op sin lanzar excepciones.
    """

    def setUp(self):
        super().setUp()
        # Garantiza que no hay credenciales -> el sync debe omitirse.
        self.env['ir.config_parameter'].sudo().set_param('estate_gcal.sa_json', '')

    def test_evento_crud_sin_credenciales(self):
        start = datetime.now() + timedelta(days=1)
        event = self.env['calendar.event'].create({
            'name': 'Evento Gcal Test',
            'start': start,
            'stop': start + timedelta(hours=1),
        })
        self.assertTrue(event.exists(), "El evento debe crearse sin error")

        event.write({'name': 'Evento Gcal Modificado'})
        self.assertEqual(event.name, 'Evento Gcal Modificado')

        event.unlink()
        self.assertFalse(event.exists(), "El evento debe eliminarse sin error")
