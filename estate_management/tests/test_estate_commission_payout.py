# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'estate_commission_payout')
class TestEstateCommissionPayout(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.currency = cls.env.company.currency_id
        cls.prop_type = cls.env['estate.property.type'].create({'name': 'Departamento Test'})
        cls.user_advisor1 = cls.env['res.users'].create({
            'name': 'Ufredo Reyes',
            'login': 'ufredo@test.com',
            'email': 'ufredo@test.com',
        })
        cls.user_advisor2 = cls.env['res.users'].create({
            'name': 'Camila Ortiz',
            'login': 'camila@test.com',
            'email': 'camila@test.com',
        })
        cls.property = cls.env['estate.property'].create({
            'title': 'Departamento Gran Manzana',
            'price': 76500.0,
            'commission_percentage': 3.0,
            'property_type_id': cls.prop_type.id,
            'is_exclusive': False,
        })
        cls.commission = cls.env['estate.commission'].create({
            'property_id': cls.property.id,
            'sale_amount': 76500.0,
            'commission_pct': 3.0,
            'amount': 2295.0,
            'client_collection_state': 'collected',
            'state': 'approved',
        })
        # Preparar reparto: Ufredo 8% (captación), Camila 10% (recepción), 15% (visita), 15% (cierre)
        cls.commission.split_line_ids = [
            (0, 0, {'sequence': 10, 'role': 'capture', 'percentage': 8.0, 'user_id': cls.user_advisor1.id}),
            (0, 0, {'sequence': 20, 'role': 'reception', 'percentage': 10.0, 'user_id': cls.user_advisor2.id}),
            (0, 0, {'sequence': 30, 'role': 'visit', 'percentage': 15.0, 'user_id': cls.user_advisor2.id}),
            (0, 0, {'sequence': 40, 'role': 'closing', 'percentage': 15.0, 'user_id': cls.user_advisor2.id}),
        ]

    def test_payout_wizard_groups_by_unique_advisor(self):
        """Verifica que si un asesor tiene varios roles (Camila: recepción, visita, cierre),
        en el wizard aparezca agrupado en una sola fila con la suma de sus montos base."""
        wizard = self.env['estate.commission.payout.wizard'].with_context(
            default_commission_id=self.commission.id,
            default_mode='split'
        ).create({'payment_method': 'transfer'})

        self.assertEqual(len(wizard.line_ids), 2, "Deben haber solo 2 filas de asesores (Ufredo y Camila)")
        
        line_camila = wizard.line_ids.filtered(lambda l: l.user_id == self.user_advisor2)
        self.assertEqual(len(line_camila), 1)
        # Camila: 10% + 15% + 15% = 40% de 2295 = 918.00
        self.assertAlmostEqual(line_camila.amount_base, 918.0, places=2)

        line_ufredo = wizard.line_ids.filtered(lambda l: l.user_id == self.user_advisor1)
        self.assertEqual(len(line_ufredo), 1)
        # Ufredo: 8% de 2295 = 183.60
        self.assertAlmostEqual(line_ufredo.amount_base, 183.6, places=2)

    def test_payout_wizard_con_y_sin_factura_por_asesor(self):
        """Ufredo cobra sin factura (neto 183.60).
        Camila cobra con factura (+15% IVA = 918 + 137.70 = 1055.70)."""
        wizard = self.env['estate.commission.payout.wizard'].with_context(
            default_commission_id=self.commission.id,
            default_mode='split'
        ).create({'payment_method': 'transfer'})

        line_ufredo = wizard.line_ids.filtered(lambda l: l.user_id == self.user_advisor1)
        line_camila = wizard.line_ids.filtered(lambda l: l.user_id == self.user_advisor2)

        line_ufredo.invoice = 'without'
        line_ufredo._onchange_invoice()
        self.assertAlmostEqual(line_ufredo.amount_vat, 0.0)
        self.assertAlmostEqual(line_ufredo.amount_total, 183.60)

        line_camila.invoice = 'with'
        line_camila._onchange_invoice()
        self.assertAlmostEqual(line_camila.amount_vat, 137.70, places=2)
        self.assertAlmostEqual(line_camila.amount_total, 1055.70, places=2)

        # Confirmar y pagar
        wizard.action_confirm()

        self.assertEqual(self.commission.state, 'split')
        children = self.commission.child_commission_ids
        self.assertEqual(len(children), 4)
        for c in children:
            self.assertEqual(c.state, 'paid')
            if c.user_id == self.user_advisor1:
                self.assertEqual(c.has_invoice, 'without')
            elif c.user_id == self.user_advisor2:
                self.assertEqual(c.has_invoice, 'with')

    def test_modify_percentages_in_split_state_syncs_children(self):
        """Si la comisión está repartida (sin pagar), modificar los porcentajes
        en split_line_ids debe actualizar el monto de las comisiones hijas."""
        # Repartir sin pagar
        self.commission.with_context(estate_split_only=True).action_split_into_commissions()
        self.assertEqual(self.commission.state, 'split')

        capture_split = self.commission.split_line_ids.filtered(lambda l: l.role == 'capture')
        # Cambiar porcentaje de captación de 8% a 10%
        capture_split.write({'percentage': 10.0})

        child_capture = self.commission.child_commission_ids.filtered(lambda c: c.role == 'capture')
        # 10% de 2295 = 229.50
        self.assertAlmostEqual(child_capture.amount, 229.50, places=2)
        self.assertAlmostEqual(child_capture.role_pct, 10.0)

    def test_payout_registra_pagos_en_facturacion(self):
        """Los tres tipos dejan un pago en Facturación: 15% y 0% con factura de
        proveedor; sin factura, un pago directo al asesor."""
        wizard = self.env['estate.commission.payout.wizard'].with_context(
            default_commission_id=self.commission.id,
            default_mode='split'
        ).create({'payment_method': 'transfer', 'payment_reference': 'TRF-1'})
        wizard.line_ids.filtered(lambda l: l.user_id == self.user_advisor1).invoice = 'without'
        line_camila = wizard.line_ids.filtered(lambda l: l.user_id == self.user_advisor2)
        line_camila.invoice = 'with_0'
        self.assertAlmostEqual(line_camila.amount_vat, 0.0)
        self.assertAlmostEqual(line_camila.amount_total, 918.0, places=2)
        wizard.action_confirm()

        for child in self.commission.child_commission_ids:
            self.assertEqual(child.state, 'paid')
            pay = child.payment_id
            self.assertTrue(pay, 'Cada asesor debe tener su pago contable')
            self.assertEqual(pay.estate_kind, 'advisor')
            self.assertEqual(pay.estate_invoice_mode, child.has_invoice)
            self.assertEqual(pay.partner_id, child.user_id.partner_id)
            hermanas = self.commission.child_commission_ids.filtered(lambda c: c.payment_id == pay)
            self.assertAlmostEqual(pay.amount, sum(hermanas.mapped('amount_total')), places=2)
            if child.has_invoice == 'without':
                self.assertFalse(child.invoice_id)
            else:
                self.assertEqual(child.invoice_id.state, 'posted')
                self.assertAlmostEqual(child.invoice_id.amount_tax, 0.0)

        # El comprobante se imprime para cada asesor
        pdf, _ = self.env['ir.actions.report']._render_qweb_html(
            'estate_management.action_report_commission_receipt',
            self.commission.child_commission_ids.ids)
        self.assertIn(b'Recib', pdf)

    def test_revertir_pago_anula_lo_contable(self):
        com = self.env['estate.commission'].create({
            'property_id': self.property.id,
            'user_id': self.user_advisor1.id,
            'amount': 500.0,
            'state': 'approved',
            'has_invoice': 'with',
            'payment_method': 'cash',
        })
        com.action_register_payment()
        self.assertAlmostEqual(com.amount_total, 575.0, places=2)
        pay, bill = com.payment_id, com.invoice_id
        self.assertEqual(bill.payment_state in ('paid', 'in_payment'), True)
        com.action_reset_to_approved()
        self.assertEqual(com.state, 'approved')
        self.assertEqual(pay.state, 'canceled')
        self.assertEqual(bill.state, 'cancel')

    def test_cada_asesor_con_su_forma_de_pago_y_un_solo_pago(self):
        """Cada recuadro guarda su propia forma de pago, fecha y referencia, y
        las tres comisiones de Camila se pagan con un solo pago."""
        wizard = self.env['estate.commission.payout.wizard'].with_context(
            default_commission_id=self.commission.id,
            default_mode='split'
        ).create({})
        ufredo = wizard.line_ids.filtered(lambda l: l.user_id == self.user_advisor1)
        camila = wizard.line_ids.filtered(lambda l: l.user_id == self.user_advisor2)
        ufredo.write({'payment_method': 'cash', 'payment_reference': 'REC-1', 'invoice': 'without'})
        camila.write({'payment_method': 'transfer', 'payment_reference': 'TRF-2', 'invoice': 'with'})
        wizard.action_confirm()

        hijos = self.commission.child_commission_ids
        de_ufredo = hijos.filtered(lambda c: c.user_id == self.user_advisor1)
        de_camila = hijos.filtered(lambda c: c.user_id == self.user_advisor2)
        self.assertEqual(de_ufredo.payment_method, 'cash')
        self.assertEqual(de_ufredo.payment_reference, 'REC-1')
        self.assertEqual(set(de_camila.mapped('payment_method')), {'transfer'})
        self.assertEqual(len(de_camila.payment_id), 1, 'Camila recibe un solo pago')
        self.assertEqual(len(de_camila.invoice_id), 1, 'y una sola factura con una línea por rol')
        self.assertEqual(len(de_camila.invoice_id.invoice_line_ids), 3)
        self.assertAlmostEqual(de_camila.payment_id.amount, 1055.70, places=2)
        self.assertAlmostEqual(de_ufredo.payment_id.amount, 183.60, places=2)

        # Revertir una comisión de Camila revierte su pago completo
        de_camila[:1].action_reset_to_approved()
        self.assertEqual(set(de_camila.mapped('state')), {'approved'})
