from datetime import date, timedelta

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'estate_contract')
class TestEstateContractConstraints(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Contract = cls.env['estate.contract']
        cls.partner = cls.env['res.partner'].create({'name': 'Cliente Test'})
        cls.prop_type = cls.env['estate.property.type'].create({'name': 'Tipo Contract'})
        cls.property = cls.env['estate.property'].create({
            'title': 'Casa Contrato',
            'price': 80000.0,
            'property_type_id': cls.prop_type.id,
        })

    def _make(self, **overrides):
        vals = {
            'property_id': self.property.id,
            'partner_id': self.partner.id,
            'date_start': date.today(),
            'amount': 80000.0,
            'contract_type': 'sale',
        }
        vals.update(overrides)
        return self.Contract.create(vals)

    def test_negative_amount_raises(self):
        with self.assertRaises(UserError):
            self._make(amount=-1.0)

    def test_zero_amount_passes(self):
        # 0 está permitido (un contrato puede no tener amount asignado)
        c = self._make(amount=0.0)
        self.assertEqual(c.amount, 0.0)

    def test_positive_amount_passes(self):
        c = self._make(amount=50000.0)
        self.assertEqual(c.amount, 50000.0)

    def test_end_before_start_raises(self):
        start = date.today()
        end = start - timedelta(days=10)
        with self.assertRaises(UserError):
            self._make(date_start=start, date_end=end)

    def test_end_equal_to_start_passes(self):
        d = date.today()
        c = self._make(date_start=d, date_end=d)
        self.assertEqual(c.date_end, d)

    def test_end_after_start_passes(self):
        start = date.today()
        end = start + timedelta(days=365)
        c = self._make(date_start=start, date_end=end)
        self.assertEqual(c.date_end, end)
