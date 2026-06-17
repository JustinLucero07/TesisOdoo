from odoo import models, fields, api


class EstateAdvisorSocialPost(models.Model):
    _name = 'estate.advisor.fb.post'
    _description = 'Publicación Personal de Asesor en Redes Sociales'
    _order = 'published_date desc'

    property_id = fields.Many2one(
        'estate.property', string='Propiedad',
        required=True, ondelete='cascade', index=True)
    user_id = fields.Many2one(
        'res.users', string='Asesor',
        required=True, default=lambda self: self.env.user,
        index=True)
    platform = fields.Selection([
        ('facebook', 'Facebook Personal'),
        ('instagram', 'Instagram Personal'),
    ], string='Plataforma', required=True, default='facebook', index=True)
    published_date = fields.Datetime(
        string='Fecha de Publicación',
        required=True, default=fields.Datetime.now)
    url = fields.Char(
        string='Enlace al Post',
        help='URL opcional del post publicado')
    notes = fields.Text(
        string='Observaciones',
        help='Alcance, comentarios recibidos, me gustas, etc.')

    @api.depends('platform', 'user_id', 'property_id', 'published_date')
    def _compute_display_name(self):
        platforms = dict(self._fields['platform'].selection)
        for rec in self:
            date_str = rec.published_date.strftime('%d/%m/%Y') if rec.published_date else ''
            plat = platforms.get(rec.platform, rec.platform or '')
            prop = rec.property_id.name or ''
            user = rec.user_id.name or ''
            rec.display_name = f'[{plat}] {user} – {prop} ({date_str})'
