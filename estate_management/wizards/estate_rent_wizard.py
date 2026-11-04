# -*- coding: utf-8 -*-
"""Arrendar una propiedad (o modificar el arriendo ya registrado).

Más sencillo que el negocio cerrado de una venta: quién arrienda, desde cuándo,
por cuántos meses, cuánto paga al mes y la garantía. La comisión se calcula
sobre el primer mes y queda a nombre del asesor a cargo.
"""
from dateutil.relativedelta import relativedelta
from markupsafe import Markup

from odoo import api, fields, models
from odoo.exceptions import UserError


class EstateRentWizard(models.TransientModel):
    _name = 'estate.rent.wizard'
    _description = 'Arrendar propiedad'

    property_id = fields.Many2one('estate.property', string='Propiedad', required=True, readonly=True)
    is_edit_mode = fields.Boolean(string='Modificar arriendo')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    owner_id = fields.Many2one(related='property_id.owner_id', string='Propietario')
    tenant_id = fields.Many2one('res.partner', string='Arrendatario (inquilino)')
    date_rented = fields.Date(string='Fecha de inicio', required=True, default=fields.Date.context_today)
    rent_months = fields.Integer(string='Duración (meses)', default=12)
    date_end = fields.Date(string='Termina el', compute='_compute_date_end')
    rental_price = fields.Monetary(string='Valor del arriendo mensual', required=True)
    rent_deposit = fields.Monetary(string='Garantía / depósito')
    commission_pct = fields.Float(string='Comisión (%)')
    commission_amount = fields.Monetary(
        string='Comisión (primer mes)', compute='_compute_commission_amount',
        store=True, readonly=False,
        help='Puedes escribir el monto: el porcentaje se calcula solo, y al revés.')
    user_id = fields.Many2one('res.users', string='Asesor a cargo', required=True,
                              domain=[('share', '=', False)])
    rented_by = fields.Selection(
        selection=lambda self: self.env['estate.property']._fields['rented_by'].selection,
        string='Arrendado por', required=True, default='agency')
    deal_partner_id = fields.Many2one('res.partner', string='Colega / Referido')
    deal_partner_amount = fields.Monetary(
        string='Monto al referido', help='Se resta del arriendo mensual antes de calcular la comisión.')
    our_share_pct = fields.Float(string='Nuestra parte de la comisión (%)', default=50.0)
    is_shared = fields.Boolean(compute='_compute_our_commission')
    our_commission_amount = fields.Monetary(
        string='Nuestra parte', compute='_compute_our_commission')
    rent_observations = fields.Text(string='Observaciones')

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        prop = self.env['estate.property'].browse(
            vals.get('property_id') or self.env.context.get('default_property_id'))
        if prop.exists():
            vals.update({
                'tenant_id': prop.tenant_id.id or False,
                'date_rented': prop.date_rented or fields.Date.context_today(self),
                'rent_months': prop.rent_months or 12,
                'rental_price': prop.rental_price or prop.price,
                'rent_deposit': prop.rent_deposit,
                'commission_pct': prop.commission_percentage,
                'user_id': prop._estate_rent_advisor().id,
                'rent_observations': prop.rent_observations,
                'rented_by': prop.rented_by or 'agency',
                'deal_partner_id': prop.deal_partner_id.id if prop.rented_by in ('colleague', 'referral') else False,
                'deal_partner_amount': prop.deal_partner_amount if prop.rented_by == 'referral' else 0.0,
                'our_share_pct': prop.allied_split_pct or 50.0,
            })
        return vals

    @api.depends('date_rented', 'rent_months')
    def _compute_date_end(self):
        for wiz in self:
            wiz.date_end = (wiz.date_rented + relativedelta(months=wiz.rent_months)
                            if wiz.date_rented and wiz.rent_months else False)

    def _base(self):
        self.ensure_one()
        base = self.rental_price or 0.0
        if self.rented_by == 'referral':
            base = max(base - (self.deal_partner_amount or 0.0), 0.0)
        return base

    def _our_ratio(self):
        self.ensure_one()
        if self.rented_by == 'colleague':
            return (self.our_share_pct or 50.0) / 100.0
        if self.property_id.is_allied_property:
            return (self.property_id.allied_split_pct or 50.0) / 100.0
        return 1.0

    @api.depends('rental_price', 'commission_pct', 'rented_by', 'deal_partner_amount')
    def _compute_commission_amount(self):
        for wiz in self:
            if wiz.rented_by in ('owner', 'external'):
                wiz.commission_amount = 0.0
            else:
                wiz.commission_amount = wiz._base() * (wiz.commission_pct or 0.0) / 100.0

    @api.depends('commission_amount', 'rented_by', 'our_share_pct',
                 'property_id.is_allied_property', 'property_id.allied_split_pct')
    def _compute_our_commission(self):
        for wiz in self:
            wiz.is_shared = wiz.rented_by == 'colleague' or bool(wiz.property_id.is_allied_property)
            wiz.our_commission_amount = round(wiz.commission_amount * wiz._our_ratio(), 2)

    @api.onchange('commission_amount')
    def _onchange_commission_amount(self):
        for wiz in self:
            base = wiz._base()
            if base and wiz.rented_by not in ('owner', 'external'):
                pct = wiz.commission_amount / base * 100.0
                if abs(pct - (wiz.commission_pct or 0.0)) > 0.00005:
                    wiz.commission_pct = pct

    def action_confirm(self):
        self.ensure_one()
        prop = self.property_id
        if self.rental_price <= 0:
            raise UserError('El valor del arriendo mensual debe ser mayor que cero.')
        if self.commission_pct < 0:
            raise UserError('La comisión no puede ser negativa.')
        if self.rented_by in ('colleague', 'referral') and not self.deal_partner_id:
            raise UserError('Indica quién es el colega o el referido.')
        if self.rented_by == 'referral' and self.deal_partner_amount <= 0:
            raise UserError('Indica el monto que se le paga al referido.')
        vals = {
            'tenant_id': self.tenant_id.id or False,
            'date_rented': self.date_rented,
            'rent_months': self.rent_months,
            'contract_end_date': self.date_end,
            'rental_price': self.rental_price,
            'rent_deposit': self.rent_deposit,
            'commission_percentage': self.commission_pct,
            'user_id': self.user_id.id,
            'rent_observations': self.rent_observations,
            'rented_by': self.rented_by,
            'deal_partner_id': self.deal_partner_id.id if self.rented_by in ('colleague', 'referral') else False,
            'deal_partner_amount': self.deal_partner_amount if self.rented_by == 'referral' else 0.0,
        }
        if self.rented_by == 'colleague':
            vals['allied_split_pct'] = self.our_share_pct
        if self.is_edit_mode:
            if prop.state != 'rented':
                raise UserError('Solo se puede modificar el arriendo de una propiedad Arrendada.')
            prop.with_context(no_wp_sync=True).write(vals)
            self._sync_rent_commission(prop)
            prop.message_post(body=Markup('<b>Datos del arriendo actualizados.</b>'))
            return {'type': 'ir.actions.act_window_close'}

        if prop.state not in ('available', 'reserved'):
            raise UserError('Solo se puede arrendar una propiedad Disponible o Reservada.')
        prop.with_context(no_wp_sync=True).write(vals)
        prop._estate_do_rent()
        prop.message_post(body=Markup(
            '<b>Propiedad ARRENDADA</b> a <b>%s</b> desde el %s · $%s al mes%s. '
            'Arrendado por: %s. Comisión (primer mes): $%s.') % (
            self.tenant_id.name or '—', self.date_rented.strftime('%d/%m/%Y'),
            '{:,.2f}'.format(self.rental_price),
            ' · %s meses' % self.rent_months if self.rent_months else '',
            dict(prop._fields['rented_by'].selection).get(self.rented_by),
            '{:,.2f}'.format(self.commission_amount)))
        return prop.action_print_rent()

    def _sync_rent_commission(self, prop):
        """La comisión de arriendo que aún no se paga toma los valores nuevos."""
        tops = self.env['estate.commission'].search([
            ('property_id', '=', prop.id), ('type', '=', 'rent'),
            ('parent_commission_id', '=', False), ('state', '!=', 'cancelled')])
        if not tops:
            return
        if self.rented_by in ('owner', 'external'):
            pendientes = (tops | tops.child_commission_ids).filtered(lambda c: c.state in ('draft', 'approved'))
            if pendientes and not any(c.state == 'paid' for c in tops | tops.child_commission_ids):
                pendientes.action_cancel()
                prop.message_post(body=Markup(
                    'La comisión del arriendo se canceló: lo arrendó el propietario o un externo.'))
            return
        if any(c.state == 'paid' for c in tops | tops.child_commission_ids):
            prop.message_post(body=Markup(
                '<b>Aviso:</b> la comisión del arriendo ya está pagada y no se cambió. '
                'Usa "Corregir pago" si el monto cambió.'))
            return
        ratio = self._our_ratio()
        old_total = sum(tops.mapped('amount')) or 0.0
        for com in tops:
            share = (com.amount / old_total) if old_total else 1.0 / len(tops)
            vals = {'sale_amount': self._base(),
                    'commission_pct': self.commission_pct * ratio * share}
            if len(tops) == 1:
                vals['user_id'] = self.user_id.id
            com.write(vals)
        tops.filtered(lambda c: c.state == 'split')._sync_split_to_children()
