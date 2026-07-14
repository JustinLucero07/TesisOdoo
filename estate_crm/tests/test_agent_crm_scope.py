# -*- coding: utf-8 -*-
"""Un Asesor solo debe ver SUS propios leads en el CRM.

Regresión: las reglas de registro de grupos distintos se combinan con OR, así
que si el asesor conservaba el grupo de ventas "Todos los documentos" (cuya
regla es [(1,'=',1)]), terminaba viendo los leads de todos los demás."""
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'estate_crm_agent_scope')
class TestAgentCrmScope(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.agent_group = cls.env.ref('estate_management.estate_group_agent')
        # "Todos los documentos" = group_sale_salesman_all_leads (su regla es
        # [(1,'=',1)]). NO confundir con group_sale_manager (Admin de ventas).
        cls.all_docs = cls.env.ref('sales_team.group_sale_salesman_all_leads')
        cls.own_docs = cls.env.ref('sales_team.group_sale_salesman')

        # Se crea con "Todos los documentos" a propósito: es el caso real que
        # hacía que el asesor viera los leads de todos.
        cls.asesor = cls.env['res.users'].create({
            'name': 'Asesor Scope', 'login': 'asesor_scope_test',
            'email': 'asesor_scope@test.com',
            'group_ids': [(4, cls.agent_group.id), (4, cls.all_docs.id)],
        })
        cls.otro = cls.env['res.users'].create({
            'name': 'Otro Asesor', 'login': 'otro_asesor_scope',
            'email': 'otro_scope@test.com',
            'group_ids': [(4, cls.agent_group.id)],
        })
        cls.lead_propio = cls.env['crm.lead'].create({
            'name': 'Lead del asesor', 'type': 'opportunity', 'user_id': cls.asesor.id})
        cls.lead_ajeno = cls.env['crm.lead'].create({
            'name': 'Lead de otro', 'type': 'opportunity', 'user_id': cls.otro.id})

    def _leads_visibles(self, user):
        return self.env['crm.lead'].with_user(user).search([]).ids

    def test_asesor_solo_ve_sus_leads(self):
        # Antes del fix: con "Todos los documentos" veía TAMBIÉN los ajenos
        self.assertIn(self.lead_ajeno.id, self._leads_visibles(self.asesor),
                      "Precondición: así estaba el bug (veía los leads de otros)")

        self.env['res.users']._enforce_agent_crm_scope()

        visibles = self._leads_visibles(self.asesor)
        self.assertIn(self.lead_propio.id, visibles, "Debe ver su propio lead")
        self.assertNotIn(self.lead_ajeno.id, visibles,
                          "NO debe ver el lead de otro asesor")

    def test_se_le_quita_todos_los_documentos(self):
        """Aunque le hayan dado 'Todos los documentos' a mano, se le retira."""
        self.asesor.sudo().write({'group_ids': [(4, self.all_docs.id)]})
        self.assertIn(self.all_docs, self.asesor.group_ids)  # precondición

        self.env['res.users']._enforce_agent_crm_scope()

        self.assertNotIn(self.all_docs, self.asesor.all_group_ids,
                          "Al asesor se le debe quitar 'Todos los documentos'")
        self.assertIn(self.own_docs, self.asesor.all_group_ids,
                      "Debe conservar 'Solo sus documentos'")
        self.assertNotIn(self.lead_ajeno.id, self._leads_visibles(self.asesor),
                          "Ya no debe ver los leads de los demás")

    def test_el_gerente_sigue_viendo_todo(self):
        gerente = self.env['res.users'].create({
            'name': 'Gerente Scope', 'login': 'gerente_scope_test',
            'email': 'gerente_scope@test.com',
            'group_ids': [(4, self.env.ref('estate_management.estate_group_manager').id)],
        })
        self.env['res.users']._enforce_agent_crm_scope()
        visibles = self._leads_visibles(gerente)
        self.assertIn(self.lead_propio.id, visibles)
        self.assertIn(self.lead_ajeno.id, visibles,
                      "El Gerente sí debe seguir viendo los leads de todos")
