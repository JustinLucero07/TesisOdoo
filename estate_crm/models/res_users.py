# -*- coding: utf-8 -*-
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def _enforce_agent_crm_scope(self):
        """Un Asesor solo debe ver SUS propios leads en el CRM.

        En Odoo, las reglas de registro de grupos DISTINTOS se combinan con OR.
        La regla del Asesor es restrictiva —[('user_id','=',user.id)]— pero si el
        usuario conserva además el grupo de ventas "Todos los documentos"
        (sales_team.group_sale_manager), la regla de ESE grupo es [(1,'=',1)] y,
        al hacer OR, termina viendo los leads de todo el mundo.

        Aquí se le quita ese grupo a quien sea Asesor y NO sea Gerente/Admin/
        Marketing, y se le garantiza el de "Solo sus documentos". Idempotente:
        corre en cada actualización del módulo y no hace nada si ya está bien."""
        ref = lambda x: self.env.ref(x, raise_if_not_found=False)
        agent = ref('estate_management.estate_group_agent')
        own_docs = ref('sales_team.group_sale_salesman')     # "Solo sus documentos"
        if not (agent and own_docs):
            return
        # Grupos de ventas que dan visibilidad AMPLIA y hay que retirar al asesor.
        # OJO: "Todos los documentos" es group_sale_salesman_all_leads (su regla
        # es [(1,'=',1)]); group_sale_manager es el rol de Administrador de ventas.
        broad_groups = self.env['res.groups'].browse()
        for xmlid in ('sales_team.group_sale_salesman_all_leads',
                      'sales_team.group_sale_manager'):
            grp = ref(xmlid)
            if grp:
                broad_groups |= grp
        if not broad_groups:
            return

        elevated = self.env['res.groups'].browse()
        for xmlid in ('estate_group_manager', 'estate_group_admin', 'estate_group_marketing'):
            grp = ref(f'estate_management.{xmlid}')
            if grp:
                elevated |= grp

        # Asesores "puros": tienen el rol de Asesor y ninguno de los elevados
        agents = self.search([('all_group_ids', 'in', agent.id)])
        pure_agents = agents.filtered(
            lambda u: not (u.all_group_ids & elevated) and u.id != self.env.ref('base.user_root').id
        )
        for user in pure_agents:
            vals = [(3, grp.id) for grp in broad_groups if grp in user.group_ids]
            if own_docs not in user.all_group_ids:
                vals.append((4, own_docs.id))   # asegurar "Solo sus documentos"
            if vals:
                user.sudo().write({'group_ids': vals})
                _logger.info(
                    'CRM: el asesor %s ya solo verá sus propios leads '
                    '(se le quitó el acceso a todos los documentos de ventas).',
                    user.login)

        self._ensure_sales_team_membership()

    @api.model
    def _ensure_sales_team_membership(self):
        """Mete al equipo "Ventas" a todo usuario interno del CRM que no esté en
        ningún equipo.

        Odoo arma las columnas del embudo con las etapas del EQUIPO del usuario
        (contexto show_user_team_stages). Un usuario sin equipo no ve las etapas
        del equipo Ventas: solo las que no tienen equipo asignado. Por eso a los
        asesores les aparecían etapas distintas a las del resto. Idempotente."""
        ventas = self.env.ref('sales_team.team_sales_department', raise_if_not_found=False)
        agent = self.env.ref('estate_management.estate_group_agent', raise_if_not_found=False)
        if not (ventas and agent):
            return
        Member = self.env['crm.team.member'].sudo().with_context(active_test=False)
        crm_users = self.search([
            ('share', '=', False), ('active', '=', True),
            ('all_group_ids', 'in', agent.id),
        ])
        for user in crm_users:
            if not Member.search_count([('user_id', '=', user.id)]):
                Member.create({'user_id': user.id, 'crm_team_id': ventas.id})
                _logger.info('CRM: %s se agregó al equipo "%s" para que vea las '
                             'etapas correctas del embudo.', user.login, ventas.name)
