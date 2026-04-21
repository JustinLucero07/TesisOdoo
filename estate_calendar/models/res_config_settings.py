from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    whatsapp_active = fields.Boolean(
        string='Activar WhatsApp',
        config_parameter='estate_calendar.whatsapp_active')
    whatsapp_phone_number_id = fields.Char(
        string='Phone Number ID',
        config_parameter='estate_calendar.whatsapp_phone_number_id',
        help='El "Phone Number ID" de tu app en developers.facebook.com → WhatsApp → Configuración de la API')
    whatsapp_access_token = fields.Char(
        string='Access Token (permanente)',
        config_parameter='estate_calendar.whatsapp_access_token',
        help='Token permanente generado desde Meta Business → Usuarios del sistema')
    whatsapp_template_name = fields.Char(
        string='Nombre de Plantilla',
        config_parameter='estate_calendar.whatsapp_template_name',
        default='recordatorio_cita',
        help='Nombre exacto de la plantilla aprobada en Meta (ej: recordatorio_cita)')
    whatsapp_contract_template = fields.Char(
        string='Plantilla Contratos',
        config_parameter='estate_management.whatsapp_contract_template',
        default='recordatorio_contrato',
        help='Nombre exacto de la plantilla en Meta para recordatorios de vencimiento de contratos. '
             'Parámetros: {{1}} destinatario, {{2}} propiedad, {{3}} fecha vencimiento, {{4}} días restantes.')

    whatsapp_business_number = fields.Char(
        string='Número WhatsApp Business',
        config_parameter='estate_social.whatsapp_business_number',
        help='Número de WhatsApp Business para compartir propiedades (ej: 593981234567)')

    meta_verify_token = fields.Char(
        string='Token de Verificación Meta (Webhook)',
        config_parameter='estate_crm.meta_verify_token',
        help=(
            'Token secreto que configuras en developers.facebook.com al registrar el webhook. '
            'Debe coincidir exactamente con el que pones en Meta → Webhooks → Token de verificación.'
        ))
