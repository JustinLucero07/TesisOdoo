# -*- coding: utf-8 -*-
"""Pago de una comisión cuando un solo asesor hizo todos los pasos.

Aunque una misma persona capte, reciba, visite y cierre, no cobra el 100% de
los honorarios: cobra la suma de los cuatro roles y el resto se queda en la
oficina. Este asistente muestra ese desglose antes de pagar y deja ajustar la
captación, que es la única que cambia según haya exclusividad o no.
"""
from odoo import api, fields, models
from odoo.exceptions import UserError


class EstateCommissionPayWizard(models.TransientModel):
    _name = 'estate.commission.pay.wizard'
    _description = 'Pagar comisión a un solo asesor'

    commission_id = fields.Many2one('estate.commission', required=True, readonly=True)
    user_id = fields.Many2one(
        'res.users', string='Asesor', related='commission_id.user_id', readonly=True)
    property_id = fields.Many2one(
        'estate.property', related='commission_id.property_id', readonly=True)
    company_currency = fields.Many2one(
        'res.currency', related='commission_id.company_currency', readonly=True)
    # No es related porque estate.commission.amount es Float, no Monetary.
    deal_total = fields.Monetary(
        string='Honorarios del negocio', compute='_compute_deal_total',
        currency_field='company_currency')
    is_exclusive = fields.Boolean(
        string='Captación en exclusividad', related='commission_id.property_id.is_exclusive',
        readonly=True)

    pct_capture = fields.Float(string='Captación (%)')
    pct_reception = fields.Float(string='Recepción (%)')
    pct_visit = fields.Float(string='Visita (%)')
    pct_closing = fields.Float(string='Cierre (%)')

    pct_total = fields.Float(
        string='Total para el asesor (%)', compute='_compute_totals')
    amount_advisor = fields.Monetary(
        string='A pagar al asesor', compute='_compute_totals',
        currency_field='company_currency')
    amount_office = fields.Monetary(
        string='Queda en la oficina', compute='_compute_totals',
        currency_field='company_currency')

    payment_method = fields.Selection(
        related='commission_id.payment_method', readonly=False, required=True,
        string='Forma de Pago')
    payment_date = fields.Date(string='Fecha de Pago', default=fields.Date.context_today)
    payment_reference = fields.Char(string='Comprobante / Referencia')

    @api.depends('commission_id.amount')
    def _compute_deal_total(self):
        for w in self:
            w.deal_total = w.commission_id.amount or 0.0

    @api.depends('pct_capture', 'pct_reception', 'pct_visit', 'pct_closing', 'deal_total')
    def _compute_totals(self):
        for w in self:
            total = (w.pct_capture + w.pct_reception + w.pct_visit + w.pct_closing)
            w.pct_total = total
            w.amount_advisor = (w.deal_total or 0.0) * (total / 100.0)
            w.amount_office = (w.deal_total or 0.0) - w.amount_advisor

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        comision = self.env['estate.commission'].browse(
            self.env.context.get('active_id'))
        if not comision.exists():
            return vals
        company = self.env.company
        vals.update({
            'commission_id': comision.id,
            'pct_capture': (company.estate_pct_capture_exclusive
                            if comision.property_id.is_exclusive
                            else company.estate_pct_capture),
            'pct_reception': company.estate_pct_reception,
            'pct_visit': company.estate_pct_visit,
            'pct_closing': company.estate_pct_closing,
            'payment_reference': comision.payment_reference,
        })
        return vals

    def action_confirm(self):
        self.ensure_one()
        comision = self.commission_id
        if self.pct_total <= 0:
            raise UserError('El porcentaje total del asesor debe ser mayor que cero.')
        if self.pct_total > 100:
            raise UserError('El porcentaje total no puede pasar del 100%.')
        if comision.state == 'paid':
            raise UserError('Esta comisión ya está pagada.')

        # Se deja constancia del desglose con una línea por rol, todas para el
        # mismo asesor, y una sola comisión pagable para no partir la factura.
        comision.split_line_ids.unlink()
        comision.split_line_ids = [(0, 0, {
            'sequence': seq, 'role': rol, 'percentage': pct,
            'user_id': comision.user_id.id,
        }) for seq, rol, pct in (
            (10, 'capture', self.pct_capture),
            (20, 'reception', self.pct_reception),
            (30, 'visit', self.pct_visit),
            (40, 'closing', self.pct_closing),
        ) if pct > 0]

        hija = self.env['estate.commission'].create({
            'property_id': comision.property_id.id,
            'lead_id': comision.lead_id.id,
            'user_id': comision.user_id.id,
            'sale_amount': comision.sale_amount,
            'commission_pct': comision.commission_pct * (self.pct_total / 100.0),
            'amount': self.amount_advisor,
            'role': 'all',
            'role_pct': self.pct_total,
            'type': comision.type,
            'date': comision.date,
            'state': 'approved',
            'parent_commission_id': comision.id,
            'payment_method': self.payment_method,
            'payment_date': self.payment_date,
            'payment_reference': self.payment_reference,
        })
        comision.state = 'split'
        comision.message_post(body=(
            '<b>Comisión pagada a un solo asesor.</b> %s hizo los cuatro pasos: '
            'captación %.0f%%, recepción %.0f%%, visita %.0f%%, cierre %.0f%% = '
            '%.0f%% ($%s). Oficina: $%s.'
            % (comision.user_id.name, self.pct_capture, self.pct_reception,
               self.pct_visit, self.pct_closing, self.pct_total,
               '{:,.2f}'.format(self.amount_advisor),
               '{:,.2f}'.format(self.amount_office))))
        hija.action_register_payment()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'estate.commission',
            'res_id': hija.id,
            'view_mode': 'form',
        }
