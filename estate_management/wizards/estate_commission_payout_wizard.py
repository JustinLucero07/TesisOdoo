# -*- coding: utf-8 -*-
from odoo import api, fields, models


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
        string='¿Cómo se les paga?', required=True)
    payment_date = fields.Date(string='Fecha de pago', required=True,
                               default=fields.Date.context_today)
    payment_reference = fields.Char(string='Comprobante / Referencia',
                                    help='Nº de transferencia, recibo o cheque.')
    company_currency = fields.Many2one(related='commission_id.company_currency')
    amount_to_pay = fields.Monetary(
        string='Total a pagar', currency_field='company_currency',
        compute='_compute_summary')
    advisors = fields.Char(string='Asesores', compute='_compute_summary')

    @api.depends('commission_id', 'mode')
    def _compute_summary(self):
        for wiz in self:
            com = wiz.commission_id
            if wiz.mode == 'split':
                lines = com.split_line_ids.filtered(lambda l: l.user_id and l.amount > 0)
                amount, users = sum(lines.mapped('amount')), lines.user_id
            elif wiz.mode == 'pending':
                pend = com.child_commission_ids.filtered(lambda c: c.state in ('draft', 'approved'))
                amount, users = sum(pend.mapped('amount')), pend.user_id
            else:
                amount, users = com.amount, com.user_id
            wiz.amount_to_pay = amount
            wiz.advisors = ', '.join(users.mapped('name'))

    def action_confirm(self):
        self.ensure_one()
        com = self.commission_id
        com.write({
            'payment_method': self.payment_method,
            'payment_date': self.payment_date,
            'payment_reference': self.payment_reference,
        })
        if self.mode == 'split':
            return com.action_split_into_commissions()
        if self.mode == 'pending':
            return com.action_pay_all_children()
        com.action_register_payment()
        return {'type': 'ir.actions.act_window_close'}
