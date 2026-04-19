# -*- coding: utf-8 -*-
from odoo import models, fields


class EstateCommissionWizard(models.TransientModel):
    _name = 'estate.commission.wizard'
    _description = 'Asistente de Reporte de Comisiones'

    user_id = fields.Many2one(
        'res.users', string='Asesor',
        help='Deja vacío para incluir todos los asesores.')
    date_from = fields.Date(string='Desde', required=True,
                            default=lambda self: fields.Date.today().replace(day=1))
    date_to = fields.Date(string='Hasta', required=True,
                          default=fields.Date.today)
    include_all_states = fields.Boolean(
        string='Incluir todas las comisiones',
        default=False,
        help='Si está activo, incluye borradores y canceladas. Por defecto solo aprobadas y pagadas.')

    def action_print_commission_report(self):
        """Genera el PDF de liquidación de comisiones para el asesor/período seleccionado."""
        domain = []
        if self.user_id:
            domain.append(('id', '=', self.user_id.id))
        else:
            # Todos los asesores que tienen comisiones en el período
            commissions = self.env['estate.commission'].search(
                self._get_commission_domain())
            user_ids = commissions.mapped('user_id').ids
            if not user_ids:
                raise models.ValidationError('No se encontraron comisiones para el período seleccionado.')
            domain.append(('id', 'in', user_ids))

        users = self.env['res.users'].search(domain)
        if not users:
            raise models.ValidationError('No se encontraron asesores con comisiones en el período.')

        return self.env.ref('estate_reports.action_report_commission_liquidation').with_context(
            date_from=self.date_from,
            date_to=self.date_to,
            include_all_states=self.include_all_states,
        ).report_action(users)

    def _get_commission_domain(self):
        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]
        if not self.include_all_states:
            domain.append(('state', 'in', ('approved', 'paid')))
        if self.user_id:
            domain.append(('user_id', '=', self.user_id.id))
        return domain
