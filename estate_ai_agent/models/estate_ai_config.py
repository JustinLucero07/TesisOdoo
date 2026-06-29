from odoo import models, fields, api


class EstateAIConfig(models.TransientModel):
    _inherit = 'res.config.settings'

    def action_reindex_ai_knowledge(self):
        """Reconstruye la base de conocimiento (RAG) desde los manuales y READMEs."""
        self.ensure_one()
        return self.env['estate.ai.knowledge'].action_reindex_knowledge()

    ai_provider = fields.Selection([
        ('chatgpt', 'ChatGPT (OpenAI)'),
        ('gemini', 'Google Gemini'),
    ], string='Proveedor de IA',
        config_parameter='estate_ai.provider', default='chatgpt')

    # ── Credenciales por proveedor ───────────────────────────────────────────
    # (Los antiguos campos únicos 'ai_api_key' / 'ai_model' se retiraron de la
    #  interfaz; el controlador aún lee esos parámetros heredados como respaldo
    #  del proveedor activo en instalaciones previas.)
    # Mantener una clave/modelo por proveedor permite alternar entre ChatGPT y
    # Gemini sin volver a escribir la configuración, y habilita el respaldo
    # automático: si el proveedor activo falla, el agente reintenta con el otro.
    ai_openai_api_key = fields.Char(
        string='API Key OpenAI (ChatGPT)',
        config_parameter='estate_ai.openai_api_key')
    ai_openai_model = fields.Char(
        string='Modelo OpenAI',
        config_parameter='estate_ai.openai_model',
        default='gpt-4o-mini')
    ai_gemini_api_key = fields.Char(
        string='API Key Google Gemini',
        config_parameter='estate_ai.gemini_api_key')
    ai_gemini_model = fields.Char(
        string='Modelo Gemini',
        config_parameter='estate_ai.gemini_model',
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

    # B4: instrucciones de estilo editables para las descripciones de propiedad.
    # Se inyectan en el prompt sin tocar código.
    # NOTA: res.config.settings NO admite fields.Text → usamos Char (multi-línea en la vista).
    ai_desc_instructions = fields.Char(
        string='Estilo de Descripciones de Propiedad',
        config_parameter='estate_ai.desc_instructions',
        default="Tono profesional pero cercano y emocional. Resalta plusvalía y "
                "potencial de inversión. Evita exageraciones poco creíbles.")

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
