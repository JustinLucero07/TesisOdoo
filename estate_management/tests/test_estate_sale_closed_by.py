# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'estate_sale_closed_by')
class TestEstateSaleClosedBy(TransactionCase):
    """Venta cerrada por Colega o con Pago a terceros / referido."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Partner = cls.env['res.partner']
        cls.owner = Partner.create({'name': 'Dueño Test'})
        cls.buyer = Partner.create({'name': 'Comprador Test'})
        cls.colleague = Partner.create({'name': 'Colega Test'})
        cls.referral = Partner.create({'name': 'Referido Test'})
        cls.advisor = cls.env['res.users'].create({'name': 'Asesor Venta', 'login': 'venta@test.com'})
        ptype = cls.env['estate.property.type'].create({'name': 'Casa Test'})
        cls.prop = cls.env['estate.property'].create({
            'title': 'Casa para cerrar', 'price': 140000.0, 'commission_percentage': 3.0,
            'property_type_id': ptype.id, 'owner_id': cls.owner.id, 'state': 'available',
            'user_id': cls.advisor.id,
        })

    def _sell(self, **vals):
        wiz = self.env['estate.sale.wizard'].with_context(active_id=self.prop.id).create(dict({
            'property_id': self.prop.id, 'buyer_id': self.buyer.id, 'sale_price': 140000.0,
            'commission_pct': 3.0, 'user_id': self.advisor.id,
        }, **vals))
        commission = wiz.commission_amount
        wiz.action_confirm_sale()
        order = self.env['sale.order'].search([('property_id', '=', self.prop.id)], limit=1)
        return wiz, commission, order

    def _collect(self, order, **vals):
        self.env['estate.sale.collect.wizard'].with_context(
            active_model='sale.order', active_ids=order.ids).create(dict({
                'invoice': 'without', 'method': 'transfer'}, **vals)).action_confirm()

    def test_referido_resta_del_precio_y_se_paga_al_cobrar(self):
        _wiz, commission, order = self._sell(
            sold_by='referral', deal_partner_id=self.referral.id, deal_partner_amount=1000.0)
        # 140.000 − 1.000 = 139.000 × 3% = 4.170
        self.assertAlmostEqual(commission, 4170.0, places=2)
        self.assertEqual(self.prop.deal_partner_id, self.referral)
        coms = self.env['estate.commission'].search([('property_id', '=', self.prop.id)])
        self.assertAlmostEqual(sum(coms.mapped('amount')), 4170.0, places=2)
        self.assertEqual(order.estate_referral_partner_id, self.referral)
        self._collect(order)
        third = order.estate_third_payment_ids
        self.assertEqual(third.partner_id, self.referral)
        self.assertAlmostEqual(third.amount, 1000.0)
        self.assertAlmostEqual(order.estate_collection_payment_ids.amount, 4170.0, places=2)

    def test_colega_reparte_como_aliado(self):
        _wiz, commission, order = self._sell(
            sold_by='colleague', deal_partner_id=self.colleague.id, our_share_pct=50.0)
        self.assertAlmostEqual(commission, 4200.0, places=2)
        # Los asesores cobran sobre nuestra parte, como con un aliado
        com = self.env['estate.commission'].search([('property_id', '=', self.prop.id)])
        self.assertAlmostEqual(sum(com.mapped('amount')), 2100.0, places=2)
        self.assertTrue(order.estate_is_allied)
        self.assertEqual(order.estate_allied_agency_id, self.colleague)
        self._collect(order, collect_full=True)
        self.assertAlmostEqual(order.estate_collection_payment_ids.amount, 4200.0, places=2)
        third = order.estate_third_payment_ids
        self.assertEqual(third.partner_id, self.colleague)
        self.assertAlmostEqual(third.amount, 2100.0, places=2)

    def test_nuestra_parte_con_colega_en_la_ventana(self):
        wiz = self.env['estate.sale.wizard'].with_context(active_id=self.prop.id).create({
            'property_id': self.prop.id, 'buyer_id': self.buyer.id, 'sale_price': 163000.0,
            'commission_pct': 3.0, 'sold_by': 'colleague', 'deal_partner_id': self.colleague.id,
            'our_share_pct': 50.0})
        self.assertAlmostEqual(wiz.commission_amount, 4890.0, places=2)
        self.assertAlmostEqual(wiz.our_commission_amount, 2445.0, places=2)

    def test_modificar_negocio_cerrado_actualiza_venta_y_comision(self):
        _wiz, commission, order = self._sell()
        self.assertAlmostEqual(commission, 4200.0, places=2)

        def edit(**vals):
            wiz = self.env['estate.sale.wizard'].with_context(
                active_id=self.prop.id, edit_deal_mode=True).create(dict({
                    'property_id': self.prop.id, 'buyer_id': self.buyer.id,
                    'commission_pct': 3.0, 'user_id': self.advisor.id}, **vals))
            wiz.action_confirm_sale()

        # Precio corregido: 139.000 × 3% = 4.170
        edit(sale_price=139000.0)
        self.assertAlmostEqual(order.amount_untaxed, 4170.0, places=2)
        coms = self.env['estate.commission'].search([
            ('property_id', '=', self.prop.id), ('parent_commission_id', '=', False)])
        self.assertAlmostEqual(sum(coms.mapped('amount')), 4170.0, places=2)

        # Ahora resulta que lo vendió un colega (50%): la venta sigue cobrando
        # el total y los asesores cobran sobre nuestra parte.
        edit(sale_price=139000.0, sold_by='colleague', deal_partner_id=self.colleague.id,
             our_share_pct=50.0)
        self.assertAlmostEqual(order.amount_untaxed, 4170.0, places=2)
        self.assertAlmostEqual(sum(coms.mapped('amount')), 2085.0, places=2)
        self.assertTrue(order.estate_is_allied)
        wiz = self.env['estate.sale.collect.wizard'].with_context(
            active_model='sale.order', active_ids=order.ids).create({'invoice': 'without'})
        self.assertAlmostEqual(wiz.amount_total, 2085.0, places=2)
