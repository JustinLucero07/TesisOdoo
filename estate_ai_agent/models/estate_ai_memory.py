from odoo import models, fields, api
from datetime import date


class EstateAIMemory(models.Model):
    _name = 'estate.ai.memory'
    _description = 'Memoria Persistente del Agente IA'
    _order = 'create_date desc'

    user_id = fields.Many2one(
        'res.users', string='Usuario', required=True,
        default=lambda self: self.env.user,
        ondelete='cascade'
    )
    memory_type = fields.Selection([
        ('preference', 'Preferencia del usuario'),
        ('fact', 'Hecho importante'),
        ('client', 'Dato del cliente'),
        ('alert', 'Alerta / Recordatorio'),
        ('context', 'Contexto del negocio'),
    ], string='Tipo', required=True, default='fact')

    title = fields.Char(string='Título', required=True)
    content = fields.Text(string='Contenido', required=True)

    expires_at = fields.Date(string='Expira en')
    is_active = fields.Boolean(string='Activa', default=True, compute='_compute_is_active', store=True)
    tags = fields.Char(string='Etiquetas', help='Palabras clave separadas por comas')

    # Related entity (optional)
    lead_id = fields.Many2one('crm.lead', string='Lead relacionado', ondelete='set null')
    property_id = fields.Many2one('estate.property', string='Propiedad relacionada', ondelete='set null')
    partner_id = fields.Many2one('res.partner', string='Contacto relacionado', ondelete='set null')

    @api.depends('expires_at')
    def _compute_is_active(self):
        today = date.today()
        for rec in self:
            if rec.expires_at and rec.expires_at < today:
                rec.is_active = False
            else:
                rec.is_active = True

    def name_get(self):
        return [(rec.id, f"[{rec.memory_type}] {rec.title}") for rec in self]

    @api.model
    def get_active_memories_for_user(self, user_id, limit=20):
        """Returns active memories for a given user, ordered by recency."""
        memories = self.search([
            ('user_id', '=', user_id),
            ('is_active', '=', True),
        ], limit=limit, order='create_date desc')
        return memories.read(['memory_type', 'title', 'content', 'tags', 'create_date'])
