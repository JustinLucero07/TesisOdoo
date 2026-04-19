from odoo import models, fields, api


class EstateAIConfig(models.TransientModel):
    _inherit = 'res.config.settings'

    ai_provider = fields.Selection([
        ('chatgpt', 'ChatGPT (OpenAI)'),
        ('gemini', 'Google Gemini'),
    ], string='Proveedor de IA',
        config_parameter='estate_ai.provider', default='chatgpt')

    ai_api_key = fields.Char(
        string='API Key',
        config_parameter='estate_ai.api_key')

    ai_model = fields.Char(
        string='Modelo',
        config_parameter='estate_ai.model',
        default='gemini-flash-latest')

    ai_temperature = fields.Float(
        string='Temperatura (Creatividad)',
        config_parameter='estate_ai.temperature',
        default=0.7)

    ai_max_tokens = fields.Integer(
        string='Máximo de Tokens',
        config_parameter='estate_ai.max_tokens',
        default=1000)

    ai_active = fields.Boolean(
        string='Agente IA Activo',
        config_parameter='estate_ai.active',
        default=True)

    ai_system_prompt = fields.Char(
        string='Prompt del Sistema',
        config_parameter='estate_ai.system_prompt',
        default="""Eres un asistente inteligente para un sistema de gestión inmobiliaria. 
Puedes ayudar con:
- Consultar propiedades disponibles, vendidas o alquiladas
- Información sobre clientes
- Estado de contratos y pagos
- Generar reportes
- Responder preguntas sobre el sistema

Responde siempre en español y de forma concisa y profesional.
Cuando te pidan datos, usa la información proporcionada del sistema.
Si no tienes información suficiente, indica qué datos necesitas.""")
