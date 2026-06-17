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

    sale_amount = fields.Float(string='Monto de la Venta/Renta',
                               help='Valor total de la transacción que genera esta comisión.')
    commission_pct = fields.Float(string='Porcentaje de Comisión (%)', default=5.0,
                                  help='Porcentaje aplicado sobre el monto de la venta.')
    amount = fields.Float(string='Monto de Comisión', required=True,
                          compute='_compute_commission_amount', store=True, readonly=False)
    company_currency = fields.Many2one(
        'res.currency', string='Moneda',
        default=lambda self: self.env.company.currency_id)
    date = fields.Date(string='Fecha', default=fields.Date.context_today)

    type = fields.Selection([
        ('sale', 'Venta'),
        ('rent', 'Arrendamiento (1er mes)'),
        ('bonus', 'Bono/Premio')
    ], string='Tipo de Comisión', required=True, default='sale')

    @api.depends('sale_amount', 'commission_pct')
    def _compute_commission_amount(self):
        for rec in self:
            if rec.sale_amount and rec.commission_pct:
                rec.amount = rec.sale_amount * (rec.commission_pct / 100.0)

    @api.onchange('property_id', 'type')
    def _onchange_property_autofill(self):
        """Al elegir la propiedad, trae automáticamente su monto (precio o canon
        de arriendo) y su porcentaje de comisión. El Monto de Comisión se
        recalcula solo (sale_amount × commission_pct)."""
        if not self.property_id:
            return
        prop = self.property_id
        if self.type == 'rent':
            self.sale_amount = prop.rental_price or prop.price or 0.0
        else:
            self.sale_amount = prop.price or 0.0
        if prop.commission_percentage:
            self.commission_pct = prop.commission_percentage
        if not self.user_id and prop.user_id:
            self.user_id = prop.user_id

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

    # --- Constancia del pago al asesor ---
    payment_date = fields.Date(string='Fecha de Pago', readonly=True, copy=False,
        help='Fecha en que se pagó la comisión al asesor.')
    payment_method = fields.Selection([
        ('transfer', 'Transferencia'),
        ('cash', 'Efectivo'),
        ('check', 'Cheque'),
        ('other', 'Otro'),
    ], string='Forma de Pago', copy=False)
    payment_reference = fields.Char(string='Comprobante / Referencia', copy=False,
        help='Nº de transferencia, recibo o comprobante del pago.')
    paid_by_id = fields.Many2one('res.users', string='Pagado por', readonly=True, copy=False)

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

    def action_register_payment(self):
        """Registra el pago de la comisión al asesor y deja constancia.
        Requiere fecha y forma de pago (capturadas en el formulario)."""
        for rec in self:
            if rec.state == 'paid':
                raise UserError('Esta comisión ya está marcada como Pagada.')
            if rec.state == 'cancelled':
                raise UserError('No se puede pagar una comisión cancelada.')
            if not rec.payment_method:
                raise UserError(
                    'Indica la Forma de Pago antes de registrar el pago '
                    '(pestaña/grupo "Pago al Asesor").')
            rec.write({
                'state': 'paid',
                'payment_date': rec.payment_date or fields.Date.context_today(rec),
                'paid_by_id': self.env.user.id,
            })
            metodo = dict(rec._fields['payment_method'].selection).get(rec.payment_method, '')
            ref = f" (Ref: {rec.payment_reference})" if rec.payment_reference else ''
            rec.message_post(
                body=(f"<b>Comisión PAGADA</b> al asesor <b>{rec.user_id.name}</b> "
                      f"por <b>${rec.amount:,.2f}</b> el {rec.payment_date} "
                      f"vía {metodo}{ref}. Registrado por {self.env.user.name}."))
        return True

    def action_reset_to_approved(self):
        """Revierte un pago registrado por error (vuelve a Aprobada)."""
        for rec in self:
            if rec.state != 'paid':
                raise UserError('Solo se pueden revertir comisiones Pagadas.')
            rec.write({'state': 'approved', 'payment_date': False,
                       'payment_method': False, 'payment_reference': False,
                       'paid_by_id': False})
            rec.message_post(body=f"Pago de comisión REVERTIDO por {self.env.user.name}.")
        return True

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
