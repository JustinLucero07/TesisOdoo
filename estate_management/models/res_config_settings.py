# -*- coding: utf-8 -*-
from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    # Plantillas Word (.docx con marcadores) para generar contratos
    estate_docx_template = fields.Binary(string='Plantilla de Contrato General (Word)')
    estate_docx_template_name = fields.Char(string='Nombre de la Plantilla Word')

    # Las 4 plantillas específicas de Corretaje
    estate_tpl_exclusive_owner = fields.Binary(string='Plantilla Con Exclusividad - Propietario (.docx)')
    estate_tpl_exclusive_owner_name = fields.Char(string='Nombre Plantilla Con Exclusividad Propietario')

    estate_tpl_exclusive_proxy = fields.Binary(string='Plantilla Con Exclusividad - Apoderado (.docx)')
    estate_tpl_exclusive_proxy_name = fields.Char(string='Nombre Plantilla Con Exclusividad Apoderado')

    estate_tpl_non_exclusive_owner = fields.Binary(string='Plantilla Sin Exclusividad - Propietario (.docx)')
    estate_tpl_non_exclusive_owner_name = fields.Char(string='Nombre Plantilla Sin Exclusividad Propietario')

    estate_tpl_non_exclusive_proxy = fields.Binary(string='Plantilla Sin Exclusividad - Apoderado (.docx)')
    estate_tpl_non_exclusive_proxy_name = fields.Char(string='Nombre Plantilla Sin Exclusividad Apoderado')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    estate_docx_template = fields.Binary(
        related='company_id.estate_docx_template', readonly=False,
        string='Plantilla de Contrato General (Word)')
    estate_docx_template_name = fields.Char(
        related='company_id.estate_docx_template_name', readonly=False,
        string='Nombre de la Plantilla Word')

    estate_tpl_exclusive_owner = fields.Binary(
        related='company_id.estate_tpl_exclusive_owner', readonly=False,
        string='Plantilla Con Exclusividad - Propietario (.docx)')
    estate_tpl_exclusive_owner_name = fields.Char(
        related='company_id.estate_tpl_exclusive_owner_name', readonly=False,
        string='Nombre Plantilla Con Exclusividad Propietario')

    estate_tpl_exclusive_proxy = fields.Binary(
        related='company_id.estate_tpl_exclusive_proxy', readonly=False,
        string='Plantilla Con Exclusividad - Apoderado (.docx)')
    estate_tpl_exclusive_proxy_name = fields.Char(
        related='company_id.estate_tpl_exclusive_proxy_name', readonly=False,
        string='Nombre Plantilla Con Exclusividad Apoderado')

    estate_tpl_non_exclusive_owner = fields.Binary(
        related='company_id.estate_tpl_non_exclusive_owner', readonly=False,
        string='Plantilla Sin Exclusividad - Propietario (.docx)')
    estate_tpl_non_exclusive_owner_name = fields.Char(
        related='company_id.estate_tpl_non_exclusive_owner_name', readonly=False,
        string='Nombre Plantilla Sin Exclusividad Propietario')

    estate_tpl_non_exclusive_proxy = fields.Binary(
        related='company_id.estate_tpl_non_exclusive_proxy', readonly=False,
        string='Plantilla Sin Exclusividad - Apoderado (.docx)')
    estate_tpl_non_exclusive_proxy_name = fields.Char(
        related='company_id.estate_tpl_non_exclusive_proxy_name', readonly=False,
        string='Nombre Plantilla Sin Exclusividad Apoderado')
