import base64

from odoo.exceptions import ValidationError, UserError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'estate_document_lifecycle')
class TestDocumentLifecycle(TransactionCase):
    """Tests del ciclo de vida de estate.document: pending → received → verified → archived/rejected."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Doc = cls.env['estate.document']
        cls.DocType = cls.env['estate.document.type']
        cls.partner = cls.env['res.partner'].create({'name': 'Cliente Doc'})
        cls.prop_type = cls.env['estate.property.type'].create({'name': 'Tipo Doc Test'})
        cls.property = cls.env['estate.property'].create({
            'title': 'Casa Doc',
            'price': 50000.0,
            'property_type_id': cls.prop_type.id,
        })
        cls.fake_pdf = base64.b64encode(b'%PDF-1.4 fake content').decode()
        cls.doctype = cls.env.ref('estate_document.doc_type_id_card')
        cls.agent_group = cls.env.ref('estate_management.estate_group_agent')
        cls.manager_group = cls.env.ref('estate_management.estate_group_manager')

        cls.base_user_group = cls.env.ref('base.group_user')
        cls.manager_user = cls.env['res.users'].create({
            'name': 'Manager Lifecycle',
            'login': 'manager_lifecycle_test',
            'group_ids': [(6, 0, [cls.base_user_group.id, cls.agent_group.id, cls.manager_group.id])],
        })
        cls.agent_user = cls.env['res.users'].create({
            'name': 'Agent Lifecycle',
            'login': 'agent_lifecycle_test',
            'group_ids': [(6, 0, [cls.base_user_group.id, cls.agent_group.id])],
        })

    def _make_doc(self, **overrides):
        vals = {
            'name': 'Doc Test',
            'type_id': self.doctype.id,
            'partner_id': self.partner.id,
            'property_id': self.property.id,
            'file': self.fake_pdf,
            'filename': 'test.pdf',
        }
        vals.update(overrides)
        return self.Doc.create(vals)

    def test_default_state_is_received_when_file_present(self):
        doc = self._make_doc()
        self.assertEqual(doc.state, 'received')

    def test_placeholder_pending_no_file(self):
        doc = self._make_doc(state='pending', file=False, filename=False)
        self.assertEqual(doc.state, 'pending')
        self.assertFalse(doc.file)

    def test_uploading_file_to_placeholder_auto_marks_received(self):
        doc = self._make_doc(state='pending', file=False, filename=False)
        doc.write({'file': self.fake_pdf, 'filename': 'a.pdf'})
        self.assertEqual(doc.state, 'received')

    def test_cannot_leave_pending_without_file(self):
        doc = self._make_doc(state='pending', file=False, filename=False)
        with self.assertRaises(ValidationError):
            doc.state = 'verified'  # Va a fallar el constraint

    def test_verify_requires_manager(self):
        doc = self._make_doc()
        # Usuario que solo es agente → bloqueado
        with self.assertRaises(UserError):
            doc.with_user(self.agent_user).action_verify()

    def test_verify_sets_verified_by_and_date(self):
        doc = self._make_doc().with_user(self.manager_user)
        doc.action_verify()
        self.assertEqual(doc.state, 'verified')
        self.assertEqual(doc.verified_by, self.manager_user)
        self.assertTrue(doc.verified_date)

    def test_archive_after_verified(self):
        doc = self._make_doc().with_user(self.manager_user)
        doc.action_verify()
        doc.action_archive_doc()
        self.assertEqual(doc.state, 'archived')

    def test_reset_to_pending_clears_verification(self):
        doc = self._make_doc().with_user(self.manager_user)
        doc.action_verify()
        doc.action_reset_to_pending()
        self.assertEqual(doc.state, 'pending')
        self.assertFalse(doc.verified_by)
        self.assertFalse(doc.verified_date)

    def test_file_size_oversize_rejected(self):
        # 11 MB de basura
        big = base64.b64encode(b'X' * (11 * 1024 * 1024)).decode()
        with self.assertRaises(ValidationError):
            self._make_doc(file=big, filename='big.pdf')

    def test_invalid_extension_rejected(self):
        with self.assertRaises(ValidationError):
            self._make_doc(filename='malware.exe')

    def test_type_category_inherited(self):
        doc = self._make_doc()
        # doctype es 'id_card' que pertenece a categoría 'identity'
        self.assertEqual(doc.type_category, 'identity')
