from datetime import date

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'estate_document_contract')
class TestContractDocumentAutoCreation(TransactionCase):
    """Verifica que al activar un contrato se creen automáticamente los documentos placeholder."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Contract = cls.env['estate.contract']
        cls.Doc = cls.env['estate.document']
        cls.partner = cls.env['res.partner'].create({'name': 'Cliente Auto Doc'})
        cls.prop_type = cls.env['estate.property.type'].create({'name': 'Tipo Auto Doc'})
        cls.property = cls.env['estate.property'].create({
            'title': 'Casa Auto Doc',
            'price': 80000.0,
            'property_type_id': cls.prop_type.id,
        })

    def _make_contract(self, **overrides):
        vals = {
            'property_id': self.property.id,
            'partner_id': self.partner.id,
            'date_start': date.today(),
            'amount': 80000.0,
            'contract_type': 'sale',
        }
        vals.update(overrides)
        return self.Contract.create(vals)

    def test_activate_creates_placeholder_documents(self):
        contract = self._make_contract()
        # Antes de activar: 0 documentos
        self.assertEqual(len(contract.document_ids), 0)
        # Activar
        contract.action_activate()
        # Debería crear 2 placeholders: 'contract_signed' y 'client_id_card'
        self.assertEqual(len(contract.document_ids), 2)
        codes = contract.document_ids.mapped('type_id.code')
        self.assertIn('contract_signed', codes)
        self.assertIn('client_id_card', codes)

    def test_placeholders_start_in_pending_state(self):
        contract = self._make_contract()
        contract.action_activate()
        for doc in contract.document_ids:
            self.assertEqual(doc.state, 'pending')
            self.assertFalse(doc.file)

    def test_no_duplicates_on_repeated_activation(self):
        """Si ya hay documentos vinculados, no se crean otra vez al re-llamar la lógica.
        El parent action_activate bloquea segunda activación (state ya activo), así que
        verificamos directamente la guarda interna de no-duplicación."""
        contract = self._make_contract()
        contract.action_activate()
        n_first = len(contract.document_ids)
        # Reset a draft sin ejecutar otras acciones, luego volver a activar
        contract.write({'state': 'draft'})
        # Re-activar: no debe crear duplicados
        contract.action_activate()
        n_second = len(contract.document_ids)
        self.assertEqual(n_first, n_second,
            'No se deben duplicar placeholders en activaciones repetidas')

    def test_contract_id_set_correctly(self):
        contract = self._make_contract()
        contract.action_activate()
        for doc in contract.document_ids:
            self.assertEqual(doc.contract_id, contract)
            self.assertEqual(doc.property_id, self.property)
            self.assertEqual(doc.partner_id, self.partner)

    def test_full_folder_view_includes_contract_docs(self):
        """La vista 'Carpeta completa' del cliente debe incluir docs del contrato."""
        contract = self._make_contract()
        contract.action_activate()
        action = self.partner.action_view_full_folder()
        # El domain debe permitir filtrar por contract_id del cliente
        domain = action['domain']
        # Construir el queryset y verificar que los docs aparecen
        docs = self.Doc.search(domain)
        for doc in contract.document_ids:
            self.assertIn(doc, docs,
                'La carpeta completa del partner debe incluir documentos del contrato')
