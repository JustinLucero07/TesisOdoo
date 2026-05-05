from odoo import models, fields


class EstateProperty(models.Model):
    _inherit = 'estate.property'

    document_ids = fields.One2many(
        'estate.document', 'property_id', string='Documentos')
    document_count = fields.Integer(compute='_compute_document_count')

    def _compute_document_count(self):
        for rec in self:
            rec.document_count = len(rec.document_ids)

    def action_view_documents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documentos',
            'view_mode': 'kanban,list,form',
            'res_model': 'estate.document',
            'domain': [('property_id', '=', self.id)],
            'context': {'default_property_id': self.id},
        }
