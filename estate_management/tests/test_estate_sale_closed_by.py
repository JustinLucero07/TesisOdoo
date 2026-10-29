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
