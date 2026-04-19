from odoo import models, fields


class EstateClientInteraction(models.Model):
    _name = 'estate.client.interaction'
    _description = 'Interacción con Cliente'
    _order = 'date desc'

    partner_id = fields.Many2one(
        'res.partner', string='Cliente', required=True, ondelete='cascade')
    date = fields.Datetime(
        string='Fecha', default=fields.Datetime.now, required=True)
    interaction_type = fields.Selection([
        ('call', 'Llamada'),
        ('email', 'Correo'),
        ('visit', 'Visita'),
        ('meeting', 'Reunión'),
        ('whatsapp', 'WhatsApp'),
        ('other', 'Otro'),
    ], string='Tipo', required=True, default='call')
    summary = fields.Text(string='Resumen', required=True)
    user_id = fields.Many2one(
        'res.users', string='Responsable',
        default=lambda self: self.env.user)
    lead_id = fields.Many2one(
        'crm.lead', string='Oportunidad / Lead',
        help='Lead CRM al que pertenece esta interacción.')
    property_id = fields.Many2one(
        'estate.property', string='Propiedad Relacionada')
