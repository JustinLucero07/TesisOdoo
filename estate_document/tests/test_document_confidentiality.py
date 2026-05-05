import base64

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'estate_document_confidentiality')
class TestDocumentConfidentiality(TransactionCase):
    """Tests del campo confidentiality + ir.rule:
        public/internal → todos los asesores ven
        restricted → solo creador o asignado a la entidad ve
        confidential → solo manager/admin
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Doc = cls.env['estate.document']
        cls.fake_pdf = base64.b64encode(b'%PDF-1.4 conf').decode()
        cls.doctype = cls.env.ref('estate_document.doc_type_id_card')
        cls.agent_group = cls.env.ref('estate_management.estate_group_agent')
        cls.manager_group = cls.env.ref('estate_management.estate_group_manager')

        cls.base_user_group = cls.env.ref('base.group_user')

        # Crear dos agentes diferentes (con base.group_user para login)
        cls.agent_a = cls.env['res.users'].create({
            'name': 'Agent A',
            'login': 'agent_a_test',
            'group_ids': [(6, 0, [cls.base_user_group.id, cls.agent_group.id])],
        })
        cls.agent_b = cls.env['res.users'].create({
            'name': 'Agent B',
            'login': 'agent_b_test',
            'group_ids': [(6, 0, [cls.base_user_group.id, cls.agent_group.id])],
        })
        cls.manager = cls.env['res.users'].create({
            'name': 'Manager Test',
            'login': 'manager_test',
            'group_ids': [(6, 0, [cls.base_user_group.id, cls.agent_group.id, cls.manager_group.id])],
        })

    def _make_doc(self, user, confidentiality='internal'):
        return self.Doc.with_user(user).create({
            'name': f'Doc {confidentiality}',
            'type_id': self.doctype.id,
            'file': self.fake_pdf,
            'filename': 'doc.pdf',
            'confidentiality': confidentiality,
        })

    def test_internal_visible_to_other_agents(self):
        doc = self._make_doc(self.agent_a, confidentiality='internal')
        # agent_b debería verlo
        visible = self.Doc.with_user(self.agent_b).search([('id', '=', doc.id)])
        self.assertEqual(len(visible), 1)

    def test_public_visible_to_other_agents(self):
        doc = self._make_doc(self.agent_a, confidentiality='public')
        visible = self.Doc.with_user(self.agent_b).search([('id', '=', doc.id)])
        self.assertEqual(len(visible), 1)

    def test_restricted_invisible_to_other_agent(self):
        # Doc creado por agent_a, sin entidad asignada a agent_b
        doc = self._make_doc(self.agent_a, confidentiality='restricted')
        visible = self.Doc.with_user(self.agent_b).search([('id', '=', doc.id)])
        self.assertEqual(len(visible), 0,
            'agent_b NO debe ver un documento restricted creado por otro agente')

    def test_restricted_visible_to_creator(self):
        doc = self._make_doc(self.agent_a, confidentiality='restricted')
        visible = self.Doc.with_user(self.agent_a).search([('id', '=', doc.id)])
        self.assertEqual(len(visible), 1)

    def test_restricted_visible_to_manager(self):
        doc = self._make_doc(self.agent_a, confidentiality='restricted')
        visible = self.Doc.with_user(self.manager).search([('id', '=', doc.id)])
        self.assertEqual(len(visible), 1)

    def test_confidential_invisible_to_agents(self):
        # Confidential = solo manager/admin
        # Necesita ser creado como manager (los agents no pueden crear confidential? sí pueden, pero no lo verán de otros)
        doc = self.Doc.with_user(self.manager).create({
            'name': 'Confidential Doc',
            'type_id': self.doctype.id,
            'file': self.fake_pdf,
            'filename': 'c.pdf',
            'confidentiality': 'confidential',
        })
        # agent_b no debe verlo
        visible = self.Doc.with_user(self.agent_b).search([('id', '=', doc.id)])
        self.assertEqual(len(visible), 0)
        # manager sí
        visible_mgr = self.Doc.with_user(self.manager).search([('id', '=', doc.id)])
        self.assertEqual(len(visible_mgr), 1)
