import datetime

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'estate_property')
class TestEstatePropertyConstraints(TransactionCase):
    """Tests para constraints de estate.property (year_built, bottom_price, commission_split_pct)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Property = cls.env['estate.property']
        cls.prop_type = cls.env['estate.property.type'].create({'name': 'Tipo Test Property'})

    def _make(self, **overrides):
        vals = {
            'title': 'Casa Test',
            'price': 100000.0,
            'property_type_id': self.prop_type.id,
        }
        vals.update(overrides)
        return self.Property.create(vals)

    def test_year_built_future_raises(self):
        future = datetime.date.today().year + 5
        with self.assertRaises(UserError):
            self._make(year_built=future)

    def test_year_built_too_old_raises(self):
        with self.assertRaises(UserError):
            self._make(year_built=1500)

    def test_year_built_valid_passes(self):
        prop = self._make(year_built=2020)
        self.assertEqual(prop.year_built, 2020)

    def test_year_built_zero_passes(self):
        # 0 = no establecido, no debe disparar el constraint
        prop = self._make(year_built=0)
        self.assertEqual(prop.year_built, 0)

    def test_bottom_price_higher_than_price_raises(self):
        with self.assertRaises(UserError):
            self._make(price=100000.0, bottom_price=110000.0)

    def test_bottom_price_equal_to_price_raises(self):
        with self.assertRaises(UserError):
            self._make(price=100000.0, bottom_price=100000.0)

    def test_bottom_price_lower_passes(self):
        prop = self._make(price=100000.0, bottom_price=85000.0)
        self.assertEqual(prop.bottom_price, 85000.0)

    def test_commission_split_negative_raises(self):
        with self.assertRaises(UserError):
            self._make(commission_split_pct=-5)

    def test_commission_split_over_100_raises(self):
        with self.assertRaises(UserError):
            self._make(commission_split_pct=150)

    def test_commission_split_in_range_passes(self):
        prop = self._make(commission_split_pct=50)
        self.assertEqual(prop.commission_split_pct, 50)

    def test_commission_split_boundary_0_passes(self):
        prop = self._make(commission_split_pct=0)
        self.assertEqual(prop.commission_split_pct, 0)

    def test_commission_split_boundary_100_passes(self):
        prop = self._make(commission_split_pct=100)
        self.assertEqual(prop.commission_split_pct, 100)

    def test_default_state_available(self):
        prop = self._make()
        self.assertEqual(prop.state, 'available')

    def test_indexes_exist(self):
        """Verifica que wp_post_id, fb_post_id, ig_post_id tengan índice."""
        # En PostgreSQL, los índices se crean automáticamente al sincronizar el modelo
        # Verificamos que el modelo declara index='btree_not_null' (smoke test)
        for fname in ['wp_post_id', 'fb_post_id', 'ig_post_id']:
            field = self.Property._fields.get(fname)
            if field:
                self.assertTrue(field.index, f'{fname} debe tener index activo')
