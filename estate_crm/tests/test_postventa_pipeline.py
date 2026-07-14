from odoo.tools.safe_eval import safe_eval
from odoo.tests.common import TransactionCase, tagged

# Etapas del embudo Postventa ("Ventas Cerradas"), en orden del trámite.
POSTVENTA_XMLIDS = (
    'stage_pv_sena', 'stage_pv_financiamiento', 'stage_pv_minuta',
    'stage_pv_transferencia', 'stage_pv_impuestos', 'stage_pv_escritura',
    'stage_pv_registro', 'stage_pv_desembolso', 'stage_pv_encuesta',
    'stage_pv_comision',
)


@tagged('post_install', '-at_install', 'estate_crm_postventa')
class TestPostventaPipeline(TransactionCase):
    """Embudo Postventa (ETAPA PUENTE): el lead ganado NO se mueve. Se queda en
    'Cierre' —etapa compartida entre el equipo Ventas y el equipo Postventa— y
    por eso se ve a la vez en el embudo comercial (última columna) y en el
    Embudo Postventa (bandeja de entrada), con la MISMA tarjeta."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.postventa_team = cls.env.ref('estate_crm.crm_team_postventa')
        cls.ventas_team = cls.env.ref('sales_team.team_sales_department')
        cls.stage_cierre = cls.env.ref('estate_crm.stage_lead7_estate_cierre')
        cls.stage_recepcion = cls.env.ref('estate_crm.stage_lead1_estate_nuevo')
        cls.stage_sena = cls.env.ref('estate_crm.stage_pv_sena')

    # --- Etapas y scoping --------------------------------------------------

    def test_cierre_es_etapa_puente(self):
        """'Cierre' pertenece a AMBOS equipos: Ventas y Postventa."""
        self.assertEqual(self.stage_cierre.name, 'Cierre')
        self.assertIn(self.ventas_team, self.stage_cierre.team_ids)
        self.assertIn(self.postventa_team, self.stage_cierre.team_ids)

    def test_etapas_postventa_solo_de_postventa(self):
        for xmlid in POSTVENTA_XMLIDS:
            stage = self.env.ref(f'estate_crm.{xmlid}')
            self.assertEqual(stage.team_ids, self.postventa_team,
                              f"{xmlid} debe pertenecer solo al equipo Postventa")

    def test_orden_del_tramite_postventa(self):
        """Las etapas van después de 'Cierre' y en el orden de Ventas Cerradas."""
        seqs = [self.env.ref(f'estate_crm.{x}').sequence for x in POSTVENTA_XMLIDS]
        self.assertEqual(seqs, sorted(seqs), "Deben quedar en orden del trámite")
        self.assertGreater(seqs[0], self.stage_cierre.sequence,
                           "Todas van después de la etapa puente 'Cierre'")
        self.assertTrue(self.env.ref('estate_crm.stage_pv_comision').is_won,
                        "'Comisión' es la etapa final (ganada) de postventa")

    def test_etapas_del_embudo_comercial(self):
        """Las 6 etapas del 'Proceso de Ventas', solo del equipo Ventas."""
        esperado = [
            ('stage_lead1_estate_nuevo', 'Recepción'),
            ('stage_lead3b_estate_seguimiento', 'Seguimiento'),
            ('stage_lead2b_estate_con_necesidad', 'Con Necesidad Pendiente'),
            ('stage_lead_vendedores', 'Vendedores'),
            ('stage_lead4_estate_papeles', 'En Proceso Cierre'),
        ]
        for xmlid, name in esperado:
            stage = self.env.ref(f'estate_crm.{xmlid}')
            self.assertEqual(stage.name, name)
            self.assertEqual(stage.team_ids, self.ventas_team,
                              f"{xmlid} debe ser solo del equipo Ventas")

    def test_existe_la_etapa_perdido(self):
        """'Perdido' es una columna real y visible (plegada) del embudo comercial."""
        perdido = self.env.ref('estate_crm.stage_lead_perdido')
        self.assertTrue(perdido.is_lost, "Debe estar marcada como etapa perdida")
        self.assertTrue(perdido.fold, "Va plegada para no estorbar el día a día")
        self.assertEqual(perdido.team_ids, self.ventas_team)

    # --- El lead ganado NO se mueve ---------------------------------------

    def test_ganar_lead_no_cambia_su_etapa_ni_equipo(self):
        lead = self.env['crm.lead'].create({
            'name': 'Lead Ganado Test', 'stage_id': self.stage_recepcion.id,
            'team_id': self.ventas_team.id, 'type': 'opportunity',
        })
        lead.stage_id = self.stage_cierre
        self.assertEqual(lead.stage_id, self.stage_cierre,
                          "El lead ganado se queda en 'Cierre', no se mueve")
        self.assertEqual(lead.team_id, self.ventas_team,
                          "El lead ganado no cambia de equipo")

    # --- Visibilidad cruzada: misma tarjeta en ambos embudos --------------

    def test_lead_ganado_visible_en_ambos_embudos(self):
        lead = self.env['crm.lead'].create({
            'name': 'Lead Puente Test', 'stage_id': self.stage_cierre.id,
            'team_id': self.ventas_team.id, 'type': 'opportunity',
        })
        flujo = self.env['ir.actions.act_window']._for_xml_id('crm.crm_lead_action_pipeline')
        self.assertTrue(
            self.env['crm.lead'].search(safe_eval(flujo['domain']) + [('id', '=', lead.id)]),
            "El lead ganado SÍ debe verse en Mi Flujo (columna Cierre)")
        pv = self.env['ir.actions.act_window']._for_xml_id('estate_crm.action_crm_lead_postventa')
        self.assertTrue(
            self.env['crm.lead'].search(safe_eval(pv['domain']) + [('id', '=', lead.id)]),
            "El lead ganado SÍ debe verse en el Embudo Postventa (misma etapa puente)")

    def test_lead_no_ganado_no_aparece_en_postventa(self):
        lead = self.env['crm.lead'].create({
            'name': 'Lead Normal Test', 'stage_id': self.stage_recepcion.id,
            'team_id': self.ventas_team.id, 'type': 'opportunity',
        })
        pv = self.env['ir.actions.act_window']._for_xml_id('estate_crm.action_crm_lead_postventa')
        self.assertFalse(
            self.env['crm.lead'].search(safe_eval(pv['domain']) + [('id', '=', lead.id)]),
            "Un lead sin ganar no debe verse en el Embudo Postventa")

    def test_lead_en_tramite_sale_de_mi_flujo(self):
        """Al avanzar el lead al trámite (Seña), deja de verse en el embudo comercial."""
        lead = self.env['crm.lead'].create({
            'name': 'Lead En Tramite', 'stage_id': self.stage_sena.id,
            'team_id': self.ventas_team.id, 'type': 'opportunity',
        })
        flujo = self.env['ir.actions.act_window']._for_xml_id('crm.crm_lead_action_pipeline')
        self.assertFalse(
            self.env['crm.lead'].search(safe_eval(flujo['domain']) + [('id', '=', lead.id)]),
            "Un lead en etapa de postventa no debe verse en Mi Flujo")

    # --- Menú restringido --------------------------------------------------

    def test_solo_admin_ve_el_menu_postventa(self):
        menu = self.env.ref('estate_crm.menu_crm_lead_postventa')
        action = self.env.ref('estate_crm.action_crm_lead_postventa')
        self.assertEqual(menu.action.id, action.id)
        admin_group = self.env.ref('estate_management.estate_group_admin')
        self.assertIn(admin_group, menu.group_ids,
                      "El menú de Postventa debe estar restringido al grupo de admins")
