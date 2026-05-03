from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'estate_crm_negotiation')
class TestNegotiationStrategy(TransactionCase):
    """Tests del compute _compute_negotiation_strategy basado en match_percentage."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Lead = cls.env['crm.lead']
        cls.Property = cls.env['estate.property']
        cls.prop_type = cls.env['estate.property.type'].create({'name': 'Tipo Negotiation'})

    def _make_lead_with_match(self, match_pct):
        """Crea un lead con propiedad/budget tales que match_percentage = match_pct (aprox)."""
        prop = self.Property.create({'title': 'P', 'price': 100000.0})
        # Para forzar el match, ajustar el budget según la regla:
        # match alto = budget cubre precio, ciudad y tipo NO definidos.
        # Usamos sólo el componente de presupuesto (50 pts max) para simplificar el test.
        if match_pct >= 90:
            budget = 100000.0
            type_id = False
            city = ''
        elif match_pct >= 60:
            budget = 75000.0  # ratio 0.75 = 25 pts solo
            # Aquí sumamos 0 de tipo+ciudad+habs si no tiene preferencias
            # En realidad este test verifica el resultado del compute, no recrea el match
            type_id = False
            city = ''
        else:
            budget = 10000.0
            type_id = False
            city = ''
        return self.Lead.create({
            'name': f'Test {match_pct}',
            'target_property_id': prop.id,
            'client_budget': budget,
            'preferred_city': city,
        })

    def test_easy_when_match_above_90(self):
        prop = self.Property.create({
            'title': 'Prop Easy',
            'price': 100000.0,
            'city': 'Cuenca',
            'bedrooms': 3,
            'property_type_id': self.prop_type.id,
        })
        lead = self.Lead.create({
            'name': 'Lead Easy',
            'target_property_id': prop.id,
            'client_budget': 100000.0,  # 50
            'preferred_city': 'Cuenca',  # 20
            'preferred_bedrooms': 3,     # 10
            'preferred_property_type_id': self.prop_type.id,  # 20
        })
        # Total = 100
        self.assertGreaterEqual(lead.match_percentage, 90)
        self.assertEqual(lead.closing_difficulty, 'easy')
        self.assertIn('Cierre inmediato', lead.smart_negotiation_tips)

    def test_moderate_when_match_60_89(self):
        prop = self.Property.create({
            'title': 'Prop Mod', 'price': 100000.0, 'city': 'Quito',
            'property_type_id': self.prop_type.id,
        })
        lead = self.Lead.create({
            'name': 'Lead Moderate',
            'target_property_id': prop.id,
            'client_budget': 100000.0,  # 50
            'preferred_city': 'Quito',  # 20
            # Sin tipo, sin habitaciones → total 70
        })
        self.assertGreaterEqual(lead.match_percentage, 60)
        self.assertLess(lead.match_percentage, 90)
        self.assertEqual(lead.closing_difficulty, 'moderate')
        self.assertIn('financiamiento', lead.smart_negotiation_tips)

    def test_hard_when_match_below_60(self):
        prop = self.Property.create({
            'title': 'Prop Hard', 'price': 100000.0,
            'property_type_id': self.prop_type.id,
        })
        lead = self.Lead.create({
            'name': 'Lead Hard',
            'target_property_id': prop.id,
            'client_budget': 30000.0,  # ratio 0.3 → 0 pts
            # Sin más bonos → 0
        })
        self.assertLess(lead.match_percentage, 60)
        self.assertEqual(lead.closing_difficulty, 'hard')
        self.assertIn('seguimiento intensivo', lead.smart_negotiation_tips)

    def test_stored_field_persists(self):
        """closing_difficulty tiene store=True, debe persistir tras refresh."""
        prop = self.Property.create({
            'title': 'P', 'price': 100000.0,
            'property_type_id': self.prop_type.id,
        })
        lead = self.Lead.create({
            'name': 'L',
            'target_property_id': prop.id,
            'client_budget': 100000.0,
        })
        original = lead.closing_difficulty
        lead.invalidate_recordset(['closing_difficulty'])
        # Tras invalidar la cache, sigue accesible (vienen de DB)
        self.assertEqual(lead.closing_difficulty, original)
