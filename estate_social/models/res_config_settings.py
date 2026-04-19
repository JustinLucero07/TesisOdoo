from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    whatsapp_business_number = fields.Char(
        string='Número WhatsApp Business',
        config_parameter='estate_social.whatsapp_business_number',
        help='Número para que clientes contacten directamente (ej: 593981234567)')

    facebook_page_id = fields.Char(
        string='Facebook Page ID',
        config_parameter='estate_social.facebook_page_id',
        help='ID de tu página de Facebook. Lo encuentras en Configuración de la página → Información de la página.')

    facebook_page_token = fields.Char(
        string='Page Access Token',
        config_parameter='estate_social.facebook_page_token',
        help='Token de acceso de la página (no el de usuario). Genera uno en developers.facebook.com → Tu App → Herramientas → Explorador de la API Graph → selecciona tu página.')

    instagram_account_id = fields.Char(
        string='Instagram Business Account ID',
        config_parameter='estate_social.instagram_account_id',
        help='ID de tu cuenta de Instagram Business vinculada a tu página de Facebook. Ve a Tu App → Instagram → Configuración de la API.')

    odoo_base_url = fields.Char(
        string='URL Pública del Servidor',
        config_parameter='estate_social.odoo_base_url',
        help='URL pública de este servidor Odoo (ej: https://miinmobiliaria.com). Necesaria para que Instagram pueda acceder a las imágenes si no usas WordPress.')
