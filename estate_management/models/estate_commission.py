from odoo import models, fields, api
from odoo.exceptions import UserError


class EstateCommission(models.Model):
    _name = 'estate.commission'
    _description = 'Comisión Inmobiliaria'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string='Referencia', required=True, copy=False, readonly=True, default='NUEVO')
    lead_id = fields.Many2one(
        'crm.lead', string='Oportunidad (CRM)', tracking=True,
        help='Oportunidad o Lead del CRM de donde proviene esta comisión.')
    property_id = fields.Many2one('estate.property', string='Propiedad', required=False)
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

    @api.onchange('lead_id')
    def _onchange_lead_id_autofill(self):
        """Al seleccionar una oportunidad/lead del CRM, autocompleta la propiedad,
        el asesor, el tipo de comisión, el monto de la venta/renta y el porcentaje."""
        if not self.lead_id:
            return
        lead = self.lead_id
        if lead.target_property_id:
            self.property_id = lead.target_property_id
            prop = lead.target_property_id
            self.type = 'rent' if prop.offer_type == 'rent' else 'sale'
            if self.type == 'rent':
                self.sale_amount = lead.client_budget or prop.rental_price or prop.price or 0.0
            else:
                self.sale_amount = lead.client_budget or prop.price or 0.0
            if prop.commission_percentage:
                pct = prop.commission_percentage
                if prop.is_allied_property:
                    allied_ratio = (prop.allied_split_pct or 50.0) / 100.0
                    pct = pct * allied_ratio
                if prop.co_user_id and lead.user_id == prop.co_user_id and 0 < prop.commission_split_pct < 100:
                    pct = pct * (prop.commission_split_pct / 100.0)
                elif prop.co_user_id and lead.user_id == prop.user_id and 0 < prop.commission_split_pct < 100:
                    pct = pct * ((100.0 - prop.commission_split_pct) / 100.0)
                self.commission_pct = pct
        else:
            if lead.client_budget:
                self.sale_amount = lead.client_budget
            if lead.expected_commission and lead.client_budget:
                self.commission_pct = (lead.expected_commission / lead.client_budget) * 100.0
                
        if lead.user_id:
            self.user_id = lead.user_id

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
            pct = prop.commission_percentage
            if prop.is_allied_property:
                allied_ratio = (prop.allied_split_pct or 50.0) / 100.0
                pct = pct * allied_ratio
            self.commission_pct = pct
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
    payment_date = fields.Date(string='Fecha de Pago', default=fields.Date.context_today, copy=False,
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

    @api.constrains('amount', 'sale_amount')
    def _check_positive_amounts(self):
        for rec in self:
            if rec.amount < 0:
                raise UserError('El monto de la comisión no puede ser negativo.')
            if rec.sale_amount < 0:
                raise UserError('El monto de venta/renta no puede ser negativo.')

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
            if rec.amount <= 0:
                raise UserError('No se puede aprobar una comisión cuyo monto sea $0.00 o negativo.')
        self.write({'state': 'approved'})

    def action_cancel(self):
        for rec in self:
            if rec.state == 'paid':
                raise UserError('No se puede cancelar una comisión ya pagada.')
            if rec.state == 'draft' and rec.invoice_id and rec.invoice_id.state != 'cancel':
                rec.invoice_id.button_cancel()
        self.write({'state': 'cancelled'})

    def action_register_payment(self):
        """Registra el pago de la comisión al asesor y deja constancia.
        Si la factura de proveedor no ha sido creada, la genera automáticamente,
        la valida (action_post) y le registra el pago contable para dejarla en estado Pagado."""
        for rec in self:
            if rec.state == 'paid':
                raise UserError('Esta comisión ya está marcada como Pagada.')
            if rec.state == 'cancelled':
                raise UserError('No se puede pagar una comisión cancelada.')
            if rec.amount <= 0:
                raise UserError('No se puede registrar pago para una comisión cuyo monto sea $0.00 o negativo.')
            if not rec.payment_method:
                raise UserError(
                    'Indica la Forma de Pago en la sección "Pago al Asesor (Constancia)" antes de registrar el pago.')

            # 1. Generar factura de comisión si no existe
            if not rec.invoice_id:
                partner = rec.user_id.partner_id
                if not partner:
                    raise UserError('El asesor no tiene un contacto (partner) asociado.')
                commission_account = self.env['account.account'].search([
                    ('account_type', '=', 'expense'),
                    ('company_ids', 'in', self.env.company.id),
                ], limit=1)
                invoice_vals = {
                    'move_type': 'in_invoice',
                    'partner_id': partner.id,
                    'invoice_date': rec.payment_date or fields.Date.context_today(rec),
                    'estate_transaction_type': 'commission',
                    'invoice_line_ids': [(0, 0, {
                        'name': f'Comisión {dict(rec._fields["type"].selection)[rec.type]} — {rec.property_id.title or rec.name}',
                        'quantity': 1.0,
                        'price_unit': rec.amount,
                        'account_id': commission_account.id if commission_account else False,
                    })],
                    'narration': f'Comisión generada desde {rec.name} para {partner.name}',
                }
                invoice = self.env['account.move'].create(invoice_vals)
                rec.invoice_id = invoice.id

            # 2. Confirmar / Publicar la factura contable si está en borrador
            if rec.invoice_id.state == 'draft':
                rec.invoice_id.action_post()

            # 3. Registrar el pago contable en la factura (si no está ya pagada)
            if rec.invoice_id.payment_state not in ('paid', 'in_payment'):
                journal_type = 'bank' if rec.payment_method in ('transfer', 'check') else 'cash'
                journal = self.env['account.journal'].search([
                    ('type', '=', journal_type),
                    ('company_id', '=', self.env.company.id),
                ], limit=1)
                if not journal:
                    journal = self.env['account.journal'].search([
                        ('type', 'in', ('bank', 'cash')),
                        ('company_id', '=', self.env.company.id),
                    ], limit=1)
                if journal:
                    payment_register = self.env['account.payment.register'].with_context(
                        active_model='account.move',
                        active_ids=[rec.invoice_id.id]
                    ).create({
                        'payment_date': rec.payment_date or fields.Date.context_today(rec),
                        'journal_id': journal.id,
                        'communication': rec.payment_reference or rec.name,
                    })
                    payment_register._create_payments()

            # 4. Actualizar estado y constancia de la comisión
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
                      f"vía {metodo}{ref}. Factura contable <b>{rec.invoice_id.name}</b> autogenerada y conciliada. "
                      f"Registrado por {self.env.user.name}."))
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
            ('company_ids', 'in', self.env.company.id),
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
