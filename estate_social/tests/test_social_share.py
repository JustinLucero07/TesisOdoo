from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'estate_social_share')
class TestSocialShare(TransactionCase):
    """Generación de enlaces para compartir en redes (sin llamadas externas)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ptype = cls.env['estate.property.type'].create({'name': 'Casa Social Test'})
        cls.prop = cls.env['estate.property'].create({
            'title': 'Casa Bonita', 'price': 85000.0, 'city': 'Cuenca',
            'property_type_id': ptype.id,
        })

    def test_share_facebook_url(self):
        action = self.prop.action_share_facebook()
        self.assertEqual(action['type'], 'ir.actions.act_url')
        self.assertIn('facebook.com/sharer', action['url'])

    def test_share_whatsapp_url(self):
        action = self.prop.action_share_whatsapp()
        self.assertEqual(action['type'], 'ir.actions.act_url')
        self.assertIn('wa.me', action['url'])

    def test_share_twitter_url(self):
        action = self.prop.action_share_twitter()
        self.assertIn('twitter.com/intent/tweet', action['url'])

    def test_whatsapp_business_sin_numero_avisa(self):
        self.env['ir.config_parameter'].sudo().set_param(
            'estate_social.whatsapp_business_number', '')
        action = self.prop.action_whatsapp_business_contact()
        # Sin número configurado debe devolver una notificación, no una URL.
        self.assertEqual(action['tag'], 'display_notification')

    def test_whatsapp_business_con_numero_genera_link(self):
        self.env['ir.config_parameter'].sudo().set_param(
            'estate_social.whatsapp_business_number', '593981234567')
        action = self.prop.action_whatsapp_business_contact()
        self.assertEqual(action['type'], 'ir.actions.act_url')
        self.assertIn('wa.me/593981234567', action['url'])
