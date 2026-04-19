import calendar

from odoo import models, fields, api
from odoo.exceptions import UserError


class EstatePayrollLine(models.Model):
    _name = 'estate.payroll.line'
    _description = 'Nómina de Asesor Inmobiliario'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'period_year desc, period_month desc, id desc'

    name = fields.Char(
        string='Referencia', required=True, copy=False,
        readonly=True, default='NUEVO')

    employee_id = fields.Many2one(
        'hr.employee', string='Empleado', required=True, tracking=True)
    user_id = fields.Many2one(
        'res.users', string='Usuario Asesor',
        related='employee_id.user_id', store=True, readonly=True)

    period_month = fields.Selection([
        ('1', 'Enero'), ('2', 'Febrero'), ('3', 'Marzo'),
        ('4', 'Abril'), ('5', 'Mayo'), ('6', 'Junio'),
        ('7', 'Julio'), ('8', 'Agosto'), ('9', 'Septiembre'),
        ('10', 'Octubre'), ('11', 'Noviembre'), ('12', 'Diciembre'),
    ], string='Mes', required=True, tracking=True)
    period_year = fields.Integer(
        string='Año', required=True,
        default=lambda self: fields.Date.context_today(self).year)

    # ── Haberes ──────────────────────────────────────────────────────────
    base_salary = fields.Float(string='Sueldo Base', required=True, default=0.0)
    commission_bonus = fields.Float(string='Bono de Comisiones', default=0.0)
    transport_allowance = fields.Float(string='Subsidio de Transporte', default=0.0)
    other_income = fields.Float(string='Otros Ingresos', default=0.0)
    gross_salary = fields.Float(
        string='Total Haberes', compute='_compute_gross', store=True)

    # ── Deducciones ───────────────────────────────────────────────────────
    iess_personal = fields.Float(
        string='Aporte Personal IESS', compute='_compute_iess', store=True)
    advance_deduction = fields.Float(string='Anticipo / Préstamo', default=0.0)
    other_deduction = fields.Float(string='Otras Deducciones', default=0.0)
    total_deductions = fields.Float(
        string='Total Deducciones', compute='_compute_deductions', store=True)

    # ── Neto ──────────────────────────────────────────────────────────────
    net_salary = fields.Float(
        string='Sueldo Neto a Pagar', compute='_compute_net', store=True)

    currency_id = fields.Many2one(
        'res.currency', string='Moneda',
        default=lambda self: self.env.company.currency_id)

    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmado'),
        ('paid', 'Pagado'),
        ('cancel', 'Cancelado'),
    ], string='Estado', default='draft', tracking=True)

    invoice_id = fields.Many2one(
        'account.move', string='Factura de Pago',
        readonly=True, copy=False)
    invoice_state = fields.Selection(
        related='invoice_id.payment_state', string='Estado Factura', readonly=True)

    notes = fields.Text(string='Notas')

    # ── Cómputos ──────────────────────────────────────────────────────────

    @api.depends('base_salary', 'commission_bonus', 'transport_allowance', 'other_income')
    def _compute_gross(self):
        for rec in self:
            rec.gross_salary = (
                rec.base_salary + rec.commission_bonus +
                rec.transport_allowance + rec.other_income
            )

    @api.depends('base_salary')
    def _compute_iess(self):
        pct = float(self.env['ir.config_parameter'].sudo().get_param(
            'estate_payroll.iess_personal_pct', '9.45'))
        for rec in self:
            rec.iess_personal = round(rec.base_salary * pct / 100, 2)

    @api.depends('iess_personal', 'advance_deduction', 'other_deduction')
    def _compute_deductions(self):
        for rec in self:
            rec.total_deductions = (
                rec.iess_personal + rec.advance_deduction + rec.other_deduction
            )

    @api.depends('gross_salary', 'total_deductions')
    def _compute_net(self):
        for rec in self:
            rec.net_salary = rec.gross_salary - rec.total_deductions

    # ── CRUD ──────────────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'NUEVO') == 'NUEVO':
                vals['name'] = self.env['ir.sequence'].next_by_code('estate.payroll.line') or 'NOM'
        return super().create(vals_list)

    # ── Acciones ──────────────────────────────────────────────────────────

    def action_compute_commissions(self):
        """Calcula el bono de comisiones sumando las comisiones aprobadas/pagadas del período."""
        for rec in self:
            if rec.state != 'draft':
                raise UserError('Solo se puede recalcular comisiones en nóminas en borrador.')
            if not rec.user_id:
                raise UserError(f'El empleado {rec.employee_id.name} no tiene usuario vinculado.')
            month = int(rec.period_month)
            year = rec.period_year
            date_from = fields.Date.to_date(f'{year}-{month:02d}-01')
            last_day = calendar.monthrange(year, month)[1]
            date_to = fields.Date.to_date(f'{year}-{month:02d}-{last_day}')
            commissions = self.env['estate.commission'].search([
                ('user_id', '=', rec.user_id.id),
                ('state', 'in', ('approved', 'paid')),
                ('date', '>=', date_from),
                ('date', '<=', date_to),
            ])
            rec.commission_bonus = sum(commissions.mapped('amount'))
            names = ', '.join(commissions.mapped('name')) or 'ninguna'
            rec.message_post(
                body=f'Bono de comisiones recalculado: <b>${rec.commission_bonus:,.2f}</b> '
                     f'({len(commissions)} comisiones: {names})',
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError('Solo se pueden confirmar nóminas en borrador.')
        self.write({'state': 'confirmed'})

    def action_cancel(self):
        for rec in self:
            if rec.state == 'paid':
                raise UserError('No se puede cancelar una nómina ya pagada.')
        self.write({'state': 'cancel'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    def action_generate_payment_invoice(self):
        """Genera un vendor bill para pagar el sueldo neto al empleado."""
        self.ensure_one()
        if self.invoice_id:
            raise UserError('Esta nómina ya tiene una factura generada.')
        if self.state != 'confirmed':
            raise UserError('Confirma la nómina antes de generar la factura.')

        partner = self.employee_id.address_home_id or self.employee_id.user_id.partner_id
        if not partner:
            raise UserError('El empleado no tiene dirección particular (partner) configurada.')

        expense_account = self.env['account.account'].search([
            ('account_type', '=', 'expense'),
            ('company_id', '=', self.env.company.id),
        ], limit=1)

        month_label = dict(self._fields['period_month'].selection).get(self.period_month, self.period_month)
        invoice_vals = {
            'move_type': 'in_invoice',
            'partner_id': partner.id,
            'invoice_date': fields.Date.context_today(self),
            'narration': f'Pago de nómina {month_label} {self.period_year} — {self.employee_id.name}',
            'invoice_line_ids': [
                (0, 0, {
                    'name': f'Sueldo Base {month_label} {self.period_year}',
                    'quantity': 1.0,
                    'price_unit': self.base_salary,
                    'account_id': expense_account.id if expense_account else False,
                }),
            ],
        }
        if self.commission_bonus:
            invoice_vals['invoice_line_ids'].append((0, 0, {
                'name': f'Bono Comisiones {month_label} {self.period_year}',
                'quantity': 1.0,
                'price_unit': self.commission_bonus,
                'account_id': expense_account.id if expense_account else False,
            }))
        if self.transport_allowance:
            invoice_vals['invoice_line_ids'].append((0, 0, {
                'name': f'Subsidio Transporte {month_label} {self.period_year}',
                'quantity': 1.0,
                'price_unit': self.transport_allowance,
                'account_id': expense_account.id if expense_account else False,
            }))
        if self.iess_personal:
            invoice_vals['invoice_line_ids'].append((0, 0, {
                'name': f'Descuento IESS Personal 9.45% {month_label} {self.period_year}',
                'quantity': 1.0,
                'price_unit': -self.iess_personal,
                'account_id': expense_account.id if expense_account else False,
            }))
        if self.advance_deduction:
            invoice_vals['invoice_line_ids'].append((0, 0, {
                'name': f'Descuento Anticipo/Préstamo {month_label} {self.period_year}',
                'quantity': 1.0,
                'price_unit': -self.advance_deduction,
                'account_id': expense_account.id if expense_account else False,
            }))

        invoice = self.env['account.move'].create(invoice_vals)
        self.write({'invoice_id': invoice.id, 'state': 'paid'})
        self.message_post(
            body=f'Factura de nómina <b>{invoice.name or "borrador"}</b> generada. Neto: <b>${self.net_salary:,.2f}</b>',
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
            raise UserError('No hay factura generada para esta nómina.')
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
