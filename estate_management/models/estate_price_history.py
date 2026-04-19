from odoo import models, fields, api


class EstatePropertyPriceHistory(models.Model):
    """Historial de cambios de precio de una propiedad."""
    _name = 'estate.property.price.history'
    _description = 'Historial de Precio'
    _order = 'date desc, id desc'

    property_id = fields.Many2one('estate.property', string='Propiedad', required=True, ondelete='cascade')
    date = fields.Datetime(string='Fecha del Cambio', default=fields.Datetime.now, required=True)
    old_price = fields.Float(string='Precio Anterior')
    new_price = fields.Float(string='Precio Nuevo')
    change_pct = fields.Float(string='Variación (%)', compute='_compute_change', store=True)
    change_reason = fields.Selection([
        ('initial',    'Precio Inicial'),
        ('reduction',  'Reducción para Acelerar Venta'),
        ('increase',   'Aumento por Mejoras'),
        ('market',     'Ajuste de Mercado'),
        ('avm',        'Ajuste por AVM'),
        ('appraisal',  'Resultado de Tasación'),
        ('negotiation','Negociación con Cliente'),
        ('other',      'Otro'),
    ], string='Motivo', default='market')
    user_id = fields.Many2one('res.users', string='Modificado por',
                              default=lambda self: self.env.user, readonly=True)
    notes = fields.Char(string='Notas')

    @api.depends('old_price', 'new_price')
    def _compute_change(self):
        for rec in self:
            if rec.old_price and rec.old_price > 0:
                rec.change_pct = ((rec.new_price - rec.old_price) / rec.old_price) * 100
            else:
                rec.change_pct = 0.0
