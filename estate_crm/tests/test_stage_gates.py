from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'estate_crm_gates')
class TestStageGates(TransactionCase):
    """Compuertas de acciones del CRM según la etapa (gate_* por XML id)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.lead = cls.env['crm.lead'].create({'name': 'Lead Compuertas Test'})

    def _stage(self, xmlid):
        return self.env.ref(xmlid)

    def test_etapa_inicial_captacion(self):
        self.lead.stage_id = self._stage('estate_crm.stage_lead1_estate_nuevo')
        self.lead.invalidate_recordset()
        self.assertTrue(self.lead.gate_capture, "En etapa inicial se permite captación")
        self.assertFalse(self.lead.gate_offer, "Aún no se puede ofertar")
        self.assertFalse(self.lead.gate_contract, "Aún no se puede contratar")

    def test_etapa_visita_negociacion(self):
        self.lead.stage_id = self._stage('estate_crm.stage_lead3_estate_visita')
        self.lead.invalidate_recordset()
        self.assertFalse(self.lead.gate_capture)
        self.assertTrue(self.lead.gate_offer, "En Visita se puede crear oferta")
        self.assertTrue(self.lead.gate_reserve, "En Visita se puede reservar")
        self.assertFalse(self.lead.gate_contract)

    def test_etapa_cierre_contrato(self):
        self.lead.stage_id = self._stage('estate_crm.stage_lead4_estate_papeles')
        self.lead.invalidate_recordset()
        self.assertFalse(self.lead.gate_offer, "En Papeles ya no se ofertan precios")
        self.assertTrue(self.lead.gate_reserve)
        self.assertTrue(self.lead.gate_contract, "Desde Papeles se puede formalizar contrato")
