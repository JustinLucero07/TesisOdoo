from odoo.tests.common import HttpCase, tagged


@tagged('post_install', '-at_install', 'estate_portal_smoke')
class TestPortalRoutes(HttpCase):
    """Prueba de humo: las páginas del portal del propietario responden."""

    def test_portal_properties_responde(self):
        user = self.env['res.users'].create({
            'name': 'Portal Test User',
            'login': 'portal_test_user',
            'password': 'portal_test_user',
            'group_ids': [(6, 0, [self.env.ref('base.group_portal').id])],
        })
        self.assertTrue(user.exists())
        self.authenticate('portal_test_user', 'portal_test_user')
        resp = self.url_open('/my/properties')
        self.assertEqual(
            resp.status_code, 200,
            "La página /my/properties debe responder 200 para un usuario del portal")
