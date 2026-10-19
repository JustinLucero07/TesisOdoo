# -*- coding: utf-8 -*-
from odoo import api, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.depends('property_id.deal_lead_origin', 'lead_id.lead_source_id.name',
                 'estate_buyer_id')
    def _compute_estate_source(self):
        """La difusión sale de la fuente del lead de origen. Si la orden no
        tiene lead, se busca el lead del comprador para esa propiedad."""
        Lead = self.env['crm.lead'].with_context(active_test=False).sudo()
        for order in self:
            lead = order.lead_id
            if not lead.lead_source_id and order.property_id and order.estate_buyer_id:
                lead = Lead.search([
                    ('target_property_id', '=', order.property_id.id),
                    ('partner_id', '=', order.estate_buyer_id.id),
                    ('lead_source_id', '!=', False),
                ], order='id desc', limit=1)
            order.estate_source = (lead.lead_source_id.name
                                   or order.property_id.deal_lead_origin or False)
