from types import SimpleNamespace
from unittest.mock import patch, MagicMock

from odoo.tests.common import TransactionCase, tagged
from odoo.addons.estate_ai_agent.controllers.estate_ai_controller import EstateAIController


def _fake_response(content, finish_reason='stop', tool_calls=None):
    message = SimpleNamespace(content=content, tool_calls=tool_calls)
    choice = SimpleNamespace(finish_reason=finish_reason, message=message)
    return SimpleNamespace(choices=[choice])


@tagged('post_install', '-at_install', 'estate_ai_no_hallucination')
class TestNoHallucinatedCharts(TransactionCase):
    """El agente IA no debe inventar cifras en [GRAFICO:...] sin haber
    consultado datos reales primero (bug: reportó "Ventas por Mes" con
    números de ejemplo del prompt cuando no había ventas registradas)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ctrl = EstateAIController()

    def test_grafico_sin_herramienta_de_datos_se_corrige(self):
        """Si el modelo responde con un [GRAFICO:...] sin haber llamado a
        ninguna herramienta de datos, el controlador debe forzar una
        corrección en vez de devolver la cifra inventada tal cual."""
        hallucinated = _fake_response(
            '[GRAFICO:linea|Ventas por Mes,Enero:5,Febrero:8,Marzo:12]')
        corrected = _fake_response(
            'Aún no hay ventas registradas en el sistema.')

        fake_client = MagicMock()
        fake_client.chat.completions.create.side_effect = [hallucinated, corrected]

        with patch('odoo.addons.estate_ai_agent.controllers.estate_ai_controller.openai.OpenAI',
                    return_value=fake_client):
            result = self.ctrl._query_chatgpt_with_tools(
                'fake-key', 'gpt-4o-mini', 0.7, 800,
                'system prompt', '¿cuáles son mis ventas?', [])

        self.assertEqual(fake_client.chat.completions.create.call_count, 2,
                          "Debe reintentar una vez al detectar un gráfico sin datos reales")
        self.assertNotIn('Enero:5', result)
        self.assertIn('Aún no hay ventas', result)

    def test_grafico_con_herramienta_de_datos_no_se_corrige(self):
        """Si el modelo SÍ llamó a get_report_data antes de generar el
        gráfico, no debe activarse la corrección (falso positivo)."""
        tool_call = SimpleNamespace(
            id='call_1',
            function=SimpleNamespace(name='get_report_data', arguments='{"report_type": "sales_by_month"}'),
        )
        with_tool_call = _fake_response(None, finish_reason='tool_calls', tool_calls=[tool_call])
        final = _fake_response('[GRAFICO:linea|Ventas por Mes,Enero:2]')

        fake_client = MagicMock()
        fake_client.chat.completions.create.side_effect = [with_tool_call, final]

        with patch('odoo.addons.estate_ai_agent.controllers.estate_ai_controller.openai.OpenAI',
                    return_value=fake_client), \
             patch.object(EstateAIController, '_execute_tool', return_value='{"data": {"Enero": 2}}'):
            result = self.ctrl._query_chatgpt_with_tools(
                'fake-key', 'gpt-4o-mini', 0.7, 800,
                'system prompt', 'reporte de ventas', [])

        self.assertEqual(fake_client.chat.completions.create.call_count, 2,
                          "Sin falso positivo: no debe haber una tercera llamada correctiva")
        self.assertIn('Enero:2', result)
