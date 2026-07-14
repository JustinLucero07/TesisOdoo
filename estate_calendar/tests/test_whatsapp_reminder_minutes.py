# -*- coding: utf-8 -*-
"""Recordatorio de WhatsApp con anticipación configurable en 3 niveles
(cita > asesor > general), eligiendo la unidad: minutos, horas o días."""
from datetime import datetime, timedelta
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'estate_whatsapp_reminder_minutes')
class TestWhatsappReminderMinutes(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ptype = cls.env['estate.property.type'].create({'name': 'Casa Test WA'})
        cls.owner = cls.env['res.partner'].create({'name': 'Propietario WA', 'phone': '0990000002'})
        cls.prop = cls.env['estate.property'].create({
            'title': 'Casa WA', 'property_type_id': cls.ptype.id,
            'price': 100000.0, 'owner_id': cls.owner.id,
        })
        cls.advisor_default = cls.env['res.users'].create({
            'name': 'Asesor Default', 'login': 'asesor_default_wa',
            'email': 'asesor_default_wa@test.com',
        })
        cls.advisor_default.partner_id.mobile = '0991112222'
        # Asesor con 15 MINUTOS propios
        cls.advisor_custom = cls.env['res.users'].create({
            'name': 'Asesor Custom', 'login': 'asesor_custom_wa',
            'email': 'asesor_custom_wa@test.com',
            'whatsapp_reminder_value': 15, 'whatsapp_reminder_unit': 'minutes',
        })
        cls.advisor_custom.partner_id.mobile = '0993334444'

        ICP = cls.env['ir.config_parameter'].sudo()
        ICP.set_param('estate_calendar.whatsapp_active', 'True')
        ICP.set_param('estate_calendar.whatsapp_notify_client', 'False')
        # General: 1 HORA (= 60 min)
        ICP.set_param('estate_calendar.whatsapp_reminder_default_value', '1')
        ICP.set_param('estate_calendar.whatsapp_reminder_default_unit', 'hours')

    def _make_visit(self, user, minutes_ahead, value=0, unit='minutes'):
        start = datetime.now() + timedelta(minutes=minutes_ahead)
        return self.env['calendar.event'].create({
            'name': 'Visita WA Test',
            'start': start.strftime('%Y-%m-%d %H:%M:%S'),
            'stop': (start + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),
            'property_id': self.prop.id,
            'user_id': user.id,
            'appointment_type': 'visit',
            'whatsapp_reminder_value': value,
            'whatsapp_reminder_unit': unit,
        })

    # --- Conversión de unidades ------------------------------------------

    def test_unidades_se_convierten_a_minutos(self):
        ev_min = self._make_visit(self.advisor_default, 500, value=30, unit='minutes')
        ev_hrs = self._make_visit(self.advisor_default, 500, value=2, unit='hours')
        ev_day = self._make_visit(self.advisor_default, 500, value=1, unit='days')
        self.assertEqual(ev_min.whatsapp_reminder_minutes, 30)
        self.assertEqual(ev_hrs.whatsapp_reminder_minutes, 120)
        self.assertEqual(ev_day.whatsapp_reminder_minutes, 1440)

    def test_asesor_y_general_con_unidades(self):
        # Asesor con 15 minutos propios
        self.assertEqual(self.advisor_custom.whatsapp_reminder_minutes, 15)
        # General configurado en 1 hora
        self.assertEqual(self.env['calendar.event']._global_reminder_minutes(), 60)

    # --- Prioridad cita > asesor > general --------------------------------

    def test_effective_cae_a_asesor_y_a_general(self):
        ev_asesor = self._make_visit(self.advisor_custom, 5)      # asesor = 15 min
        ev_general = self._make_visit(self.advisor_default, 5)    # sin config -> general = 1h
        self.assertEqual(ev_asesor._effective_reminder_minutes(), 15)
        self.assertEqual(ev_general._effective_reminder_minutes(), 60)

    def test_la_cita_manda_sobre_el_asesor(self):
        """Asesor con 15 min, pero la cita fija 2 HORAS: gana la cita."""
        ev = self._make_visit(self.advisor_custom, 100, value=2, unit='hours')
        self.assertEqual(ev._effective_reminder_minutes(), 120)
        with patch.object(type(self.env['calendar.event']), '_send_whatsapp', return_value=True):
            self.env['calendar.event']._cron_send_whatsapp_reminders()
        self.assertTrue(ev.whatsapp_sent,
                        "Con 2 horas en la cita, a 100 min de la cita ya debe avisarse")

    # --- Comportamiento del cron -----------------------------------------

    def test_respeta_minutos_por_asesor(self):
        ev_default_ok = self._make_visit(self.advisor_default, 50)      # general 60 -> avisa
        ev_custom_too_early = self._make_visit(self.advisor_custom, 50)  # asesor 15 -> aun no
        ev_custom_ok = self._make_visit(self.advisor_custom, 10)         # asesor 15 -> avisa

        with patch.object(type(self.env['calendar.event']), '_send_whatsapp', return_value=True):
            self.env['calendar.event']._cron_send_whatsapp_reminders()

        self.assertTrue(ev_default_ok.whatsapp_sent)
        self.assertFalse(ev_custom_too_early.whatsapp_sent)
        self.assertTrue(ev_custom_ok.whatsapp_sent)

    def test_no_reenvia_si_ya_se_envio(self):
        ev = self._make_visit(self.advisor_custom, 10)
        ev.whatsapp_sent = True
        with patch.object(type(self.env['calendar.event']), '_send_whatsapp', return_value=True) as mock_send:
            self.env['calendar.event']._cron_send_whatsapp_reminders()
        mock_send.assert_not_called()
