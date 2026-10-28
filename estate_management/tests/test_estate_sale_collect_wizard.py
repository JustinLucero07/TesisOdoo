# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'estate_sale_collect')
class TestEstateSaleCollectWizard(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env['res.partner']
        cls.buyer = cls.Partner.create({'name': 'Comprador Test'})
        cls.owner = cls.Partner.create({'name': 'Propietario Test'})

        cls.prop_type = cls.env['estate.property.type'].create({'name': 'Departamento Test'})
        cls.property = cls.env['estate.property'].create({
            'title': 'Depto en Cuenca',
            'price': 100000.0,
            'property_type_id': cls.prop_type.id,
            'owner_id': cls.owner.id,
            'state': 'sold',
        })

        cls.product = cls.property.product_id

        # Orden de venta sin impuestos iniciales (comisión de $2,000)
        cls.order = cls.env['sale.order'].create({
            'partner_id': cls.owner.id,
            'property_id': cls.property.id,
            'estate_transaction_type': 'sale',
            'order_line': [(0, 0, {
                'product_id': cls.product.product_variant_id.id,
                'name': 'Honorarios de Corretaje',
                'price_unit': 2000.0,
                'product_uom_qty': 1,
            })],
        })
        cls.order.action_confirm()

    def test_wizard_con_factura_suma_15_pct(self):
        wizard = self.env['estate.sale.collect.wizard'].with_context(
            active_model='sale.order', active_ids=self.order.ids
        ).create({
            'invoice': 'with',
            'method': 'transfer',
            'reference': 'REF-12345',
        })

        self.assertEqual(wizard.amount_untaxed, 2000.0)
        self.assertEqual(wizard.amount_vat, 300.0)  # 15% de 2000
        self.assertEqual(wizard.amount_total, 2300.0)

        # Confirmar cobro
        wizard.action_confirm()

        self.assertTrue(self.order.estate_commission_collected)
        self.assertEqual(self.order.estate_collected_invoice, 'with')
        self.assertEqual(self.order.amount_tax, 300.0)
        self.assertEqual(self.order.amount_total, 2300.0)

    def test_wizard_sin_factura_deja_igual(self):
        wizard = self.env['estate.sale.collect.wizard'].with_context(
            active_model='sale.order', active_ids=self.order.ids
        ).create({
            'invoice': 'without',
            'method': 'cash',
        })

        self.assertEqual(wizard.amount_untaxed, 2000.0)
        self.assertEqual(wizard.amount_vat, 0.0)
        self.assertEqual(wizard.amount_total, 2000.0)

        # Confirmar cobro
        wizard.action_confirm()

        self.assertTrue(self.order.estate_commission_collected)
        self.assertEqual(self.order.estate_collected_invoice, 'without')
        self.assertEqual(self.order.amount_tax, 0.0)
        self.assertEqual(self.order.amount_total, 2000.0)

    def test_wizard_onchange_dinamico(self):
        wizard = self.env['estate.sale.collect.wizard'].with_context(
            active_model='sale.order', active_ids=self.order.ids
        ).create({
            'invoice': 'with',
        })

        self.assertEqual(wizard.amount_total, 2300.0)

        # Cambiar a sin factura
        wizard.invoice = 'without'
        wizard._onchange_invoice()
        self.assertEqual(wizard.amount_total, 2000.0)
        self.assertEqual(wizard.amount_vat, 0.0)

        # Volver a con factura
        wizard.invoice = 'with'
        wizard._onchange_invoice()
        self.assertEqual(wizard.amount_total, 2300.0)
        self.assertEqual(wizard.amount_vat, 300.0)

    def _collect(self, mode, method='transfer'):
        self.env['estate.sale.collect.wizard'].with_context(
            active_model='sale.order', active_ids=self.order.ids
        ).create({'invoice': mode, 'method': method, 'reference': 'DEP-9'}).action_confirm()
        return self.order.estate_collection_payment_ids

    def test_cobro_con_factura_queda_pagado_en_facturacion(self):
        pays = self._collect('with')
        self.assertEqual(len(pays), 1)
        self.assertEqual(pays.estate_kind, 'collection')
        self.assertAlmostEqual(pays.amount, 2300.0, places=2)
        inv = self.order.invoice_ids.filtered(lambda m: m.state == 'posted')
        self.assertTrue(inv)
        self.assertIn(inv.payment_state, ('paid', 'in_payment'))

    def test_cobro_con_factura_0(self):
        pays = self._collect('with_0')
        self.assertAlmostEqual(pays.amount, 2000.0, places=2)
        self.assertEqual(pays.estate_invoice_mode, 'with_0')
        self.assertAlmostEqual(self.order.amount_tax, 0.0)

    def test_cobro_sin_factura_recibo_directo_y_quitar_cobro(self):
        pays = self._collect('without', 'cash')
        self.assertEqual(pays.payment_type, 'inbound')
        self.assertAlmostEqual(pays.amount, 2000.0, places=2)
        self.assertFalse(self.order.invoice_ids.filtered(lambda m: m.state == 'posted'))
        html, _ = self.env['ir.actions.report']._render_qweb_html(
            'estate_management.action_report_estate_payment_receipt', pays.ids)
        self.assertIn(b'Recibo de cobro', html)

        self.order.action_estate_unmark_collected()
        self.assertFalse(self.order.estate_commission_collected)
        self.assertEqual(pays.state, 'canceled')

    def test_venta_cobrada_antes_del_cambio_registra_el_cobro_al_verlo(self):
        """Ventas marcadas cobradas sin pago en Facturación (versión anterior):
        Ver cobro / Imprimir recibo lo registran con los datos guardados."""
        self.order.write({
            'estate_collected_manual': True,
            'estate_collected_manual_date': '2026-10-23',
            'estate_collected_method_manual': 'transfer',
            'estate_collected_invoice_manual': 'without',
            'estate_collected_reference': 'BANCO-1',
        })
        self.assertFalse(self.order.estate_collection_payment_ids)
        action = self.order.action_estate_view_collection()
        pay = self.env['account.payment'].browse(action['res_id'])
        self.assertEqual(pay.estate_kind, 'collection')
        self.assertAlmostEqual(pay.amount, 2000.0, places=2)
        self.assertEqual(str(pay.date), '2026-10-23')
        # La segunda vez no duplica
        self.order.action_estate_print_collection()
        self.assertEqual(len(self.order.estate_collection_payment_ids), 1)

    def test_corregir_cobro(self):
        pays = self._collect('with')
        correct = self.env['estate.payment.correct.wizard'].with_context(
            active_model='sale.order', active_ids=self.order.ids).create({})
        self.assertEqual(correct.kind, 'collection')
        correct.write({'date': '2026-10-02', 'invoice': 'with_0', 'bank_to': 'Banco Pichincha'})
        correct.action_confirm()
        self.assertEqual(pays.state, 'canceled')
        nuevo = self.order.estate_collection_payment_ids.filtered(lambda p: p.state != 'canceled')
        self.assertEqual(len(nuevo), 1)
        self.assertEqual(str(nuevo.date), '2026-10-02')
        self.assertEqual(nuevo.estate_invoice_mode, 'with_0')
        self.assertEqual(nuevo.estate_bank_to, 'Banco Pichincha')
        self.assertAlmostEqual(nuevo.amount, 2000.0, places=2)
        self.assertTrue(self.order.estate_commission_collected)

    def test_accesos_directos(self):
        self._collect('with')
        self.assertEqual(self.order.estate_link_collection_count, 1)
        self.assertEqual(self.order.action_estate_view_property()['res_id'], self.property.id)
        pay = self.order.estate_collection_payment_ids
        self.assertEqual(pay.estate_link_order_id, self.order)
        self.assertEqual(pay.action_estate_view_order()['res_id'], self.order.id)
        self.assertEqual(self.property.estate_link_sale_count, 1)
        self.assertEqual(self.property.estate_link_payment_count, 1)
        self.property.action_view_estate_payments()
        self.property.action_view_sale_orders()

    def test_cobro_con_iva_incluido(self):
        """3.000 con IVA incluido: el total no cambia y se desglosa el IVA."""
        self.order.order_line.price_unit = 3000.0
        wiz = self.env['estate.sale.collect.wizard'].with_context(
            active_model='sale.order', active_ids=self.order.ids).create({'invoice': 'with_incl'})
        self.assertAlmostEqual(wiz.amount_total, 3000.0, places=2)
        self.assertAlmostEqual(wiz.amount_untaxed, 2608.70, places=2)
        self.assertAlmostEqual(wiz.amount_vat, 391.30, places=2)
        wiz.action_confirm()
        pay = self.order.estate_collection_payment_ids
        self.assertAlmostEqual(pay.amount, 3000.0, places=2)
        inv = self.order.invoice_ids.filtered(lambda m: m.state == 'posted')
        self.assertAlmostEqual(inv.amount_total, 3000.0, places=2)
        self.assertAlmostEqual(inv.amount_untaxed, 2608.70, places=1)

    def _make_allied(self):
        agency = self.Partner.create({'name': 'Agencia Aliada Test', 'is_allied_agency': True})
        self.property.write({'is_allied_property': True, 'allied_agency_id': agency.id,
                             'allied_split_pct': 50.0})
        return agency

    def test_aliado_solo_nuestra_parte(self):
        self._make_allied()
        wiz = self.env['estate.sale.collect.wizard'].with_context(
            active_model='sale.order', active_ids=self.order.ids).create(
            {'invoice': 'without', 'note': 'Pagó en dos partes'})
        self.assertTrue(wiz.has_allied)
        self.assertAlmostEqual(wiz.allied_share, 1000.0)
        self.assertAlmostEqual(wiz.amount_total, 1000.0)
        wiz.action_confirm()
        pay = self.order.estate_collection_payment_ids
        self.assertAlmostEqual(pay.amount, 1000.0)
        self.assertEqual(pay.estate_note, 'Pagó en dos partes')
        self.assertFalse(self.order.estate_third_payment_ids)
        self.assertAlmostEqual(self.order.estate_commission_gross, 2000.0)

    def test_aliado_cobramos_total_y_pagamos_al_aliado(self):
        agency = self._make_allied()
        wiz = self.env['estate.sale.collect.wizard'].with_context(
            active_model='sale.order', active_ids=self.order.ids).create(
            {'invoice': 'without', 'collect_full': True})
        self.assertAlmostEqual(wiz.amount_total, 2000.0)
        wiz.action_confirm()
        self.assertAlmostEqual(self.order.estate_collection_payment_ids.amount, 2000.0)
        third = self.order.estate_third_payment_ids
        self.assertEqual(third.partner_id, agency)
        self.assertAlmostEqual(third.amount, 1000.0)
        self.assertAlmostEqual(self.order.estate_office_amount, 1000.0)
        # Quitar el cobro anula también el pago al aliado
        self.order.action_estate_unmark_collected()
        self.assertEqual(third.state, 'canceled')

    def test_pago_a_tercero_descuenta_de_la_oficina(self):
        self._collect('without')
        helper = self.Partner.create({'name': 'Colaborador Test'})
        action = self.env['estate.third.payment.wizard'].create({
            'order_id': self.order.id, 'partner_id': helper.id, 'amount': 500.0,
            'concept': 'Referido', 'method': 'cash', 'invoice_number': '001-001-55',
        }).action_confirm()
        pay = self.order.estate_third_payment_ids
        self.assertEqual(pay.estate_kind, 'third')
        self.assertAlmostEqual(pay.amount, 500.0)
        self.assertAlmostEqual(self.order.estate_office_amount, 1500.0)
        self.assertEqual(action['type'], 'ir.actions.report')
        html, _ = self.env['ir.actions.report']._render_qweb_html(
            'estate_management.action_report_estate_payment_receipt', pay.ids)
        self.assertIn(b'Referido', html)
        self.assertIn(b'001-001-55', html)
