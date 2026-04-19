from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    iess_personal_pct = fields.Float(
        string='Aporte Personal IESS (%)',
        config_parameter='estate_payroll.iess_personal_pct',
        default=9.45,
        help='Porcentaje de aporte personal al IESS. Valor actual en Ecuador: 9.45%')
