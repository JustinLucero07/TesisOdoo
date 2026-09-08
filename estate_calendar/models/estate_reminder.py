# -*- coding: utf-8 -*-
"""Recordatorios sobre un cliente (pólizas, pagos, renovaciones, papeleo).

A diferencia de las citas, aquí no hay un evento en el calendario: solo una
fecha y hora de vencimiento y cuánta anticipación quiere el asesor, en la misma
unidad que usan los recordatorios de visitas (minutos, horas o días). El cron
levanta el aviso por partida doble: una actividad en Odoo (campanita) y un push
a la app del responsable.
"""
import logging
from datetime import datetime, timedelta

import pytz

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from .calendar_event import REMINDER_UNITS, reminder_to_minutes

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
    _order = 'deadline asc, id desc'

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

    # ── Documentos ──────────────────────────────────────────────────────────
    document_id = fields.Many2one(
        'estate.document', string='Documento', ondelete='set null',
        help='Documento ya cargado en el expediente al que se refiere el aviso.')
    attachment_ids = fields.Many2many(
        'ir.attachment', 'estate_reminder_attachment_rel',
        'reminder_id', 'attachment_id', string='Archivos adjuntos',
        help='Sube aquí la póliza, el comprobante o cualquier respaldo suelto.')
    attachment_count = fields.Integer(compute='_compute_attachment_count')

    # ── Cuándo ──────────────────────────────────────────────────────────────
    date = fields.Date(
        string='Fecha', required=True, index=True, tracking=True,
        default=lambda self: fields.Date.context_today(self) + timedelta(days=30),
        help='El día del vencimiento o del hecho que hay que recordar.')
    hour = fields.Float(
        string='Hora', default=9.0,
        help='Hora del vencimiento. Si da igual, deja las 09:00.')
    deadline = fields.Datetime(
        string='Vence', compute='_compute_deadline', store=True, index=True,
        help='Fecha y hora del vencimiento (uso interno, en UTC).')

    remind_value = fields.Integer(
        string='Avisar antes', default=7,
        help='Cuánta anticipación quieres. 0 = avisar solo al vencer.')
    remind_unit = fields.Selection(
        REMINDER_UNITS, string='Unidad', default='days', required=True)
    remind_minutes = fields.Integer(
        string='Anticipación (minutos)', compute='_compute_notify_datetime',
        store=True, readonly=True)
    notify_datetime = fields.Datetime(
        string='Fecha del aviso', compute='_compute_notify_datetime',
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
    def _user_tz(self):
        return pytz.timezone(self.env.user.tz or 'UTC')

    @api.depends('date', 'hour')
    def _compute_deadline(self):
        tz = self._user_tz()
        for rec in self:
            if not rec.date:
                rec.deadline = False
                continue
            horas = max(min(rec.hour or 0.0, 23.99), 0.0)
            local = datetime.combine(rec.date, datetime.min.time()) + timedelta(hours=horas)
            rec.deadline = tz.localize(local).astimezone(pytz.UTC).replace(tzinfo=None)

    @api.depends('deadline', 'remind_value', 'remind_unit')
    def _compute_notify_datetime(self):
        for rec in self:
            rec.remind_minutes = reminder_to_minutes(rec.remind_value, rec.remind_unit)
            if rec.deadline:
                rec.notify_datetime = rec.deadline - timedelta(minutes=rec.remind_minutes)
            else:
                rec.notify_datetime = False

    @api.depends('attachment_ids')
    def _compute_attachment_count(self):
        for rec in self:
            rec.attachment_count = len(rec.attachment_ids)

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
            elif rec.remind_minutes and rec.days_left <= max(rec.remind_minutes // 1440, 1):
                rec.urgency = 'soon'
            else:
                rec.urgency = 'later'

    @api.constrains('remind_value')
    def _check_remind_value(self):
        for rec in self:
            if rec.remind_value and rec.remind_value < 0:
                raise ValidationError('La anticipación no puede ser negativa.')

    @api.onchange('document_id')
    def _onchange_document_id(self):
        """Al enlazar un documento se hereda lo que ya se sabe de él."""
        doc = self.document_id
        if not doc:
            return
        if doc.expiration_date:
            self.date = doc.expiration_date
        if not self.name:
            self.name = 'Vence: %s' % (doc.name or '')
        if not self.partner_id and doc.partner_id:
            self.partner_id = doc.partner_id
        if not self.property_id and doc.property_id:
            self.property_id = doc.property_id
        if self.reminder_type == 'other':
            self.reminder_type = 'document'

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

    def action_open_document(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'estate.document',
            'res_id': self.document_id.id,
            'view_mode': 'form',
        }

    def action_open_partner(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'res_id': self.partner_id.id,
            'view_mode': 'form',
        }

    # ── Envío del aviso ─────────────────────────────────────────────────────
    def _format_local(self, dt):
        """Datetime UTC → texto en la zona horaria del responsable."""
        if not dt:
            return ''
        tz = pytz.timezone(self.user_id.tz or self.env.user.tz or 'UTC')
        local = pytz.UTC.localize(dt).astimezone(tz)
        if self.hour:
            return local.strftime('%d/%m/%Y %H:%M')
        return local.strftime('%d/%m/%Y')

    def _reminder_body(self, due=False):
        self.ensure_one()
        cliente = self.partner_id.name or 'Cliente'
        cuando = self._format_local(self.deadline)
        if due:
            texto = 'vence hoy (%s)' % cuando if self.days_left == 0 else 'venció el %s' % cuando
        elif self.days_left > 0:
            texto = 'vence en %d día%s (%s)' % (
                self.days_left, '' if self.days_left == 1 else 's', cuando)
        else:
            texto = 'vence hoy a las %s' % cuando
        detalle = '%s: %s %s.' % (cliente, self.name, texto)
        if self.document_id:
            detalle += ' Documento: %s.' % self.document_id.name
        return detalle

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
                        'document_id': rec.document_id.id or 0,
                        'reminder_type': rec.reminder_type,
                    },
                )

            vals = {'last_notified_on': fields.Datetime.now(), 'advance_notified': True}
            if due:
                # Cuando el aviso previo y el del vencimiento caen juntos
                # (anticipación 0) se dan los dos por enviados.
                vals['due_notified'] = True
            rec.write(vals)

    # ── Cron ────────────────────────────────────────────────────────────────
    @api.model
    def _cron_notify_reminders(self):
        ahora = fields.Datetime.now()

        previos = self.search([
            ('state', '=', 'pending'),
            ('advance_notified', '=', False),
            ('notify_datetime', '<=', ahora),
            ('deadline', '>', ahora),
        ])
        for rec in previos:
            try:
                rec._notify(due=False)
            except Exception:
                _logger.exception('Falló el aviso previo del recordatorio %s', rec.id)

        vencidos = self.search([
            ('state', '=', 'pending'),
            ('due_notified', '=', False),
            ('deadline', '<=', ahora),
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


class EstateDocumentReminder(models.Model):
    _inherit = 'estate.document'

    reminder_ids = fields.One2many('estate.reminder', 'document_id', string='Recordatorios')

    def action_create_reminder(self):
        """Crea un recordatorio desde el documento, con lo que ya se sabe de él."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Nuevo recordatorio',
            'res_model': 'estate.reminder',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_document_id': self.id,
                'default_partner_id': self.partner_id.id,
                'default_property_id': self.property_id.id,
                'default_reminder_type': 'document',
                'default_name': 'Vence: %s' % (self.name or ''),
                'default_date': self.expiration_date or fields.Date.context_today(self),
            },
        }
