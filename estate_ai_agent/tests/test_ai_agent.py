from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'estate_ai_agent_smoke')
class TestAIAgentModels(TransactionCase):
    """Pruebas de humo de los modelos del agente IA (sin llamar APIs externas)."""

    def test_memory_crud_y_recuperacion(self):
        Memory = self.env['estate.ai.memory']
        mem = Memory.create({
            'user_id': self.env.uid,
            'memory_type': 'fact',
            'title': 'Cliente prefiere casas',
            'content': 'El cliente prefiere casas en Cuenca con jardín.',
        })
        self.assertTrue(mem.is_active, "Una memoria nueva debe estar activa")

        results = Memory.get_active_memories_for_user(self.env.uid)
        titles = [r['title'] for r in results]
        self.assertIn(
            'Cliente prefiere casas', titles,
            "get_active_memories_for_user debe devolver la memoria del usuario")

    def test_memory_expirada_no_se_recupera(self):
        from datetime import date, timedelta
        Memory = self.env['estate.ai.memory']
        mem = Memory.create({
            'user_id': self.env.uid,
            'memory_type': 'fact',
            'title': 'Memoria expirada',
            'content': 'Contenido.',
            'expires_at': date.today() - timedelta(days=1),
        })
        self.assertFalse(
            mem.is_active, "Una memoria con expires_at en el pasado debe quedar inactiva")
        results = Memory.get_active_memories_for_user(self.env.uid)
        titles = [r['title'] for r in results]
        self.assertNotIn('Memoria expirada', titles)

    def test_chat_history_create(self):
        chat = self.env['estate.ai.chat.history'].create(
            {'query': 'Hola asistente, ¿qué propiedades hay disponibles?'})
        self.assertTrue(chat.exists(), "Debe poder registrarse el historial de chat")
