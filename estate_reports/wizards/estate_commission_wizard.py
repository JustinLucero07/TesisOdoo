# -*- coding: utf-8 -*-
from odoo import models, fields, api


class EstateCommissionWizard(models.TransientModel):
    _name = 'estate.commission.wizard'
    _description = 'Asistente de Reporte de Comisiones'

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = 'Reporte de Comisiones'

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

    commission_count = fields.Integer(compute='_compute_commission_html')
    total_commissions = fields.Float(compute='_compute_commission_html')
    total_paid = fields.Float(compute='_compute_commission_html')
    total_pending = fields.Float(compute='_compute_commission_html')
    commission_html = fields.Html(string='Comisiones', compute='_compute_commission_html', sanitize=False)

    @api.depends('user_id', 'date_from', 'date_to', 'include_all_states')
    def _compute_commission_html(self):
        for wiz in self:
            domain = wiz._get_commission_domain()
            commissions = wiz.env['estate.commission'].search(domain, order='date desc')
            wiz.commission_count = len(commissions)
            wiz.total_commissions = sum(c.amount for c in commissions)
            wiz.total_paid = sum(c.amount for c in commissions if c.state == 'paid')
            wiz.total_pending = sum(c.amount for c in commissions if c.state == 'approved')

            if not commissions:
                wiz.commission_html = '<p style="color:#9ca3af;font-style:italic;padding:16px;">Sin comisiones para los filtros seleccionados.</p>'
                continue

            state_labels = {'draft': 'Borrador', 'approved': 'Aprobada', 'paid': 'Pagada', 'cancelled': 'Cancelada'}
            state_colors = {'draft': '#6b7280', 'approved': '#d97706', 'paid': '#16a34a', 'cancelled': '#dc2626'}
            rows = ''
            for i, c in enumerate(commissions):
                bg = '#f9fafb' if i % 2 == 0 else '#ffffff'
                state_color = state_colors.get(c.state, '#6b7280')
                state_label = state_labels.get(c.state, c.state)
                prop_name = c.property_id.title or c.property_id.name if c.property_id else '—'
                rows += (
                    f'<tr style="background:{bg};">'
                    f'<td style="padding:8px 12px;font-weight:600;color:#004274;">{prop_name}</td>'
                    f'<td style="padding:8px 12px;color:#6b7280;">{c.user_id.name or "—"}</td>'
                    f'<td style="padding:8px 12px;text-align:right;">${c.sale_amount:,.2f}</td>'
                    f'<td style="padding:8px 12px;text-align:center;">{c.commission_pct or 0:.1f}%</td>'
                    f'<td style="padding:8px 12px;text-align:right;font-weight:700;color:#16a34a;">${c.amount:,.2f}</td>'
                    f'<td style="padding:8px 12px;text-align:center;color:#6b7280;">{str(c.date) if c.date else "—"}</td>'
                    f'<td style="padding:8px 12px;text-align:center;">'
                    f'<span style="font-size:10px;font-weight:700;padding:2px 8px;background:{state_color}20;color:{state_color};border:1px solid {state_color}40;">{state_label}</span>'
                    f'</td>'
                    f'</tr>'
                )

            wiz.commission_html = f'''
<table style="width:100%;border-collapse:collapse;font-size:12px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <thead>
    <tr style="background:#004274;color:white;">
      <th style="padding:10px 12px;text-align:left;">Propiedad</th>
      <th style="padding:10px 12px;text-align:left;">Asesor</th>
      <th style="padding:10px 12px;text-align:right;">Monto Venta</th>
      <th style="padding:10px 12px;text-align:center;">%</th>
      <th style="padding:10px 12px;text-align:right;">Comisión</th>
      <th style="padding:10px 12px;text-align:center;">Fecha</th>
      <th style="padding:10px 12px;text-align:center;">Estado</th>
    </tr>
  </thead>
  <tbody>{rows}</tbody>
  <tfoot>
    <tr style="background:#004274;color:white;font-weight:700;">
      <td colspan="4" style="padding:10px 12px;">Total — {len(commissions)} comisiones</td>
      <td style="padding:10px 12px;text-align:right;font-size:14px;">${wiz.total_commissions:,.2f}</td>
      <td colspan="2" style="padding:10px 12px;text-align:right;font-size:11px;font-weight:400;color:rgba(255,255,255,0.7);">
        Pagado: ${wiz.total_paid:,.2f} | Pendiente: ${wiz.total_pending:,.2f}
      </td>
    </tr>
  </tfoot>
</table>'''

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

    @api.model
    def get_commission_payload(self, kwargs):
        user_id = kwargs.get('user_id')
        date_from = kwargs.get('date_from')
        date_to = kwargs.get('date_to')
        include_all = kwargs.get('include_all', False)
        
        wiz = self.create({
            'user_id': user_id,
            'date_from': date_from or fields.Date.today().replace(day=1),
            'date_to': date_to or fields.Date.today(),
            'include_all_states': include_all,
        })
        
        # Asesores activos (con comisiones)
        advisors = self.env['res.users'].search([
            ('id', 'in', self.env['estate.commission'].search([]).mapped('user_id').ids)
        ])
        advisors_list = [{'id': a.id, 'name': a.name} for a in advisors]
        
        return {
            'kpis': {
                'commission_count': wiz.commission_count,
                'total_commissions': wiz.total_commissions,
                'total_paid': wiz.total_paid,
                'total_pending': wiz.total_pending,
                'date_from': str(wiz.date_from),
                'date_to': str(wiz.date_to),
            },
            'table_html': wiz.commission_html,
            'advisors': advisors_list,
        }

    @api.model
    def owl_print_pdf(self, kwargs):
        user_id = kwargs.get('user_id')
        date_from = kwargs.get('date_from')
        date_to = kwargs.get('date_to')
        include_all = kwargs.get('include_all', False)
        
        wiz = self.create({
            'user_id': user_id,
            'date_from': date_from or fields.Date.today().replace(day=1),
            'date_to': date_to or fields.Date.today(),
            'include_all_states': include_all,
        })
        return wiz.action_print_commission_report()
