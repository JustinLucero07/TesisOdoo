from odoo import models, fields, api
from odoo.exceptions import UserError


class EstateCommission(models.Model):
    _name = 'estate.commission'
    _description = 'Comisión Inmobiliaria'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string='Referencia', required=True, copy=False, readonly=True, default='NUEVO')
    property_id = fields.Many2one('estate.property', string='Propiedad', required=True)
    user_id = fields.Many2one('res.users', string='Asesor', required=True, default=lambda self: self.env.user)

    amount = fields.Float(string='Monto de Comisión', required=True)
    company_currency = fields.Many2one(
        'res.currency', string='Moneda',
        default=lambda self: self.env.company.currency_id)
    date = fields.Date(string='Fecha', default=fields.Date.context_today)

    type = fields.Selection([
        ('sale', 'Venta'),
        ('rental', 'Alquiler'),
        ('bonus', 'Bono/Premio')
    ], string='Tipo de Comisión', required=True, default='sale')

    state = fields.Selection([
        ('draft', 'Borrador'),
        ('approved', 'Aprobada'),
        ('paid', 'Pagada'),
        ('cancelled', 'Cancelada')
    ], string='Estado', default='draft', tracking=True)

    invoice_id = fields.Many2one(
        'account.move', string='Factura de Comisión',
        readonly=True, copy=False,
        domain=[('move_type', '=', 'in_invoice')])
    invoice_state = fields.Selection(
        related='invoice_id.payment_state', string='Estado de Factura', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'NUEVO') == 'NUEVO':
                vals['name'] = self.env['ir.sequence'].next_by_code('estate.commission') or 'COM'
        return super().create(vals_list)

    def action_approve(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError('Solo se pueden aprobar comisiones en estado Borrador.')
        self.write({'state': 'approved'})

    def action_cancel(self):
        for rec in self:
            if rec.state == 'paid':
                raise UserError('No se puede cancelar una comisión ya pagada.')
        self.write({'state': 'cancelled'})

    def action_generate_invoice(self):
        """Genera una factura de proveedor (vendor bill) para pagar la comisión al asesor."""
        self.ensure_one()
        if self.invoice_id:
            raise UserError('Esta comisión ya tiene una factura generada.')
        if self.state not in ('approved', 'draft'):
            raise UserError('Solo se puede generar factura para comisiones en borrador o aprobadas.')

        partner = self.user_id.partner_id
        if not partner:
            raise UserError('El asesor no tiene un contacto (partner) asociado.')

        # Buscar cuenta de comisiones o usar la genérica de gastos
        commission_account = self.env['account.account'].search([
            ('account_type', '=', 'expense'),
            ('company_id', '=', self.env.company.id),
        ], limit=1)

        invoice_vals = {
            'move_type': 'in_invoice',
            'partner_id': partner.id,
            'invoice_date': self.date or fields.Date.context_today(self),
            'estate_transaction_type': 'commission',
            'invoice_line_ids': [(0, 0, {
                'name': f'Comisión {dict(self._fields["type"].selection)[self.type]} — {self.property_id.title or self.name}',
                'quantity': 1.0,
                'price_unit': self.amount,
                'account_id': commission_account.id if commission_account else False,
            })],
            'narration': f'Comisión generada desde {self.name} para {partner.name}',
        }
        invoice = self.env['account.move'].create(invoice_vals)
        self.write({'invoice_id': invoice.id, 'state': 'approved'})
        self.message_post(
            body=f'Factura de comisión <b>{invoice.name or "borrador"}</b> generada para <b>{partner.name}</b>.',
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_invoice(self):
        self.ensure_one()
        if not self.invoice_id:
            raise UserError('No hay factura generada para esta comisión.')
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
