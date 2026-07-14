from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'estate_crm_gates')
class TestStageGates(TransactionCase):
    """Compuertas de acciones del CRM según la etapa (gate_* por XML id).

    Embudo comercial: Recepción(1) · Seguimiento(2) · Con Necesidad(3) ·
    Vendedores(4) · En Proceso Cierre(5) · Cierre(6)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.lead = cls.env['crm.lead'].create({'name': 'Lead Compuertas Test'})

    def _stage(self, xmlid):
        return self.env.ref(xmlid)

    def test_etapa_recepcion(self):
        self.lead.stage_id = self._stage('estate_crm.stage_lead1_estate_nuevo')
        self.lead.invalidate_recordset()
        self.assertTrue(self.lead.gate_capture, "En Recepción se permite captación")
        self.assertFalse(self.lead.gate_offer, "Aún no se puede ofertar")
        self.assertFalse(self.lead.gate_contract, "Aún no se puede contratar")

    def test_etapa_seguimiento(self):
        self.lead.stage_id = self._stage('estate_crm.stage_lead3b_estate_seguimiento')
        self.lead.invalidate_recordset()
        self.assertTrue(self.lead.gate_capture, "Hasta Con Necesidad sigue habilitada la captación")
        self.assertTrue(self.lead.gate_offer, "En Seguimiento ya se puede ofertar")
        self.assertTrue(self.lead.gate_reserve, "En Seguimiento ya se puede reservar")
        self.assertFalse(self.lead.gate_contract, "Aún no se puede contratar")

    def test_etapa_en_proceso_cierre(self):
        self.lead.stage_id = self._stage('estate_crm.stage_lead4_estate_papeles')
        self.lead.invalidate_recordset()
        self.assertFalse(self.lead.gate_capture, "Ya pasó la fase de captación")
        self.assertTrue(self.lead.gate_offer, "En Proceso Cierre todavía admite ofertas")
        self.assertTrue(self.lead.gate_reserve)
        self.assertTrue(self.lead.gate_contract, "Desde En Proceso Cierre se formaliza contrato")

    def test_etapa_cierre(self):
        self.lead.stage_id = self._stage('estate_crm.stage_lead7_estate_cierre')
        self.lead.invalidate_recordset()
        self.assertFalse(self.lead.gate_offer, "Ganado: ya no se ofertan precios")
        self.assertTrue(self.lead.gate_contract, "Ganado: el contrato sigue disponible")
