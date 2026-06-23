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
            'view_mode': 'list,kanban,form',
            'res_model': 'estate.document',
            'domain': [('property_id', '=', self.id)],
            'context': {'default_property_id': self.id},
        }

    def action_new_document(self):
        """Acceso directo: abre en una ventana el formulario de un documento
        nuevo, ya vinculado a esta propiedad (y a su propietario)."""
        self.ensure_one()
        ctx = {'default_property_id': self.id}
        if self.owner_id:
            ctx['default_partner_id'] = self.owner_id.id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Nuevo Documento',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'res_model': 'estate.document',
            'target': 'new',
            'context': ctx,
        }
