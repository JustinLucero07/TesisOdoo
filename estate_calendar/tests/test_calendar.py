# -*- coding: utf-8 -*-
"""Pruebas del módulo estate_calendar (visitas / calendario).

Cubre el flujo de visitas inmobiliarias sobre calendar.event:
campo cliente, datos relacionados, color, estados y avance de lead.
"""
from datetime import datetime, timedelta

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestEstateCalendar(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ptype = cls.env['estate.property.type'].create({'name': 'Casa Test'})
        cls.owner = cls.env['res.partner'].create({
            'name': 'Propietario Test', 'phone': '0990000001'})
        cls.client = cls.env['res.partner'].create({
            'name': 'Cliente Test', 'phone': '0991112233', 'mobile': '0997778899'})
        cls.prop = cls.env['estate.property'].create({
            'title': 'Casa de Prueba',
            'property_type_id': cls.ptype.id,
            'price': 123000.0,
            'owner_id': cls.owner.id,
        })

    def _make_visit(self, **extra):
        start = datetime.now() + timedelta(days=2)
        vals = {
            'name': 'Visita Test',
            'start': start.strftime('%Y-%m-%d %H:%M:%S'),
            'stop': (start + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),
            'property_id': self.prop.id,
            'client_id': self.client.id,
            'appointment_type': 'visit',
        }
        vals.update(extra)
        return self.env['calendar.event'].create(vals)

    def test_client_id_persists(self):
        """Regresión: el cliente NO debe ser sobreescrito por el organizador."""
        ev = self._make_visit()
        self.assertEqual(ev.client_id, self.client,
                         "client_id debe conservar el cliente asignado")
        # El partner_id base (Scheduled by) sigue siendo el del organizador
        self.assertEqual(ev.partner_id, ev.user_id.partner_id,
                         "partner_id base debe seguir ligado al organizador")

    def test_related_client_phones(self):
        """Datos Clave: teléfono y celular del cliente vía related."""
        ev = self._make_visit()
        self.assertEqual(ev.client_phone, '0991112233')
        self.assertEqual(ev.client_mobile, '0997778899')

    def test_related_property_data(self):
        """Datos Clave: precio, tipo y propietario de la propiedad."""
        ev = self._make_visit()
        self.assertEqual(ev.property_price, 123000.0)
        self.assertEqual(ev.property_type_name, 'Casa Test')
        self.assertEqual(ev.property_owner_name, 'Propietario Test')

    def test_visit_color_scheduled_and_done(self):
        """El color es azul (4) si está programada y verde (10) si realizada."""
        ev = self._make_visit()
        self.assertEqual(ev.visit_color, 4)
        ev.action_done_visit()
        self.assertEqual(ev.visit_state, 'done')
        self.assertEqual(ev.visit_color, 10)

    def test_cancel_and_reschedule(self):
        ev = self._make_visit()
        ev.action_cancel_visit()
        self.assertEqual(ev.visit_state, 'cancelled')
        self.assertEqual(ev.visit_color, 1)
        ev.action_schedule_visit()
        self.assertEqual(ev.visit_state, 'scheduled')

    def test_appointment_type_color(self):
        """Una llamada (sin realizarse) usa el color de su tipo (3)."""
        ev = self._make_visit(appointment_type='call')
        self.assertEqual(ev.visit_color, 3)

    def test_get_related_lead_no_crash(self):
        """_get_related_lead no falla aunque no haya lead asociado."""
        ev = self._make_visit()
        lead = ev._get_related_lead()
        self.assertEqual(lead._name, 'crm.lead')

    def test_survey_returns_url_action(self):
        """La encuesta post-visita devuelve una acción de URL (wa.me)."""
        ev = self._make_visit()
        res = ev.action_send_survey_whatsapp()
        self.assertEqual(res.get('type'), 'ir.actions.act_url')
        self.assertIn('wa.me', res.get('url', ''))
        self.assertTrue(ev.survey_sent)
