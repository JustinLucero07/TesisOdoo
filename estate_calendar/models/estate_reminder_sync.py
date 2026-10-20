# -*- coding: utf-8 -*-
"""Vencimientos de documentos y contratos → Recordatorios de clientes.

Antes cada uno tenía su propio aviso (cron + actividad). Ahora crean un
estate.reminder, así todos los vencimientos llegan igual (actividad en Odoo,
push al móvil y WhatsApp si se activa) y se ven en una sola lista.
"""
from odoo import api, fields, models


class EstateDocumentReminderSync(models.Model):
    _inherit = 'estate.document'

    def _reminder_partner(self):
        self.ensure_one()
        return self.partner_id or self.property_id.owner_id

    def _sync_expiry_reminder(self):
        Reminder = self.env['estate.reminder'].sudo()
        ICP = self.env['ir.config_parameter'].sudo()
        try:
            days = int(ICP.get_param('estate_document.expiry_warning_days', '30') or 30)
        except ValueError:
            days = 30
        for doc in self:
            reminder = Reminder.search([('document_id', '=', doc.id),
                                        ('auto_origin', '=', 'document')], limit=1)
            partner = doc._reminder_partner()
            if not doc.expiration_date or doc.state in ('archived', 'rejected') or not partner:
                if reminder and reminder.state == 'pending':
                    reminder.state = 'cancelled'
                continue
            vals = {
                'name': 'Vence: %s' % (doc.name or 'documento'),
                'reminder_type': 'document',
                'partner_id': partner.id,
                'property_id': doc.property_id.id or False,
                'document_id': doc.id,
                'date': doc.expiration_date,
                'remind_value': days,
                'remind_unit': 'days',
                'user_id': (doc.uploaded_by or doc.property_id.user_id or self.env.user).id,
                'auto_origin': 'document',
            }
            if reminder:
                if reminder.date != doc.expiration_date:
                    vals.update(state='pending', advance_notified=False, due_notified=False)
                reminder.write(vals)
            else:
                Reminder.create(vals)

    @api.model_create_multi
    def create(self, vals_list):
        docs = super().create(vals_list)
        docs.filtered('expiration_date')._sync_expiry_reminder()
        return docs

    def write(self, vals):
        res = super().write(vals)
        if {'expiration_date', 'state', 'partner_id', 'property_id', 'name'} & set(vals):
            self._sync_expiry_reminder()
        return res

    @api.model
    def _cron_notify_expiring_documents(self):
        # Los que ya tienen recordatorio avisan por ahí: no duplicar la actividad.
        self.search([('expiry_notified', '=', False),
                     ('reminder_ids.auto_origin', '=', 'document')]).write({'expiry_notified': True})
        return super()._cron_notify_expiring_documents()


class EstatePropertyContractReminderSync(models.Model):
    _inherit = 'estate.property'

    def _sync_contract_reminder(self):
        Reminder = self.env['estate.reminder'].sudo()
        for prop in self:
            reminder = Reminder.search([('property_id', '=', prop.id),
                                        ('auto_origin', '=', 'property_contract')], limit=1)
            active = prop.contract_end_date and prop.state in ('available', 'reserved') and prop.owner_id
            if not active:
                if reminder and reminder.state == 'pending':
                    reminder.state = 'cancelled'
                continue
            vals = {
                'name': 'Vence el contrato de %s' % (prop.title or prop.display_name),
                'reminder_type': 'contract',
                'partner_id': prop.owner_id.id,
                'property_id': prop.id,
                'date': prop.contract_end_date,
                'remind_value': prop.contract_reminder_days or 30,
                'remind_unit': 'days',
                'user_id': (prop.user_id or self.env.user).id,
                'auto_origin': 'property_contract',
            }
            if reminder:
                if reminder.date != prop.contract_end_date:
                    vals.update(state='pending', advance_notified=False, due_notified=False)
                reminder.write(vals)
            else:
                Reminder.create(vals)

    @api.model_create_multi
    def create(self, vals_list):
        props = super().create(vals_list)
        props.filtered('contract_end_date')._sync_contract_reminder()
        return props

    def write(self, vals):
        res = super().write(vals)
        if {'contract_end_date', 'contract_reminder_days', 'state', 'owner_id', 'user_id'} & set(vals):
            self._sync_contract_reminder()
        return res

    @api.model
    def _cron_check_contract_expiry(self):
        # Las propiedades con recordatorio de contrato avisan por ahí (actividad,
        # push y WhatsApp); el aviso viejo queda solo para las que no tienen.
        with_reminder = self.env['estate.reminder'].sudo().search(
            [('auto_origin', '=', 'property_contract'), ('state', '=', 'pending')]).property_id
        return super(EstatePropertyContractReminderSync,
                     self.with_context(estate_skip_contract_ids=with_reminder.ids))._cron_check_contract_expiry()
