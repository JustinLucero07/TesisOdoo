from odoo import models, fields, api


class EstateAppraisal(models.Model):
    """Solicitud de tasación / avalúo formal de una propiedad."""
    _name = 'estate.appraisal'
    _description = 'Solicitud de Tasación'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_requested desc'

    name = fields.Char(string='Referencia', readonly=True, copy=False, default='Nuevo')
    property_id = fields.Many2one('estate.property', string='Propiedad', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Solicitante', required=True, tracking=True)
    user_id = fields.Many2one('res.users', string='Tasador Asignado',
                              default=lambda self: self.env.user, tracking=True)

    request_reason = fields.Selection([
        ('sale',      'Preparar para Venta'),
        ('rent',      'Preparar para Alquiler'),
        ('insurance', 'Seguro / Hipoteca'),
        ('legal',     'Trámite Legal / Sucesión'),
        ('other',     'Otro'),
    ], string='Motivo de Tasación', required=True, default='sale')

    date_requested = fields.Date(string='Fecha de Solicitud', default=fields.Date.today)
    date_scheduled = fields.Date(string='Visita Programada', tracking=True)
    date_completed = fields.Date(string='Fecha de Entrega', tracking=True)

    # Resultado
    market_value = fields.Float(string='Valor de Mercado Tasado', tracking=True)
    commercial_value = fields.Float(string='Valor Comercial', tracking=True)
    replacement_value = fields.Float(string='Valor de Reposición', tracking=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    methodology = fields.Selection([
        ('comparative', 'Método Comparativo de Mercado'),
        ('income',      'Método de Capitalización de Rentas'),
        ('cost',        'Método de Costo de Reposición'),
    ], string='Metodología Utilizada', default='comparative')

    appraisal_notes = fields.Html(string='Informe de Tasación')
    observations = fields.Text(string='Observaciones Generales')

    # Comparación con precio actual
    current_price = fields.Float(related='property_id.price', string='Precio Actual', readonly=True)
    price_variance_pct = fields.Float(
        string='Variación vs Precio Actual (%)', compute='_compute_variance', store=True)

    state = fields.Selection([
        ('requested',  'Solicitada'),
        ('scheduled',  'Visita Programada'),
        ('in_progress','En Elaboración'),
        ('completed',  'Completada'),
        ('cancelled',  'Cancelada'),
    ], string='Estado', default='requested', tracking=True)

    @api.depends('market_value', 'current_price')
    def _compute_variance(self):
        for rec in self:
            if rec.current_price and rec.current_price > 0 and rec.market_value:
                rec.price_variance_pct = ((rec.market_value - rec.current_price) / rec.current_price) * 100
            else:
                rec.price_variance_pct = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code('estate.appraisal') or 'AVAL-001'
        return super().create(vals_list)

    def action_schedule(self):
        self.write({'state': 'scheduled'})

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_complete(self):
        self.write({'state': 'completed', 'date_completed': fields.Date.today()})
        for rec in self:
            if rec.market_value and rec.property_id:
                # Auto-actualizar AVM de la propiedad con el valor tasado
                rec.property_id.write({
                    'avm_estimated_price': rec.market_value,
                    'avm_last_calculated': fields.Datetime.now(),
                })
                # Determinar status AVM comparando con precio actual
                if rec.property_id.price and rec.property_id.price > 0:
                    ratio = rec.market_value / rec.property_id.price
                    if 0.90 <= ratio <= 1.10:
                        status = 'fair'
                    elif ratio > 1.10:
                        status = 'low'
                    else:
                        status = 'high'
                    rec.property_id.write({'avm_status': status})
                rec.property_id.message_post(
                    body=f'Tasación <b>{rec.name}</b> completada. Valor de mercado: '
                         f'<b>${rec.market_value:,.2f}</b>. '
                         f'El precio AVM de la propiedad ha sido actualizado automáticamente.'
                )

    def action_cancel(self):
        self.write({'state': 'cancelled'})
