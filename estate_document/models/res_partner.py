from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    document_ids = fields.One2many(
        'estate.document', 'partner_id', string='Documentos Inmobiliarios')
    document_count = fields.Integer(compute='_compute_document_count')

    def _compute_document_count(self):
        for rec in self:
            rec.document_count = len(rec.document_ids)

    def action_view_documents(self):
        """Vista clásica filtrada por partner_id."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documentos',
            'view_mode': 'kanban,list,form',
            'res_model': 'estate.document',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }

    def action_view_full_folder(self):
        """Carpeta completa: TODOS los documentos relacionados al cliente
        (suyos, de sus propiedades como dueño/comprador, de sus leads, de sus contratos).
        """
        self.ensure_one()
        # Buscar IDs relacionados
        domain = ['|', '|', '|',
                  ('partner_id', '=', self.id),
                  ('property_id.owner_id', '=', self.id),
                  ('property_id.buyer_id', '=', self.id),
                  ('lead_id.partner_id', '=', self.id)]
        # También documentos vinculados a contratos del cliente
        contracts = self.env['estate.contract'].sudo().search([('partner_id', '=', self.id)])
        if contracts:
            domain = ['|'] + domain + [('contract_id', 'in', contracts.ids)]
        return {
            'type': 'ir.actions.act_window',
            'name': f'📂 Carpeta de {self.name}',
            'res_model': 'estate.document',
            'view_mode': 'kanban,list,form',
            'domain': domain,
            'context': {
                'default_partner_id': self.id,
                'search_default_group_category': 1,
            },
        }
