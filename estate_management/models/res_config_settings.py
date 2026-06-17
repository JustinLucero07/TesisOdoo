# -*- coding: utf-8 -*-
from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    # Plantilla Word (.docx con marcadores) para generar contratos
    estate_docx_template = fields.Binary(string='Plantilla de Contrato (Word)')
    estate_docx_template_name = fields.Char(string='Nombre de la Plantilla Word')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    estate_docx_template = fields.Binary(
        related='company_id.estate_docx_template', readonly=False,
        string='Plantilla de Contrato (Word)')
    estate_docx_template_name = fields.Char(
        related='company_id.estate_docx_template_name', readonly=False,
        string='Nombre de la Plantilla Word')
