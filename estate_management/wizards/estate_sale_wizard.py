from odoo import models, fields, api
from odoo.exceptions import UserError


class EstateSaleWizard(models.TransientModel):
    _name = 'estate.sale.wizard'
    _description = 'Asistente de Venta de Propiedad'

    property_id = fields.Many2one('estate.property', string='Propiedad', required=True, readonly=True)
    offer_type = fields.Selection(related='property_id.offer_type', readonly=True)
    buyer_id = fields.Many2one('res.partner', string='Comprador', required=True)
    sale_price = fields.Float(string='Precio de Cierre', required=True)
    date_sold = fields.Date(string='Fecha de Cierre', default=fields.Date.today, required=True)
    sold_by = fields.Selection([
        ('agency', 'Agencia'),
        ('owner', 'Propietario'),
        ('external', 'Externo'),
    ], string='Cerrado por', default='agency', required=True)
    commission_pct = fields.Float(string='Comisión (%)', required=True)
    commission_amount = fields.Float(string='Monto Comisión', compute='_compute_commission_amount')

    @api.depends('sale_price', 'commission_pct')
    def _compute_commission_amount(self):
        for rec in self:
            rec.commission_amount = (rec.sale_price or 0.0) * (rec.commission_pct / 100.0)

    def action_confirm_sale(self):
        self.ensure_one()
        prop = self.property_id
        if prop.state not in ('available', 'reserved'):
            raise UserError('Solo se puede vender una propiedad Disponible o Reservada.')
        prop.write({
            'state': 'sold',
            'offer_type': 'sale',
            'buyer_id': self.buyer_id.id,
            'price': self.sale_price,
            'commission_percentage': self.commission_pct,
            'date_sold': self.date_sold,
            'sold_by': self.sold_by,
        })
        prop._create_commission_records('sale', self.commission_amount, self.sale_price, self.commission_pct)
        return {'type': 'ir.actions.act_window_close'}
