# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError

from ..tools.invoice_modes import INVOICE_MODES, vat_amount


class EstateCommissionPayoutWizard(models.TransientModel):
    _name = 'estate.commission.payout.wizard'
    _description = 'Pagar comisión a los asesores'

    commission_id = fields.Many2one('estate.commission', required=True, readonly=True)
    mode = fields.Selection([
        ('split', 'Generar el reparto y pagar'),
        ('pending', 'Pagar a los asesores pendientes'),
        ('single', 'Pagar a este asesor'),
    ], required=True, readonly=True)
    payment_method = fields.Selection(
        selection=lambda self: self.env['estate.commission']._fields['payment_method'].selection,
        string='¿Cómo se les paga?', default='transfer',
        help='Forma de pago propuesta; cada asesor puede tener la suya.')
    payment_date = fields.Date(string='Fecha de pago',
                               default=fields.Date.context_today)
    payment_reference = fields.Char(string='Comprobante / Referencia',
                                    help='Nº de transferencia, recibo o cheque.')
    company_currency = fields.Many2one(related='commission_id.company_currency')

    line_ids = fields.One2many(
        'estate.commission.payout.line', 'wizard_id', string='Asesores a pagar')

    amount_base_total = fields.Monetary(
        string='Subtotal comisiones', currency_field='company_currency',
        compute='_compute_totals')
    amount_vat_total = fields.Monetary(
        string='Total IVA', currency_field='company_currency',
        compute='_compute_totals')
    amount_to_pay = fields.Monetary(
        string='Total a pagar a los asesores', currency_field='company_currency',
        compute='_compute_totals')
    advisor_count = fields.Integer(compute='_compute_totals')

    @api.depends('line_ids.amount_base', 'line_ids.amount_vat', 'line_ids.amount_total')
    def _compute_totals(self):
        for wiz in self:
            wiz.amount_base_total = sum(wiz.line_ids.mapped('amount_base'))
            wiz.amount_vat_total = sum(wiz.line_ids.mapped('amount_vat'))
            wiz.amount_to_pay = sum(wiz.line_ids.mapped('amount_total'))
            wiz.advisor_count = len(wiz.line_ids)

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        com_id = vals.get('commission_id') or self.env.context.get('default_commission_id')
        if not com_id:
            return vals
        com = self.env['estate.commission'].browse(com_id)
        mode = vals.get('mode') or self.env.context.get('default_mode')

        # Agrupar por asesor único para que el usuario solo elija una vez por asesor
        user_data = {}
        role_labels = dict(self.env['estate.commission.split']._fields['role'].selection)

        if mode == 'split':
            for line in com.split_line_ids.filtered(lambda l: l.user_id and l.amount > 0):
                uid = line.user_id.id
                if uid not in user_data:
                    user_data[uid] = {'user_id': uid, 'roles': [], 'amount': 0.0}
                r_name = role_labels.get(line.role, line.role)
                if r_name not in user_data[uid]['roles']:
                    user_data[uid]['roles'].append(r_name)
                user_data[uid]['amount'] += line.amount
        elif mode == 'pending':
            pend = com.child_commission_ids.filtered(lambda c: c.state in ('draft', 'approved'))
            for child in pend:
                uid = child.user_id.id
                if uid not in user_data:
                    user_data[uid] = {'user_id': uid, 'roles': [], 'amount': 0.0}
                r_name = role_labels.get(child.role, child.role)
                if r_name not in user_data[uid]['roles']:
                    user_data[uid]['roles'].append(r_name)
                user_data[uid]['amount'] += child.amount
        else:
            if com.user_id:
                uid = com.user_id.id
                r_name = role_labels.get(com.role, com.role) if com.role else 'Comisión'
                user_data[uid] = {'user_id': uid, 'roles': [r_name], 'amount': com.amount}

        method = (vals.get('payment_method') or self.env.context.get('default_payment_method')
                  or 'transfer')
        lines = []
        for uid, data in user_data.items():
            base = round(data['amount'], 2)
            lines.append((0, 0, {
                'user_id': uid,
                'roles': ', '.join(data['roles']),
                'amount_base': base,
                'invoice': 'without',
                'payment_method': method,
                'payment_date': fields.Date.context_today(self),
            }))
        vals['line_ids'] = lines
        return vals

    def _line_vals(self, user):
        """Cómo se le paga a `user`: lo que se puso en su recuadro."""
        line = self.line_ids.filtered(lambda l: l.user_id == user)[:1]
        if not line:
            return {'has_invoice': 'without', 'payment_method': self.payment_method or 'transfer',
                    'payment_date': self.payment_date, 'payment_reference': self.payment_reference}
        if not line.payment_method:
            raise UserError('Indica cómo se le paga a %s.' % user.name)
        return {
            'has_invoice': line.invoice,
            'payment_method': line.payment_method,
            'payment_date': line.payment_date or fields.Date.context_today(self),
            'payment_reference': line.payment_reference,
            'payment_bank_from': line.payment_bank_from,
            'payment_bank_to': line.payment_bank_to,
        }

    def action_confirm(self):
        self.ensure_one()
        com = self.commission_id

        if self.mode == 'split':
            lineas = com.split_line_ids.filtered(lambda l: l.user_id and l.amount > 0)
            if not lineas:
                raise UserError('Asigna al menos un asesor con monto en el reparto antes de pagar.')
            creadas = self.env['estate.commission']
            for linea in lineas:
                creadas |= self.env['estate.commission'].create(dict(self._line_vals(linea.user_id), **{
                    'property_id': com.property_id.id,
                    'lead_id': com.lead_id.id,
                    'user_id': linea.user_id.id,
                    'sale_amount': com.sale_amount,
                    'commission_pct': com.commission_pct * ((linea.percentage or 0.0) / 100.0),
                    'amount': linea.amount,
                    'role': linea.role,
                    'role_pct': linea.percentage,
                    'type': com.type,
                    'date': com.date,
                    'state': 'approved',
                    'parent_commission_id': com.id,
                }))
            com.state = 'split'
            creadas.action_register_payment()
            return com.action_view_children()

        if self.mode == 'pending':
            pendientes = com.child_commission_ids.filtered(
                lambda c: c.state in ('draft', 'approved'))
            if not pendientes:
                raise UserError('Todas las comisiones de este reparto ya están pagadas.')
            for hija in pendientes:
                hija.write(self._line_vals(hija.user_id))
            pendientes.action_register_payment()
            return com.action_view_children()

        com.write(self._line_vals(com.user_id))
        com.action_register_payment()
        return {'type': 'ir.actions.act_window_close'}


class EstateCommissionPayoutLine(models.TransientModel):
    _name = 'estate.commission.payout.line'
    _description = 'Línea de pago por asesor'

    wizard_id = fields.Many2one('estate.commission.payout.wizard', ondelete='cascade')
    user_id = fields.Many2one('res.users', string='Asesor', readonly=True)
    roles = fields.Char(string='Rol(es)', readonly=True)
    amount_base = fields.Monetary(
        string='Monto base', currency_field='company_currency', readonly=True)
    invoice = fields.Selection(
        INVOICE_MODES, string='¿Factura?', default='without', required=True)
    amount_vat = fields.Monetary(
        string='IVA', currency_field='company_currency', compute='_compute_amounts')
    amount_total = fields.Monetary(
        string='Total a pagar', currency_field='company_currency', compute='_compute_amounts')
    company_currency = fields.Many2one(related='wizard_id.company_currency')
    payment_method = fields.Selection(
        selection=lambda self: self.env['estate.commission']._fields['payment_method'].selection,
        string='¿Cómo se le paga?', default='transfer')
    payment_date = fields.Date(string='Fecha de pago', default=fields.Date.context_today)
    payment_reference = fields.Char(string='Comprobante / Referencia')
    payment_bank_from = fields.Char(string='Banco de origen')
    payment_bank_to = fields.Char(string='Banco de destino')

    @api.depends('invoice', 'amount_base')
    def _compute_amounts(self):
        for line in self:
            line.amount_vat = vat_amount(line.amount_base, line.invoice)
            line.amount_total = round(line.amount_base + line.amount_vat, 2)

    @api.onchange('invoice')
    def _onchange_invoice(self):
        self._compute_amounts()
