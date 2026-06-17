# -*- coding: utf-8 -*-
"""B5: persistencia del feedback (votos positivos/negativos) del chat IA.

Cada vez que el usuario valora una respuesta del asistente, se guarda aquí.
Sirve para detectar prompts/respuestas malas y mejorar el sistema con datos
reales en vez de solo un estado visual efímero.
"""
from odoo import models, fields, api


class EstateAIFeedback(models.Model):
    _name = 'estate.ai.feedback'
    _description = 'Feedback de Respuestas IA'
    _order = 'create_date desc'

    user_id = fields.Many2one(
        'res.users', string='Usuario',
        default=lambda self: self.env.user, required=True, index=True)
    vote = fields.Selection([
        ('up', 'Útil'),
        ('down', 'No útil'),
    ], string='Valoración', required=True, index=True)
    session_id = fields.Char(string='Sesión', index=True)
    question = fields.Text(string='Pregunta del usuario')
    answer = fields.Text(string='Respuesta de la IA')
    page_context = fields.Char(string='Contexto (módulo)')

    @api.model
    def record_vote(self, vote, **vals):
        """Crea o actualiza el voto. Llamado desde el endpoint del chat."""
        if vote not in ('up', 'down'):
            return False
        session_id = vals.get('session_id')
        answer = (vals.get('answer') or '')[:2000]
        # Evita duplicados: si ya votó esta misma respuesta en la sesión, actualiza
        existing = self.search([
            ('user_id', '=', self.env.uid),
            ('session_id', '=', session_id),
            ('answer', '=', answer),
        ], limit=1)
        data = {
            'vote': vote,
            'session_id': session_id,
            'question': (vals.get('question') or '')[:2000],
            'answer': answer,
            'page_context': (vals.get('page_context') or '')[:200],
        }
        if existing:
            existing.write({'vote': vote})
            return existing.id
        return self.create(data).id
