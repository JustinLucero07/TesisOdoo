# -*- coding: utf-8 -*-
"""Nuevos reportes: tiempo de venta (resumen general) y ventas por canal
(agencia vs propietario), pedidos para saber quién cerró cada negocio y
cuánto se tarda en vender una propiedad desde que se publica.

Las pruebas comparan por DELTA (antes/después) en vez de asumir una base de
datos vacía, porque esta suite corre sobre una BD de desarrollo que ya tiene
propiedades vendidas reales."""
import json
from datetime import date, timedelta

from odoo.tests.common import TransactionCase, tagged
from odoo.addons.estate_ai_agent.controllers.estate_ai_controller import EstateAIController


@tagged('post_install', '-at_install', 'estate_ai_sales_reports')
class TestReportSalesByChannel(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ctrl = EstateAIController()
        cls.ptype = cls.env['estate.property.type'].create({'name': 'Casa Reporte Test'})
        cls.owner = cls.env['res.partner'].create({'name': 'Propietario Reporte Test'})

    def _sold_property(self, sold_by, days_on_market):
        listed = date.today() - timedelta(days=days_on_market + 10)
        sold = listed + timedelta(days=days_on_market)
        return self.env['estate.property'].create({
            'title': f'Propiedad {sold_by} {days_on_market}d',
            'property_type_id': self.ptype.id,
            'owner_id': self.owner.id,
            'price': 100000.0,
            'commission_amount': 5000.0,
            'state': 'sold',
            'date_listed': listed,
            'date_sold': sold,
            'sold_by': sold_by,
        })

    def test_time_to_sell_summary(self):
        before = json.loads(self.ctrl._execute_report_data(
            {'report_type': 'time_to_sell_summary'}, self.env))['resumen']

        self._sold_property('agency', 30)
        self._sold_property('agency', 60)
        self._sold_property('owner', 10)

        after = json.loads(self.ctrl._execute_report_data(
            {'report_type': 'time_to_sell_summary'}, self.env))['resumen']

        self.assertEqual(after['ventas_analizadas'], before['ventas_analizadas'] + 3)
        self.assertLessEqual(after['minimo_dias'], 10)
        self.assertGreaterEqual(after['maximo_dias'], 60)

    def test_sales_by_channel(self):
        before = json.loads(self.ctrl._execute_report_data(
            {'report_type': 'sales_by_channel'}, self.env))
        before_data = before.get('data', {})
        before_detalle = {r['canal']: r for r in before.get('detalle', [])}
        before_agency_n = before_data.get('Agencia', 0)
        before_owner_n = before_data.get('Propietario', 0)
        before_external_n = before_data.get('Externo', 0)
        before_agency_comm = float(before_detalle.get('Agencia', {}).get('comisiones', 0) or 0)
        before_owner_comm = float(before_detalle.get('Propietario', {}).get('comisiones', 0) or 0)

        self._sold_property('agency', 30)
        self._sold_property('agency', 60)
        self._sold_property('owner', 10)
        self._sold_property('external', 20)

        after = json.loads(self.ctrl._execute_report_data(
            {'report_type': 'sales_by_channel'}, self.env))
        after_data = after['data']
        after_detalle = {r['canal']: r for r in after['detalle']}

        self.assertEqual(after_data['Agencia'], before_agency_n + 2)
        self.assertEqual(after_data['Propietario'], before_owner_n + 1)
        self.assertEqual(after_data['Externo'], before_external_n + 1,
                          "El asistente de venta permite 'Externo' como tercera opción; el reporte debe reflejarlo")
        self.assertAlmostEqual(
            float(after_detalle['Agencia']['comisiones']),
            before_agency_comm + 10000.0, delta=0.01)
        self.assertAlmostEqual(
            float(after_detalle['Propietario']['comisiones']),
            before_owner_comm + 5000.0, delta=0.01)

    def test_sales_by_channel_sin_ventas_no_falla(self):
        # Dentro de esta transacción de prueba (se revierte al terminar),
        # "apagamos" temporalmente TODAS las ventas para probar el caso vacío.
        self.env['estate.property'].search([('state', '=', 'sold')]).write({'state': 'available'})
        self.env.flush_all()  # _execute_report_data usa SQL crudo: debe ver el write pendiente
        result = json.loads(self.ctrl._execute_report_data(
            {'report_type': 'sales_by_channel'}, self.env))
        self.assertNotIn('error', result)
        self.assertEqual(result['data'], {})
        self.assertIn('mensaje', result)
