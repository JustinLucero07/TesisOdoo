from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'estate_phone')
class TestPhoneMixin(TransactionCase):
    """Tests para estate.phone.mixin._clean_phone()."""

    def test_local_with_leading_zero(self):
        # 0987654321 → 593987654321
        result = self.env['estate.phone.mixin']._clean_phone('0987654321')
        self.assertEqual(result, '593987654321')

    def test_already_international_with_plus(self):
        # +593987654321 → 593987654321
        result = self.env['estate.phone.mixin']._clean_phone('+593987654321')
        self.assertEqual(result, '593987654321')

    def test_with_spaces_and_dashes(self):
        # +593 98-765 4321 → 593987654321
        result = self.env['estate.phone.mixin']._clean_phone('+593 98-765 4321')
        self.assertEqual(result, '593987654321')

    def test_with_parentheses(self):
        # (098) 765-4321 → 593987654321
        result = self.env['estate.phone.mixin']._clean_phone('(098) 765-4321')
        self.assertEqual(result, '593987654321')

    def test_short_number_prepends_country_code(self):
        # 987654321 (sin 0 inicial, no empieza con 593) → 593987654321
        result = self.env['estate.phone.mixin']._clean_phone('987654321')
        self.assertEqual(result, '593987654321')

    def test_empty_string(self):
        result = self.env['estate.phone.mixin']._clean_phone('')
        self.assertEqual(result, '')

    def test_none(self):
        result = self.env['estate.phone.mixin']._clean_phone(None)
        self.assertEqual(result, '')

    def test_mixin_available_on_property(self):
        """estate.property debe tener _clean_phone heredado del mixin."""
        prop_type = self.env['estate.property.type'].create({'name': 'Tipo Mixin Test'})
        prop = self.env['estate.property'].create({
            'title': 'Test Property',
            'price': 50000,
            'property_type_id': prop_type.id,
        })
        self.assertEqual(prop._clean_phone('0987654321'), '593987654321')
