from odoo import api, models, fields


class MetaWebhookEvent(models.Model):
    """Registro de eventos de webhook Meta ya procesados, para idempotencia.

    Meta puede reenviar el mismo webhook varias veces (políticas de retry).
    Cada mensaje tiene un `id` único por canal — lo guardamos aquí con UNIQUE
    para descartar duplicados al instante.
    """
    _name = 'estate.meta.webhook.event'
    _description = 'Evento de Webhook Meta Procesado'
    _order = 'received_at desc'
    _rec_name = 'event_id'

    event_id = fields.Char(
        string='Event ID', required=True, index=True,
        help='ID único del mensaje/evento devuelto por Meta (msg.id, mid, etc.).')
    channel = fields.Selection([
        ('whatsapp', 'WhatsApp'),
        ('facebook', 'Facebook Messenger'),
        ('instagram', 'Instagram DM'),
        ('other', 'Otro'),
    ], string='Canal', required=True, default='other')
    received_at = fields.Datetime(
        string='Recibido', default=fields.Datetime.now, required=True)
    lead_id = fields.Many2one(
        'crm.lead', string='Lead generado', ondelete='set null')
    payload_summary = fields.Char(string='Resumen', size=255)

    _sql_constraints = [
        ('event_id_unique', 'UNIQUE(event_id)',
         'Este evento de webhook ya fue procesado anteriormente.'),
    ]

    @api.model
    def is_already_processed(self, event_id):
        """Devuelve True si el event_id ya está registrado."""
        if not event_id:
            return False
        return bool(self.sudo().search_count([('event_id', '=', event_id)]))

    @api.model
    def register(self, event_id, channel='other', lead=None, summary=''):
        """Registra el evento. Si ya existe (race condition), retorna False."""
        from psycopg2 import IntegrityError
        if not event_id:
            return False
        try:
            with self.env.cr.savepoint():
                rec = self.sudo().create({
                    'event_id': event_id,
                    'channel': channel,
                    'lead_id': lead.id if lead else False,
                    'payload_summary': (summary or '')[:255],
                })
                return rec
        except IntegrityError:
            # Otro request ya lo registró entre el check y el create
            return False
