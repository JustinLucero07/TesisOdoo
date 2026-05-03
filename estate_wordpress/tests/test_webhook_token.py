"""Tests del helper _verify_wp_token usado por los 3 endpoints públicos.

Testea fail-closed: si no hay secreto configurado, debe rechazar (no abrir).
También prueba el comportamiento con tokens válidos/inválidos y vía header X-WP-Secret.
"""
from unittest.mock import patch, MagicMock

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.estate_wordpress.controllers.main import EstateWordpressController


@tagged('post_install', '-at_install', 'estate_wp_webhook')
class TestWebhookTokenValidation(TransactionCase):

    def setUp(self):
        super().setUp()
        self.controller = EstateWordpressController()
        self.ICP = self.env['ir.config_parameter'].sudo()

    def _patch_request(self, headers=None, remote_addr='127.0.0.1'):
        """Mockea odoo.http.request para que el controller pueda ejecutarse fuera de HTTP."""
        req = MagicMock()
        req.env = self.env
        req.httprequest = MagicMock()
        req.httprequest.headers = headers or {}
        req.httprequest.remote_addr = remote_addr
        return patch('odoo.addons.estate_wordpress.controllers.main.request', req)

    def test_no_secret_configured_rejects(self):
        """Sin secret en config → debe rechazar (fail-closed)."""
        self.ICP.set_param('estate_wp.webhook_secret', '')
        with self._patch_request():
            result = self.controller._verify_wp_token({'secret': 'whatever'})
        self.assertFalse(result, 'Debe rechazar cuando no hay secret configurado')

    def test_valid_token_in_body_accepts(self):
        self.ICP.set_param('estate_wp.webhook_secret', 'super-secret-123')
        with self._patch_request():
            result = self.controller._verify_wp_token({'secret': 'super-secret-123'})
        self.assertTrue(result)

    def test_valid_token_in_header_accepts(self):
        self.ICP.set_param('estate_wp.webhook_secret', 'super-secret-123')
        with self._patch_request(headers={'X-WP-Secret': 'super-secret-123'}):
            result = self.controller._verify_wp_token({})
        self.assertTrue(result)

    def test_invalid_token_rejects(self):
        self.ICP.set_param('estate_wp.webhook_secret', 'super-secret-123')
        with self._patch_request():
            result = self.controller._verify_wp_token({'secret': 'wrong-token'})
        self.assertFalse(result)

    def test_missing_token_rejects(self):
        self.ICP.set_param('estate_wp.webhook_secret', 'super-secret-123')
        with self._patch_request():
            result = self.controller._verify_wp_token({})
        self.assertFalse(result)

    def test_empty_token_rejects(self):
        self.ICP.set_param('estate_wp.webhook_secret', 'super-secret-123')
        with self._patch_request():
            result = self.controller._verify_wp_token({'secret': ''})
        self.assertFalse(result)
