# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api, fields


def migrate(cr, version):
    """Crea el recordatorio de los documentos y contratos que vencen de hoy en
    adelante (los ya vencidos no, para no disparar avisos atrasados)."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    today = fields.Date.today()
    env['estate.document'].search([('expiration_date', '>=', today)])._sync_expiry_reminder()
    env['estate.property'].search([('contract_end_date', '>=', today)])._sync_contract_reminder()
