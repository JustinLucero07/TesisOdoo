# -*- coding: utf-8 -*-
from odoo import api, models, fields


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

    # --- Reparto de la comisión entre los roles del negocio ---
    # Son porcentajes SOBRE LOS HONORARIOS DE LA AGENCIA, no sobre el precio de
    # venta. Lo que no se reparte entre los roles se queda en la oficina.
    estate_pct_capture = fields.Float(
        string='Captación sin exclusividad (%)', default=8.0,
        help='Porcentaje de los honorarios para quien captó la propiedad cuando '
             'no hay exclusividad o no hay contrato firmado.')
    estate_pct_capture_exclusive = fields.Float(
        string='Captación con exclusividad (%)', default=10.0,
        help='Porcentaje para el captador cuando la propiedad está en exclusividad.')
    estate_pct_reception = fields.Float(
        string='Recepción (%)', default=10.0,
        help='Porcentaje para quien recibió el contacto del cliente.')
    estate_pct_visit = fields.Float(
        string='Visita (%)', default=15.0,
        help='Porcentaje para quien realizó la visita al inmueble.')
    estate_pct_closing = fields.Float(
        string='Cierre (%)', default=15.0,
        help='Porcentaje para quien cerró el negocio.')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    estate_docx_template = fields.Binary(
        related='company_id.estate_docx_template', readonly=False,
        string='Plantilla de Contrato General (Word)')
    estate_docx_template_name = fields.Char(
        related='company_id.estate_docx_template_name', readonly=False,
        string='Nombre de la Plantilla Word')

    estate_pct_capture = fields.Float(
        related='company_id.estate_pct_capture', readonly=False,
        string='Captación sin exclusividad (%)')
    estate_pct_capture_exclusive = fields.Float(
        related='company_id.estate_pct_capture_exclusive', readonly=False,
        string='Captación con exclusividad (%)')
    estate_pct_reception = fields.Float(
        related='company_id.estate_pct_reception', readonly=False,
        string='Recepción (%)')
    estate_pct_visit = fields.Float(
        related='company_id.estate_pct_visit', readonly=False,
        string='Visita (%)')
    estate_pct_closing = fields.Float(
        related='company_id.estate_pct_closing', readonly=False,
        string='Cierre (%)')
    estate_pct_advisors_total = fields.Float(
        string='Total a asesores (%)', compute='_compute_estate_pct_advisors_total')
    estate_pct_office = fields.Float(
        string='Queda en la oficina (%)', compute='_compute_estate_pct_advisors_total')

    @api.depends('estate_pct_capture_exclusive', 'estate_pct_reception',
                 'estate_pct_visit', 'estate_pct_closing')
    def _compute_estate_pct_advisors_total(self):
        for rec in self:
            total = (rec.estate_pct_capture_exclusive + rec.estate_pct_reception
                     + rec.estate_pct_visit + rec.estate_pct_closing)
            rec.estate_pct_advisors_total = total
            rec.estate_pct_office = 100.0 - total

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
