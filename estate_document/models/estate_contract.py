from odoo import models, fields, api


class EstateContract(models.Model):
    _inherit = 'estate.contract'

    document_ids = fields.One2many(
        'estate.document', 'contract_id', string='Documentos del Contrato')
    document_count = fields.Integer(compute='_compute_document_count')

    def _compute_document_count(self):
        for rec in self:
            rec.document_count = len(rec.document_ids)

    def action_view_documents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Documentos — {self.name}',
            'res_model': 'estate.document',
            'view_mode': 'kanban,list,form',
            'domain': [('contract_id', '=', self.id)],
            'context': {
                'default_contract_id': self.id,
                'default_property_id': self.property_id.id,
                'default_partner_id': self.partner_id.id,
            },
        }

    def action_activate(self):
        """Override: tras activar el contrato, crear placeholders de documentos
        requeridos en estado 'pending' para que el asesor los suba."""
        res = super().action_activate() if hasattr(super(), 'action_activate') else None
        # Solo crear si el contrato pasa de borrador a activo y no tiene docs aún
        DocType = self.env['estate.document.type'].sudo()
        for contract in self:
            if contract.document_ids:
                continue
            # Buscar tipos requeridos por código
            required_codes = ['contract_signed', 'client_id_card']
            for code in required_codes:
                doc_type = DocType.search([('code', '=', code)], limit=1)
                if not doc_type:
                    continue
                self.env['estate.document'].sudo().create({
                    'name': f'{doc_type.name} - {contract.name}',
                    'type_id': doc_type.id,
                    'contract_id': contract.id,
                    'property_id': contract.property_id.id,
                    'partner_id': contract.partner_id.id,
                    'state': 'pending',
                    'file': False,
                    'notes': 'Documento creado automáticamente al activar el contrato. '
                             'Suba el archivo correspondiente.',
                })
            contract.message_post(
                body='📎 Se crearon documentos pendientes para este contrato. '
                     'Revisa la pestaña Documentos.')
        return res
