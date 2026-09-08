# -*- coding: utf-8 -*-
"""Recordatorios sobre un cliente (pólizas, pagos, renovaciones, papeleo).

A diferencia de las citas, aquí no hay una hora concreta ni un evento en el
calendario: solo una fecha de vencimiento y cuántos días antes hay que avisar.
El cron levanta el aviso por partida doble, igual que los recordatorios de
visitas: una actividad en Odoo (campanita) y un push a la app del responsable.
"""
import logging
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

REMINDER_TYPES = [
    ('policy', 'Póliza / Seguro'),
    ('payment', 'Pago o cuota'),
    ('document', 'Documento por vencer'),
    ('contract', 'Contrato / Renovación'),
    ('followup', 'Seguimiento comercial'),
    ('birthday', 'Cumpleaños'),
    ('other', 'Otro'),
]

TYPE_ICON = {
    'policy': '🛡️',
    'payment': '💵',
    'document': '📄',
    'contract': '📝',
    'followup': '📞',
    'birthday': '🎂',
    'other': '🔔',
}


class EstateReminder(models.Model):
    _name = 'estate.reminder'
    _description = 'Recordatorio de cliente'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date asc, id desc'

    name = fields.Char(
        string='Asunto', required=True, tracking=True,
        help='Ej.: "Vence la póliza de incendios".')
    reminder_type = fields.Selection(
        REMINDER_TYPES, string='Tipo', default='other', required=True, tracking=True)

    partner_id = fields.Many2one(
        'res.partner', string='Cliente', required=True, index=True,
        ondelete='cascade', tracking=True)
    property_id = fields.Many2one(
        'estate.property', string='Propiedad', ondelete='set null',
        help='Opcional: si el recordatorio tiene que ver con un inmueble.')
    lead_id = fields.Many2one(
        'crm.lead', string='Oportunidad', ondelete='set null')

    date = fields.Date(
        string='Fecha', required=True, index=True, tracking=True,
        help='El día del vencimiento o del hecho que hay que recordar.')
    days_before = fields.Integer(
        string='Avisar días antes', default=7,
        help='0 = avisar solo el mismo día.')
    notify_date = fields.Date(
        string='Fecha del aviso', compute='_compute_notify_date',
        store=True, index=True)

    user_id = fields.Many2one(
        'res.users', string='Responsable', required=True, index=True,
        default=lambda self: self.env.user, tracking=True,
        domain=[('share', '=', False)],
        help='Quien recibe la actividad en Odoo y la notificación en el móvil.')

    notify_push = fields.Boolean(
        string='Notificar al móvil', default=True,
        help='Envía una notificación push a la app del responsable.')
    notify_activity = fields.Boolean(
        string='Crear actividad en Odoo', default=True,
        help='Deja el aviso en la campanita de actividades de Odoo.')

    note = fields.Text(string='Notas')

    state = fields.Selection([
        ('pending', 'Pendiente'),
        ('done', 'Hecho'),
        ('cancelled', 'Cancelado'),
    ], string='Estado', default='pending', required=True, tracking=True)

    advance_notified = fields.Boolean(string='Aviso previo enviado', readonly=True, copy=False)
    due_notified = fields.Boolean(string='Aviso del día enviado', readonly=True, copy=False)
    last_notified_on = fields.Datetime(string='Último aviso', readonly=True, copy=False)

    days_left = fields.Integer(string='Días restantes', compute='_compute_days_left')
    urgency = fields.Selection([
        ('overdue', 'Vencido'),
        ('today', 'Hoy'),
        ('soon', 'Próximo'),
        ('later', 'Más adelante'),
        ('closed', 'Cerrado'),
    ], string='Urgencia', compute='_compute_days_left')

    # ── Cálculos ────────────────────────────────────────────────────────────
    @api.depends('date', 'days_before')
    def _compute_notify_date(self):
        for rec in self:
            if rec.date:
                rec.notify_date = rec.date - timedelta(days=max(rec.days_before or 0, 0))
            else:
                rec.notify_date = False

    @api.depends('date', 'state')
    def _compute_days_left(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.days_left = (rec.date - today).days if rec.date else 0
            if rec.state != 'pending':
                rec.urgency = 'closed'
            elif not rec.date:
                rec.urgency = 'later'
            elif rec.days_left < 0:
                rec.urgency = 'overdue'
            elif rec.days_left == 0:
                rec.urgency = 'today'
            elif rec.days_left <= max(rec.days_before or 0, 1):
                rec.urgency = 'soon'
            else:
                rec.urgency = 'later'

    @api.constrains('days_before')
    def _check_days_before(self):
        for rec in self:
            if rec.days_before and rec.days_before < 0:
                raise ValidationError('Los días de anticipación no pueden ser negativos.')

    # ── Acciones ────────────────────────────────────────────────────────────
    def action_done(self):
        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset(self):
        self.write({
            'state': 'pending',
            'advance_notified': False,
            'due_notified': False,
        })

    def action_notify_now(self):
        """Botón para probar el aviso sin esperar al cron."""
        for rec in self:
            rec._notify(due=rec.days_left <= 0)
        return True

    def action_open_partner(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'res_id': self.partner_id.id,
            'view_mode': 'form',
        }

    # ── Envío del aviso ─────────────────────────────────────────────────────
    def _reminder_body(self, due=False):
        self.ensure_one()
        cliente = self.partner_id.name or 'Cliente'
        fecha = fields.Date.to_string(self.date)
        if due:
            cuando = 'vence hoy' if self.days_left == 0 else 'venció el %s' % fecha
        else:
            dias = self.days_left
            cuando = 'vence en %d día%s (%s)' % (dias, '' if dias == 1 else 's', fecha)
        return '%s: %s %s.' % (cliente, self.name, cuando)

    def _notify(self, due=False):
        """Levanta el aviso: actividad en Odoo, chatter y push al móvil."""
        for rec in self:
            body = rec._reminder_body(due=due)
            titulo = '%s %s' % (TYPE_ICON.get(rec.reminder_type, '🔔'),
                                'Vence hoy' if due else 'Recordatorio')

            if rec.notify_activity:
                try:
                    rec.activity_schedule(
                        'mail.mail_activity_data_todo',
                        date_deadline=rec.date,
                        summary=rec.name,
                        note=body,
                        user_id=rec.user_id.id,
                    )
                except Exception:
                    _logger.exception('No se pudo crear la actividad del recordatorio %s', rec.id)

            try:
                rec.message_post(body=body, partner_ids=rec.user_id.partner_id.ids)
                if rec.partner_id:
                    rec.partner_id.message_post(body=body)
            except Exception:
                _logger.exception('No se pudo publicar el recordatorio %s en el chatter', rec.id)

            if rec.notify_push and rec.user_id.fcm_token:
                rec.user_id.send_firebase_push(
                    title=titulo,
                    body=body,
                    data={
                        'type': 'client_reminder',
                        'reminder_id': rec.id,
                        'partner_id': rec.partner_id.id or 0,
                        'reminder_type': rec.reminder_type,
                    },
                )

            vals = {'last_notified_on': fields.Datetime.now()}
            if due:
                vals['due_notified'] = True
                # Cuando el aviso previo y el del día caen juntos (days_before=0)
                # se dan los dos por enviados para no repetir mañana.
                vals['advance_notified'] = True
            else:
                vals['advance_notified'] = True
            rec.write(vals)

    # ── Cron ────────────────────────────────────────────────────────────────
    @api.model
    def _cron_notify_reminders(self):
        today = fields.Date.context_today(self)

        previos = self.search([
            ('state', '=', 'pending'),
            ('advance_notified', '=', False),
            ('notify_date', '<=', today),
            ('date', '>', today),
        ])
        for rec in previos:
            try:
                rec._notify(due=False)
            except Exception:
                _logger.exception('Falló el aviso previo del recordatorio %s', rec.id)

        vencidos = self.search([
            ('state', '=', 'pending'),
            ('due_notified', '=', False),
            ('date', '<=', today),
        ])
        for rec in vencidos:
            try:
                rec._notify(due=True)
            except Exception:
                _logger.exception('Falló el aviso de vencimiento del recordatorio %s', rec.id)

        total = len(previos) + len(vencidos)
        if total:
            _logger.info('Recordatorios de clientes: %d aviso(s) enviados.', total)


class ResPartnerReminder(models.Model):
    _inherit = 'res.partner'

    reminder_ids = fields.One2many('estate.reminder', 'partner_id', string='Recordatorios')
    reminder_count = fields.Integer(
        string='Recordatorios pendientes', compute='_compute_reminder_count')

    def _compute_reminder_count(self):
        data = self.env['estate.reminder']._read_group(
            [('partner_id', 'in', self.ids), ('state', '=', 'pending')],
            ['partner_id'], ['__count'])
        counts = {partner.id: count for partner, count in data}
        for rec in self:
            rec.reminder_count = counts.get(rec.id, 0)

    def action_view_reminders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Recordatorios de %s' % self.name,
            'res_model': 'estate.reminder',
            'view_mode': 'list,form,calendar',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }
