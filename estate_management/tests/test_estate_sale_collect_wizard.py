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
