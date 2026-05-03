from datetime import date

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'estate_payment')
class TestEstatePaymentConstraints(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Payment = cls.env['estate.payment']
        cls.partner = cls.env['res.partner'].create({'name': 'Cliente Pago'})
        cls.prop_type = cls.env['estate.property.type'].create({'name': 'Tipo Payment'})
        cls.property = cls.env['estate.property'].create({
            'title': 'Casa Pagos',
            'price': 50000.0,
            'property_type_id': cls.prop_type.id,
        })
        cls.contract = cls.env['estate.contract'].create({
            'property_id': cls.property.id,
            'partner_id': cls.partner.id,
            'date_start': date.today(),
            'amount': 50000.0,
            'contract_type': 'sale',
        })

    def _make(self, **overrides):
        vals = {
            'contract_id': self.contract.id,
            'amount': 1000.0,
            'date': date.today(),
        }
        vals.update(overrides)
        return self.Payment.create(vals)

    def test_zero_amount_raises(self):
        with self.assertRaises(UserError):
            self._make(amount=0.0)

    def test_negative_amount_raises(self):
        with self.assertRaises(UserError):
            self._make(amount=-100.0)

    def test_positive_amount_passes(self):
        p = self._make(amount=500.0)
        self.assertEqual(p.amount, 500.0)
