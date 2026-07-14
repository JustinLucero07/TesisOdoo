# -*- coding: utf-8 -*-
"""Limpieza de etapas ajenas al sistema.

Odoo trae de fábrica sus propias etapas (Nuevo, Calificado, Propuesta, Ganado)
SIN equipo, o sea GLOBALES. Eso rompía tres cosas en el VPS:
  1) "Ganado" (de Odoo) también es is_won -> los leads ganados caían ahí en vez
     de en "Cierre", que aparecía vacío.
  2) Al no tener equipo, salían como columnas en TODOS los embudos.
  3) Cada usuario veía etapas distintas."""
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'estate_crm_foreign_stages')
class TestForeignStages(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cierre = cls.env.ref('estate_crm.stage_lead7_estate_cierre')
        cls.recepcion = cls.env.ref('estate_crm.stage_lead1_estate_nuevo')
        cls.ventas = cls.env.ref('sales_team.team_sales_department')

    def test_borra_las_etapas_ajenas_y_reubica_sus_leads(self):
        # Simula las etapas de fábrica de Odoo: globales (sin equipo)
        ganado_odoo = self.env['crm.stage'].create({
            'name': 'Ganado (Odoo)', 'sequence': 4, 'is_won': True})
        propuesta_odoo = self.env['crm.stage'].create({
            'name': 'Propuesta (Odoo)', 'sequence': 3})
        self.assertFalse(ganado_odoo.team_ids, "Precondición: es global (sin equipo)")

        lead_ganado = self.env['crm.lead'].create({
            'name': 'Ganado en etapa ajena', 'type': 'opportunity',
            'stage_id': ganado_odoo.id})
        lead_abierto = self.env['crm.lead'].create({
            'name': 'Abierto en etapa ajena', 'type': 'opportunity',
            'stage_id': propuesta_odoo.id})

        self.env['crm.lead']._cleanup_foreign_stages()

        self.assertFalse(ganado_odoo.exists(), "La etapa ajena debe eliminarse")
        self.assertFalse(propuesta_odoo.exists())
        self.assertEqual(lead_ganado.stage_id, self.cierre,
                          "El lead ganado debe pasar a 'Cierre' (no perderse)")
        self.assertEqual(lead_abierto.stage_id, self.recepcion,
                          "El lead abierto debe pasar a 'Recepción'")

    def test_no_toca_las_etapas_del_sistema(self):
        self.env['crm.lead']._cleanup_foreign_stages()
        for xmlid in ('stage_lead1_estate_nuevo', 'stage_lead7_estate_cierre',
                      'stage_lead_perdido', 'stage_pv_sena', 'stage_pv_comision'):
            self.assertTrue(self.env.ref(f'estate_crm.{xmlid}').exists(),
                            f'{xmlid} NO debe borrarse')

    def test_solo_cierre_es_ganado_en_ventas(self):
        """Tras la limpieza, no debe quedar otra etapa 'ganada' del equipo Ventas
        que pueda robarle los leads a 'Cierre'."""
        self.env['crm.lead']._cleanup_foreign_stages()
        ganadas = self.env['crm.stage'].search([
            ('is_won', '=', True), ('team_ids', 'in', self.ventas.id)])
        self.assertEqual(ganadas, self.cierre,
                          "Solo 'Cierre' puede ser la etapa ganada del embudo comercial")

    def test_el_asesor_queda_en_el_equipo_ventas(self):
        """Sin equipo, Odoo le muestra otras etapas. Debe quedar en Ventas."""
        asesor = self.env['res.users'].create({
            'name': 'Asesor Equipo', 'login': 'asesor_equipo_test',
            'email': 'asesor_equipo@test.com',
            'group_ids': [(4, self.env.ref('estate_management.estate_group_agent').id)],
        })
        self.env['crm.team.member'].sudo().search([('user_id', '=', asesor.id)]).unlink()
        self.assertFalse(asesor.crm_team_ids, "Precondición: sin equipo")

        self.env['res.users']._ensure_sales_team_membership()
        asesor.invalidate_recordset()

        self.assertIn(self.ventas, asesor.crm_team_ids,
                      "El asesor debe quedar en el equipo Ventas para ver las etapas correctas")
