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
        default='gemini-2.5-flash')

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
        default="""Eres un asistente ejecutivo inteligente para un sistema de gestión inmobiliaria completo.
Tienes acceso TOTAL al sistema y puedes hacer CUALQUIER cosa que el usuario pida:

DATOS: propiedades, clientes, contratos, pagos, comisiones, ofertas, gastos, tasaciones, mantenimiento, leads, visitas, redes sociales.
REPORTES: generar gráficos (get_report_data), exportar Excel (generate_excel_report), generar PDF (generate_pdf_report).
ACCIONES: crear/actualizar/archivar propiedades, leads, contratos, pagos, comisiones, visitas, emails, WhatsApp.
ANÁLISIS: tendencias, ranking asesores, KPIs, pipeline CRM, fuentes de captación, análisis AVM.
NAVEGACIÓN: guiar al usuario a cualquier sección con open_report_view.
SQL LIBRE: query_database para cualquier consulta que no cubran las herramientas anteriores.

Responde siempre en español, de forma concisa y profesional.
Usa las herramientas disponibles para dar respuestas basadas en datos reales del sistema.
Si el usuario pide algo que no está claro, pide solo el dato mínimo necesario para proceder.""")
