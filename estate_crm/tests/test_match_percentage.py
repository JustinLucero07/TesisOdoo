from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'estate_crm_match')
class TestMatchPercentage(TransactionCase):
    """Tests del compute _compute_match_percentage del crm.lead.

    Reglas (50+20+20+10 = 100 puntos máximo):
        - Presupuesto: 50/40/25/10 según ratio (>=1.0 / >=0.90 / >=0.75 / >=0.50)
        - Tipo propiedad: 20 si coincide
        - Ciudad: 20 si coincide
        - Habitaciones: 10 si prop>=preferred, 5 si prop==preferred-1
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Property = cls.env['estate.property']
        cls.Lead = cls.env['crm.lead']
        cls.PropType = cls.env['estate.property.type']

        cls.casa_type = cls.PropType.create({'name': 'Casa Match Test'})
        cls.depto_type = cls.PropType.create({'name': 'Depto Match Test'})

    def _make_property(self, **overrides):
        vals = {
            'title': 'Prop Match',
            'price': 100000.0,
            'city': 'Cuenca',
            'bedrooms': 3,
            'property_type_id': self.casa_type.id,
        }
        vals.update(overrides)
        return self.Property.create(vals)

    def _make_lead(self, prop, **overrides):
        vals = {
            'name': 'Lead Match Test',
            'target_property_id': prop.id,
            'client_budget': 100000.0,
            'preferred_city': 'Cuenca',
            'preferred_bedrooms': 3,
            'preferred_property_type_id': self.casa_type.id,
        }
        vals.update(overrides)
        return self.Lead.create(vals)

    def test_perfect_match_100(self):
        prop = self._make_property()
        lead = self._make_lead(prop)
        self.assertEqual(lead.match_percentage, 100)

    def test_no_property_zero(self):
        lead = self.Lead.create({
            'name': 'Sin propiedad',
            'client_budget': 100000.0,
        })
        self.assertEqual(lead.match_percentage, 0)

    def test_no_budget_zero(self):
        prop = self._make_property()
        lead = self.Lead.create({
            'name': 'Sin presupuesto',
            'target_property_id': prop.id,
        })
        self.assertEqual(lead.match_percentage, 0)

    def test_budget_ratio_90_pct(self):
        # 50+20+20+10 = 100 → cambia presupuesto: 90k vs 100k = ratio 0.9 → 40+20+20+10 = 90
        prop = self._make_property(price=100000.0)
        lead = self._make_lead(prop, client_budget=90000.0)
        self.assertEqual(lead.match_percentage, 90)

    def test_budget_ratio_75_pct(self):
        # ratio 0.75 → 25 pts presupuesto + 50 otros = 75
        prop = self._make_property(price=100000.0)
        lead = self._make_lead(prop, client_budget=75000.0)
        self.assertEqual(lead.match_percentage, 75)

    def test_budget_ratio_50_pct(self):
        # ratio 0.5 → 10 pts presupuesto + 50 otros = 60
        prop = self._make_property(price=100000.0)
        lead = self._make_lead(prop, client_budget=50000.0)
        self.assertEqual(lead.match_percentage, 60)

    def test_budget_too_low_zero_score(self):
        # ratio < 0.5 → 0 pts presupuesto pero conserva los otros 50
        prop = self._make_property(price=100000.0)
        lead = self._make_lead(prop, client_budget=10000.0)
        self.assertEqual(lead.match_percentage, 50)

    def test_property_type_mismatch(self):
        prop = self._make_property(property_type_id=self.depto_type.id)
        lead = self._make_lead(prop)  # prefers casa_type
        # 50 (presupuesto) + 0 (tipo) + 20 (ciudad) + 10 (hab) = 80
        self.assertEqual(lead.match_percentage, 80)

    def test_city_mismatch(self):
        prop = self._make_property(city='Quito')
        lead = self._make_lead(prop, preferred_city='Cuenca')
        # 50 + 20 + 0 (ciudad) + 10 = 80
        self.assertEqual(lead.match_percentage, 80)

    def test_bedrooms_one_less(self):
        prop = self._make_property(bedrooms=2)
        lead = self._make_lead(prop, preferred_bedrooms=3)
        # 50 + 20 + 20 + 5 (1 menos) = 95
        self.assertEqual(lead.match_percentage, 95)

    def test_bedrooms_more_than_required(self):
        prop = self._make_property(bedrooms=4)
        lead = self._make_lead(prop, preferred_bedrooms=3)
        # 50 + 20 + 20 + 10 (>=) = 100
        self.assertEqual(lead.match_percentage, 100)

    def test_bedrooms_two_less_no_score(self):
        prop = self._make_property(bedrooms=1)
        lead = self._make_lead(prop, preferred_bedrooms=3)
        # 50 + 20 + 20 + 0 = 90
        self.assertEqual(lead.match_percentage, 90)
