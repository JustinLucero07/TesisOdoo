# -*- coding: utf-8 -*-
from odoo import models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def action_open_client_import(self):
        action = self.env['ir.actions.actions']._for_xml_id(
            'estate_crm.action_estate_client_import')
        action['target'] = 'current'
        return action
