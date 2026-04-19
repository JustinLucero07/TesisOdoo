from odoo import models
# is_property_owner vive en estate_management/models/res_partner.py
# estate_crm depende de estate_management, por lo que el campo ya está disponible.
# Este archivo se mantiene para extensiones futuras específicas del CRM.


class ResPartnerCRM(models.Model):
    _inherit = 'res.partner'
