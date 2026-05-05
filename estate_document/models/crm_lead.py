from odoo import models, fields


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    document_ids = fields.One2many(
        'estate.document', 'lead_id', string='Documentos Inmobiliarios')
