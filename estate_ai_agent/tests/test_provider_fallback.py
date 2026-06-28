from odoo.tests.common import TransactionCase, tagged
from odoo.addons.estate_ai_agent.controllers.estate_ai_controller import EstateAIController


@tagged('post_install', '-at_install', 'estate_ai_fallback')
class TestAIProviderFallback(TransactionCase):
    """Cadena de proveedores y modo degradado del agente IA."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ctrl = EstateAIController()
        cls.ICP = cls.env['ir.config_parameter'].sudo()
        # limpiar claves heredadas para aislar la prueba
        for p in ('estate_ai.api_key', 'estate_ai.model',
                  'estate_ai.openai_api_key', 'estate_ai.openai_model',
                  'estate_ai.gemini_api_key', 'estate_ai.gemini_model'):
            cls.ICP.set_param(p, '')

    def test_chain_vacia_sin_claves(self):
        self.ICP.set_param('estate_ai.provider', 'chatgpt')
        self.assertEqual(self.ctrl._ai_provider_chain(self.ICP), [],
                         "Sin ninguna API Key la cadena debe estar vacía")

    def test_proveedor_activo_primero(self):
        self.ICP.set_param('estate_ai.provider', 'gemini')
        self.ICP.set_param('estate_ai.gemini_api_key', 'KEY_G')
        self.ICP.set_param('estate_ai.openai_api_key', 'KEY_O')
        chain = self.ctrl._ai_provider_chain(self.ICP)
        self.assertEqual([c[0] for c in chain], ['gemini', 'chatgpt'],
                         "El proveedor activo va primero y el otro de respaldo")

    def test_respaldo_solo_si_tiene_clave(self):
        self.ICP.set_param('estate_ai.provider', 'chatgpt')
        self.ICP.set_param('estate_ai.openai_api_key', 'KEY_O')
        self.ICP.set_param('estate_ai.gemini_api_key', '')
        chain = self.ctrl._ai_provider_chain(self.ICP)
        self.assertEqual([c[0] for c in chain], ['chatgpt'],
                         "Sin clave del otro proveedor no hay respaldo")

    def test_compatibilidad_clave_heredada(self):
        self.ICP.set_param('estate_ai.provider', 'gemini')
        self.ICP.set_param('estate_ai.gemini_api_key', '')
        self.ICP.set_param('estate_ai.api_key', 'KEY_LEGACY')
        chain = self.ctrl._ai_provider_chain(self.ICP)
        self.assertTrue(chain and chain[0][0] == 'gemini' and chain[0][1] == 'KEY_LEGACY',
                        "Debe usar la clave heredada para el proveedor activo")

    def test_modelo_por_defecto(self):
        self.ICP.set_param('estate_ai.provider', 'chatgpt')
        self.ICP.set_param('estate_ai.openai_api_key', 'KEY_O')
        self.ICP.set_param('estate_ai.openai_model', '')
        chain = self.ctrl._ai_provider_chain(self.ICP)
        self.assertEqual(chain[0][2], 'gpt-4o-mini',
                         "Sin modelo configurado usa el modelo por defecto del proveedor")

    def test_mensajes_degradados(self):
        self.assertIn('crédito', self.ctrl._friendly_ai_error(
            'gemini', Exception('Error 429 insufficient_quota')).lower())
        self.assertIn('autenticarse', self.ctrl._friendly_ai_error(
            'chatgpt', Exception('Invalid API key 401')).lower())
        self.assertIn('red', self.ctrl._friendly_ai_error(
            'gemini', Exception('Connection timeout')).lower())
        # caso genérico
        self.assertIn('no está disponible', self.ctrl._friendly_ai_error(
            'gemini', Exception('algo raro')).lower())
