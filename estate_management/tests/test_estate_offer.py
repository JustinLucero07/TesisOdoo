from datetime import date, timedelta

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'estate_offer')
class TestEstateOfferConstraints(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Offer = cls.env['estate.property.offer']
        cls.partner = cls.env['res.partner'].create({'name': 'Comprador Test'})
        cls.prop_type = cls.env['estate.property.type'].create({'name': 'Tipo Offer'})
        cls.property = cls.env['estate.property'].create({
            'title': 'Casa Ofertas',
            'price': 60000.0,
            'property_type_id': cls.prop_type.id,
        })

    def _make(self, **overrides):
        vals = {
            'property_id': self.property.id,
            'partner_id': self.partner.id,
            'offer_amount': 55000.0,
            'date': date.today(),
        }
        vals.update(overrides)
        return self.Offer.create(vals)

    def test_zero_amount_raises(self):
        with self.assertRaises(UserError):
            self._make(offer_amount=0.0)

    def test_negative_amount_raises(self):
        with self.assertRaises(UserError):
            self._make(offer_amount=-1000.0)

    def test_positive_amount_passes(self):
        o = self._make(offer_amount=58000.0)
        self.assertEqual(o.offer_amount, 58000.0)

    def test_expiry_before_offer_date_raises(self):
        d = date.today()
        with self.assertRaises(UserError):
            self._make(date=d, date_expiry=d - timedelta(days=1))

    def test_expiry_equal_to_offer_date_passes(self):
        d = date.today()
        o = self._make(date=d, date_expiry=d)
        self.assertEqual(o.date_expiry, d)

    def test_expiry_after_offer_date_passes(self):
        d = date.today()
        o = self._make(date=d, date_expiry=d + timedelta(days=15))
        self.assertEqual(o.date_expiry, d + timedelta(days=15))
