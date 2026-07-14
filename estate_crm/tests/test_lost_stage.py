# -*- coding: utf-8 -*-
"""Etapa "Perdido" VISIBLE.

Odoo de fábrica archiva el lead perdido (active=False) y por eso desaparece del
kanban: un registro archivado nunca sale en una columna. Aquí el lead perdido se
queda visible en su etapa (marcada con is_lost), pero sigue contando como
"Perdido" en filtros y reportes (won_status = 'lost')."""
from odoo.tools.safe_eval import safe_eval
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'estate_crm_lost')
class TestLostStage(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.perdido = cls.env.ref('estate_crm.stage_lead_perdido')
        cls.recepcion = cls.env.ref('estate_crm.stage_lead1_estate_nuevo')
        cls.cierre = cls.env.ref('estate_crm.stage_lead7_estate_cierre')
        cls.motivo = cls.env.ref('estate_crm.lost_reason_no_contact')

    def _lead(self, stage=None):
        return self.env['crm.lead'].create({
            'name': 'Lead Perdido Test', 'type': 'opportunity',
            'stage_id': (stage or self.recepcion).id,
        })

    def test_marcar_perdido_no_archiva_y_lo_mueve_a_la_columna(self):
        lead = self._lead()
        lead.action_set_lost(lost_reason_id=self.motivo.id)

        self.assertTrue(lead.active, "El lead perdido NO debe archivarse")
        self.assertEqual(lead.stage_id, self.perdido, "Debe quedar en la columna Perdido")
        self.assertEqual(lead.probability, 0)
        self.assertEqual(lead.lost_reason_id, self.motivo)

    def test_sigue_contando_como_perdido(self):
        """Aunque esté visible, para Odoo es 'lost' (reportes y filtros cuadran)."""
        lead = self._lead()
        lead.action_set_lost(lost_reason_id=self.motivo.id)
        self.assertEqual(lead.won_status, 'lost')

    def test_aparece_en_el_kanban_del_flujo(self):
        """La prueba de fuego: el lead perdido SÍ sale en el embudo comercial."""
        lead = self._lead()
        lead.action_set_lost(lost_reason_id=self.motivo.id)

        flujo = self.env['ir.actions.act_window']._for_xml_id('crm.crm_lead_action_pipeline')
        visibles = self.env['crm.lead'].search(safe_eval(flujo['domain']))
        self.assertIn(lead, visibles,
                      "El lead perdido debe verse en su columna del embudo")

    def test_el_filtro_perdido_lo_encuentra(self):
        lead = self._lead()
        lead.action_set_lost(lost_reason_id=self.motivo.id)
        encontrados = self.env['crm.lead'].search([('won_status', '=', 'lost')])
        self.assertIn(lead, encontrados)

    def test_ganar_un_lead_perdido_lo_saca_de_la_columna(self):
        lead = self._lead()
        lead.action_set_lost(lost_reason_id=self.motivo.id)
        self.assertEqual(lead.stage_id, self.perdido)

        lead.action_set_won()

        self.assertNotEqual(lead.stage_id, self.perdido,
                            "Al ganarlo debe salir de la columna Perdido")
        self.assertEqual(lead.won_status, 'won')

    def test_migracion_rescata_los_perdidos_archivados(self):
        """Los que quedaron archivados (escondidos) vuelven a verse."""
        lead = self._lead()
        lead.write({'active': False, 'probability': 0})
        self.assertFalse(lead.active)

        self.env['crm.lead']._migrate_lost_leads_to_stage()
        lead.invalidate_recordset()

        self.assertTrue(lead.active, "Debe dejar de estar escondido")
        self.assertEqual(lead.stage_id, self.perdido)
        self.assertEqual(lead.won_status, 'lost', "Sigue siendo un perdido")
