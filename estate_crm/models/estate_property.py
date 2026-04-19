# -*- coding: utf-8 -*-
# R5 fix: El matchmaking proactivo al crear propiedades vive AQUÍ (estate_crm),
# NO en estate_management. No duplicar el override de create() en estate_management.
from odoo import models, api, fields


class EstateProperty(models.Model):
    _inherit = 'estate.property'

    @api.model_create_multi
    def create(self, vals_list):
        properties = super(EstateProperty, self).create(vals_list)
        
        # Matchmaking Proactivo en Tiempo Real (Movido desde estate_management)
        # Esto ahora es seguro porque estate_crm depende de crm
        for prop in properties:
            if prop.state == 'available':
                domain = [
                    ('type', '=', 'lead'), 
                    ('stage_id.is_won', '=', False), 
                    ('probability', '>', 0),
                    ('client_budget', '>=', (prop.price or 0.0) * 0.95),
                ]
                if prop.city:
                    domain.append(('city', 'ilike', prop.city))
                    
                leads = self.env['crm.lead'].sudo().search(domain)
                for lead in leads:
                    self.env['mail.activity'].sudo().create({
                        'res_id': lead.id,
                        'res_model_id': self.env['ir.model'].sudo()._get_id('crm.lead'),
                        'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                        'summary': f"¡Match Instantáneo! Propiedad Nueva: {prop.name}",
                        'note': f"La propiedad {prop.title} en {prop.city} (${prop.price:,.2f}) acaba de ingresar y encaja con el presupuesto del Lead (${lead.client_budget:,.2f}).",
                        'user_id': lead.user_id.id if lead.user_id else self.env.user.id,
                    })

        return properties
