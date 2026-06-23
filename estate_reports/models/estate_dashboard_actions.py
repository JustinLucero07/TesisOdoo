# -*- coding: utf-8 -*-
"""Acciones de navegacion del dashboard (abrir listas, graficos, wizards). Extraido de estate_dashboard.py."""
import logging

from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class EstateDashboardActions(models.TransientModel):
    _inherit = 'estate.dashboard'

    def _action_open_property_list(self, domain, name):
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': 'estate.property',
            'view_mode': 'list,form',
            'domain': domain,
            'target': 'current',
        }

    def action_open_all_properties(self):
        return self._action_open_property_list([], 'Todas las Propiedades')

    def action_open_available(self):
        return self._action_open_property_list([('state', '=', 'available')], 'Propiedades Disponibles')

    def action_open_sold(self):
        return self._action_open_property_list([('state', '=', 'sold')], 'Propiedades Vendidas')

    def action_open_stagnant(self):
        cutoff_45 = fields.Date.today() - timedelta(days=45)
        stagnant_ids = []
        available_old = self.env['estate.property'].search([
            ('state', '=', 'available'), ('date_listed', '<=', cutoff_45)
        ])
        CalEvent = self.env['calendar.event'].sudo()
        for prop in available_old:
            if not CalEvent.search_count([
                ('property_id', '=', prop.id),
                ('visit_state', '=', 'done'),
                ('start', '>=', fields.Datetime.to_datetime(cutoff_45)),
            ]):
                stagnant_ids.append(prop.id)
        return self._action_open_property_list([('id', 'in', stagnant_ids)], 'Propiedades Estancadas (+45 días)')

    def action_open_offers(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Ofertas Activas',
            'res_model': 'estate.property.offer',
            'view_mode': 'list,form',
            'domain': [('state', 'in', ('submitted', 'countered', 'accepted'))],
            'target': 'current',
        }

    def action_open_contracts(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Contratos Activos',
            'res_model': 'estate.contract',
            'view_mode': 'list,form',
            'domain': [('state', '=', 'active')],
            'target': 'current',
        }

    def action_open_sale_orders(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Órdenes de Venta',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [('property_id', '!=', False), ('state', 'in', ('sale', 'done'))],
            'target': 'current',
        }

    def action_open_opportunities(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Oportunidades Activas',
            'res_model': 'crm.lead',
            'view_mode': 'list,form',
            'domain': [('type', '=', 'opportunity'), ('probability', '>', 0), ('probability', '<', 100)],
            'target': 'current',
        }

    def action_open_appointments(self):
        today = fields.Date.today()
        first_day = today.replace(day=1)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Visitas Realizadas (Mes)',
            'res_model': 'calendar.event',
            'view_mode': 'list,form',
            'domain': [('property_id', '!=', False), ('visit_state', '=', 'done'), ('start', '>=', first_day)],
            'target': 'current',
        }

    def action_open_expiring_contracts(self):
        limit = fields.Date.today() + timedelta(days=30)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Contratos por Vencer (30 días)',
            'res_model': 'estate.property',
            'view_mode': 'list,form',
            'domain': [
                ('contract_end_date', '!=', False),
                ('contract_end_date', '<=', limit),
                ('state', 'in', ('available', 'reserved')),
            ],
            'target': 'current',
        }

    def action_open_ai(self):
        return {'type': 'ir.actions.client', 'tag': 'estate_ai_open_chat'}

    def action_open_report_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Generar Reporte',
            'res_model': 'estate.report.wizard',
            'view_mode': 'form',
            'target': 'new',
        }

    def action_export_dashboard_pdf(self):
        """A4: exporta el dashboard completo (KPIs, finanzas, tendencias,
        embudo y ranking) a un PDF ejecutivo."""
        self.ensure_one()
        # Aseguramos que los campos computados estén frescos antes de imprimir
        self._compute_kpis()
        self._compute_trends()
        self._compute_funnel()
        self._compute_advisor_ranking()
        return self.env.ref(
            'estate_reports.action_report_dashboard_executive'
        ).report_action(self)

    def action_open_funnel_leads(self):
        period_from, period_to = self._get_period_dates()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Leads del Período',
            'res_model': 'crm.lead',
            'view_mode': 'list,form,kanban',
            'domain': [
                ('create_date', '>=', str(period_from)),
                ('create_date', '<=', str(period_to) + ' 23:59:59'),
            ],
            'target': 'current',
        }

    def action_open_overdue_payments(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Pagos Vencidos',
            'res_model': 'estate.payment',
            'view_mode': 'list,form',
            'domain': [('state', '=', 'pending'), ('date', '<', fields.Date.today())],
            'target': 'current',
        }

    def _reload_dashboard(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'estate.dashboard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_sales_graph(self):
        return self.env.ref('estate_reports.action_sales_by_month').read()[0]

    def action_open_advisor_graph(self):
        return self.env.ref('estate_reports.action_sales_by_user').read()[0]

    def action_open_commission_wizard(self):
        return self.env.ref('estate_reports.action_estate_commission_report_owl').read()[0]

    @api.model
    def _reset_board_customizations(self):
        board_view = self.env.ref('estate_reports.estate_board_view', raise_if_not_found=False)
        if board_view:
            self.env['ir.ui.view.custom'].sudo().search([('ref_id', '=', board_view.id)]).unlink()
