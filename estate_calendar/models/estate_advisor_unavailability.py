from odoo import models, fields, api
from odoo.exceptions import ValidationError


class EstateAdvisorUnavailability(models.Model):
    _name = 'estate.advisor.unavailability'
    _description = 'Días no disponibles del asesor'
    _order = 'date_from desc'

    user_id = fields.Many2one(
        'res.users',
        string='Asesor',
        required=True,
        default=lambda self: self.env.user,
        domain=[('share', '=', False), ('active', '=', True)],
    )
    date_from = fields.Date(string='Desde', required=True)
    date_to = fields.Date(string='Hasta', required=True)
    reason = fields.Char(string='Motivo')

    @api.depends('user_id', 'date_from', 'date_to')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.user_id.name}: {rec.date_from} → {rec.date_to}"

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_from > rec.date_to:
                raise ValidationError('La fecha de inicio debe ser anterior o igual a la fecha de fin.')
