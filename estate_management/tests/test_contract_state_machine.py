from datetime import date, timedelta

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'estate_contract_states')
class TestContractStateMachine(TransactionCase):
    """Tests de la state machine ampliada del contrato:
    draft → active → suspended → active → renewing → renewed
                  → expired → renewing
                  → cancelled
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Contract = cls.env['estate.contract']
        cls.partner = cls.env['res.partner'].create({'name': 'Cliente Estados'})
        cls.prop_type = cls.env['estate.property.type'].create({'name': 'Tipo Estados'})
        cls.property = cls.env['estate.property'].create({
            'title': 'Casa Estados',
            'price': 80000.0,
            'property_type_id': cls.prop_type.id,
        })

    def _make(self, **overrides):
        vals = {
            'property_id': self.property.id,
            'partner_id': self.partner.id,
            'date_start': date.today(),
            'date_end': date.today() + timedelta(days=365),
            'amount': 80000.0,
            'contract_type': 'sale',
        }
        vals.update(overrides)
        return self.Contract.create(vals)

    def test_default_state_is_draft(self):
        c = self._make()
        self.assertEqual(c.state, 'draft')

    def test_draft_to_active(self):
        c = self._make()
        c.action_activate()
        self.assertEqual(c.state, 'active')

    def test_active_to_suspended_and_back(self):
        c = self._make()
        c.action_activate()
        c.action_suspend()
        self.assertEqual(c.state, 'suspended')
        c.action_resume_active()
        self.assertEqual(c.state, 'active')

    def test_active_to_renewing(self):
        c = self._make()
        c.action_activate()
        c.action_start_renewal()
        self.assertEqual(c.state, 'renewing')

    def test_create_renewal_creates_child_contract(self):
        c = self._make()
        c.action_activate()
        c.action_start_renewal()
        result = c.action_create_renewal()
        self.assertEqual(c.state, 'renewed')
        # El resultado abre el contrato hijo
        new_id = result['res_id']
        new_contract = self.Contract.browse(new_id)
        self.assertEqual(new_contract.state, 'draft')
        self.assertEqual(new_contract.parent_contract_id, c)
        self.assertIn(new_contract, c.child_contract_ids)

    def test_invalid_transition_raises(self):
        c = self._make()
        # draft → expired NO es válido (debe pasar por active)
        with self.assertRaises(UserError):
            c.action_set_expired()

    def test_suspended_can_be_cancelled(self):
        c = self._make()
        c.action_activate()
        c.action_suspend()
        c.action_cancel()
        self.assertEqual(c.state, 'cancelled')

    def test_cancelled_can_be_reset_to_draft(self):
        c = self._make()
        c.action_activate()
        c.action_cancel()
        c.action_reset_draft()
        self.assertEqual(c.state, 'draft')

    def test_renewed_is_terminal(self):
        c = self._make()
        c.action_activate()
        c.action_start_renewal()
        c.action_create_renewal()
        # Estado renewed no permite ninguna transición
        self.assertEqual(c.state, 'renewed')
        with self.assertRaises(UserError):
            c.action_activate()

    def test_view_offer_without_offer_raises(self):
        c = self._make()
        with self.assertRaises(UserError):
            c.action_view_offer()

    def test_view_payments_returns_action(self):
        c = self._make()
        action = c.action_view_payments()
        self.assertEqual(action['res_model'], 'estate.payment')
        self.assertEqual(action['domain'], [('contract_id', '=', c.id)])
