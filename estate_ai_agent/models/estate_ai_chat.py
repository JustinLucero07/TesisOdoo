import logging
from datetime import date, timedelta
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class EstateAIChatHistory(models.Model):
    _name = 'estate.ai.chat.history'
    _description = 'Historial de Chat IA'
    _order = 'create_date desc'

    user_id = fields.Many2one(
        'res.users', string='Usuario',
        default=lambda self: self.env.user, required=True)
    query = fields.Text(string='Consulta', required=True)
    response = fields.Text(string='Respuesta')
    query_type = fields.Selection([
        ('property', 'Propiedades'),
        ('client', 'Clientes'),
        ('contract', 'Contratos'),
        ('payment', 'Pagos'),
        ('report', 'Reportes'),
        ('general', 'General'),
    ], string='Tipo de Consulta', default='general')
    processing_time = fields.Float(string='Tiempo de Procesamiento (s)')
    # Metrics for dashboard (C5)
    tool_calls_count = fields.Integer(string='Herramientas usadas', default=0)
    session_id = fields.Char(string='Sesión')

    @api.model
    def _cron_proactive_agent(self):
        """B6: Proactive agent — runs daily, generates alerts for all managers."""
        _logger.info("Agente IA proactivo: iniciando análisis...")
        today = date.today()

        # Gather critical data
        alerts = []

        # 1. Overdue payments (>= 3 days)
        overdue_payments = self.env['estate.payment'].sudo().search([
            ('state', '=', 'pending'),
            ('date', '<', today),
        ])
        if overdue_payments:
            total_overdue = sum(p.amount for p in overdue_payments)
            oldest = min(overdue_payments.mapped('date'))
            alerts.append(
                f"⚠️ *{len(overdue_payments)} pagos vencidos* por un total de ${total_overdue:,.2f}.\n"
                f"  → El más antiguo desde: {oldest}.\n"
                f"  → Acción: Ir a CRM > Pagos > Vencidos y contactar al cliente."
            )

        # 2. Properties available > 90 days
        stale_props = self.env['estate.property'].sudo().search([
            ('state', '=', 'available'),
            ('date_listed', '<=', today - timedelta(days=90)),
        ])
        if stale_props:
            names = ', '.join(stale_props[:3].mapped('title'))
            alerts.append(
                f"🏠 *{len(stale_props)} propiedades* llevan más de 90 días disponibles: {names}{'...' if len(stale_props) > 3 else ''}.\n"
                f"  → Acción: Revisar precio con AVM, mejorar descripción o ajustar comisión."
            )

        # 3. Contracts expiring in next 30 days
        expiring = self.env['estate.contract'].sudo().search([
            ('state', '=', 'active'),
            ('date_end', '>=', today),
            ('date_end', '<=', today + timedelta(days=30)),
        ])
        if expiring:
            nearest = min(expiring.mapped('date_end'))
            alerts.append(
                f"📄 *{len(expiring)} contratos* vencen en los próximos 30 días (el más próximo: {nearest}).\n"
                f"  → Acción: Contactar arrendatarios para renovación antes del vencimiento."
            )

        # 4. Hot leads without activity > 7 days
        stale_leads = self.env['crm.lead'].sudo().search([
            ('lead_temperature', 'in', ['hot', 'boiling']),
            ('type', '=', 'opportunity'),
            ('stage_id.is_won', '=', False),
            ('write_date', '<=', fields.Datetime.now() - timedelta(days=7)),
        ])
        if stale_leads:
            lead_names = ', '.join(l.contact_name or l.name for l in stale_leads[:3])
            alerts.append(
                f"🔥 *{len(stale_leads)} leads calientes* sin actividad por más de 7 días: {lead_names}{'...' if len(stale_leads) > 3 else ''}.\n"
                f"  → Acción: Crear actividad de seguimiento o llamada para cada uno."
            )

        # 5. New leads from webhook (last 24h)
        new_leads = self.env['crm.lead'].sudo().search_count([
            ('create_date', '>=', str(fields.Datetime.now() - timedelta(hours=24))),
            ('type', '=', 'opportunity'),
        ])
        if new_leads:
            alerts.append(
                f"📥 *{new_leads} nuevos leads* ingresaron en las últimas 24 horas.\n"
                f"  → Acción: Calificarlos y asignar asesor."
            )

        # 6. Today's visits
        tomorrow = today + timedelta(days=1)
        today_visits = self.env['calendar.event'].sudo().search_count([
            ('start', '>=', str(today)),
            ('start', '<', str(tomorrow)),
        ])
        if today_visits:
            alerts.append(
                f"📅 *{today_visits} visitas programadas* para hoy.\n"
                f"  → Recordatorio: Confirmar con los clientes y preparar fichas de propiedades."
            )

        if not alerts:
            alerts.append("✅ Todo en orden — sin alertas críticas para hoy.")

        alert_text = "\n".join(alerts)
        summary_msg = f"📊 *Resumen diario del Agente IA — {today.strftime('%d/%m/%Y')}*\n\n{alert_text}"

        # Send notification to all managers and admins
        manager_group = self.env.ref('estate_management.estate_group_manager', raise_if_not_found=False)
        admin_group = self.env.ref('estate_management.estate_group_admin', raise_if_not_found=False)
        group_ids = [g.id for g in [manager_group, admin_group] if g]
        if group_ids:
            users = self.env['res.users'].search([('group_ids', 'in', group_ids)])
        else:
            users = self.env['res.users']
        partners = users.mapped('partner_id')

        for partner in partners:
            try:
                self.env['bus.bus']._sendone(
                    partner,
                    'simple_notification',
                    {
                        'title': '📊 Agente IA — Resumen Diario',
                        'message': summary_msg,
                        'type': 'info',
                        'sticky': True,
                    }
                )
            except Exception as e:
                _logger.warning("Error enviando notificación proactiva a %s: %s", partner.name, e)

        # Log to history
        self.sudo().create({
            'user_id': self.env.ref('base.user_root').id,
            'query': 'CRON: Análisis proactivo diario',
            'response': summary_msg,
            'query_type': 'report',
        })

        _logger.info("Agente IA proactivo: análisis completado. %d alertas generadas.", len(alerts))
