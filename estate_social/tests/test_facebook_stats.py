from unittest.mock import patch, MagicMock

from odoo.tests.common import TransactionCase, tagged


def _mock_resp(status_code, payload):
    m = MagicMock()
    m.status_code = status_code
    m.json.return_value = payload
    return m


@tagged('post_install', '-at_install', 'estate_social_fb')
class TestFacebookStatsFetch(TransactionCase):
    """Tests del método _fetch_stats con la Meta Graph API mockeada."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Stats = cls.env['estate.facebook.stats']
        cls.History = cls.env['estate.facebook.stats.history']
        # Token configurado para que pase la validación inicial
        cls.env['ir.config_parameter'].sudo().set_param(
            'estate_social.facebook_page_token', 'TEST_TOKEN_xxxxxxxxx')

    def _make_stats(self, post_id='12345_67890'):
        return self.Stats.create({'fb_post_id': post_id})

    def test_no_token_sets_fetch_error(self):
        self.env['ir.config_parameter'].sudo().set_param(
            'estate_social.facebook_page_token', '')
        rec = self._make_stats()
        rec._fetch_stats()
        self.assertIn('Page Access Token', rec.fetch_error or '')
        # Restore para otros tests
        self.env['ir.config_parameter'].sudo().set_param(
            'estate_social.facebook_page_token', 'TEST_TOKEN_xxxxxxxxx')

    def test_no_post_id_sets_fetch_error(self):
        rec = self.Stats.create({})  # sin fb_post_id ni property_id
        rec._fetch_stats()
        self.assertIn('Facebook Post ID', rec.fetch_error or '')

    def test_successful_fetch_with_reactions_and_insights(self):
        """API devuelve OK: campos del post + insights completos."""
        post_resp = _mock_resp(200, {
            'r_likes':   {'summary': {'total_count': 8}},
            'r_loves':   {'summary': {'total_count': 1}},
            'r_hahas':   {'summary': {'total_count': 0}},
            'r_wows':    {'summary': {'total_count': 0}},
            'r_sads':    {'summary': {'total_count': 0}},
            'r_angries': {'summary': {'total_count': 0}},
            'comments':  {'summary': {'total_count': 3}},
            'shares':    {'count': 2},
        })
        ins_resp = _mock_resp(200, {
            'data': [
                {'name': 'post_impressions',         'values': [{'value': 3250}]},
                {'name': 'post_impressions_unique',  'values': [{'value': 2293}]},
                {'name': 'post_clicks',              'values': [{'value': 55}]},
                {'name': 'post_impressions_fan_unique', 'values': [{'value': 900}]},
                {'name': 'post_impressions_organic_unique', 'values': [{'value': 3000}]},
            ],
        })

        with patch('odoo.addons.estate_social.models.estate_facebook_stats.request_with_retry',
                   side_effect=[post_resp, ins_resp]):
            rec = self._make_stats()
            rec._fetch_stats()

        self.assertFalse(rec.fetch_error)
        self.assertEqual(rec.likes, 8)
        self.assertEqual(rec.loves, 1)
        self.assertEqual(rec.comments, 3)
        self.assertEqual(rec.shares, 2)
        self.assertEqual(rec.impressions, 3250)
        self.assertEqual(rec.reach, 2293)
        self.assertEqual(rec.clicks, 55)
        self.assertEqual(rec.fan_reach, 900)
        self.assertEqual(rec.non_fan_reach, 2293 - 900)  # calculado
        self.assertEqual(rec.organic_reach, 3000)

    def test_post_api_error_sets_fetch_error(self):
        """API devuelve error en la consulta de campos del post."""
        post_resp = _mock_resp(400, {
            'error': {
                'message': 'Invalid OAuth access token',
                'code': 190,
            },
        })
        with patch('odoo.addons.estate_social.models.estate_facebook_stats.request_with_retry',
                   return_value=post_resp):
            rec = self._make_stats()
            rec._fetch_stats()

        self.assertIn('Invalid OAuth', rec.fetch_error)

    def test_insights_unavailable_keeps_reactions(self):
        """Insights falla por permisos pero las reacciones se guardan igual."""
        post_resp = _mock_resp(200, {
            'r_likes':   {'summary': {'total_count': 5}},
            'r_loves':   {'summary': {'total_count': 0}},
            'r_hahas':   {'summary': {'total_count': 0}},
            'r_wows':    {'summary': {'total_count': 0}},
            'r_sads':    {'summary': {'total_count': 0}},
            'r_angries': {'summary': {'total_count': 0}},
            'comments':  {'summary': {'total_count': 1}},
            'shares':    {'count': 0},
        })
        ins_resp = _mock_resp(403, {
            'error': {'message': '(#10) read_insights permission missing', 'code': 10},
        })

        with patch('odoo.addons.estate_social.models.estate_facebook_stats.request_with_retry',
                   side_effect=[post_resp, ins_resp]):
            rec = self._make_stats()
            rec._fetch_stats()

        # Las reacciones SÍ se guardan
        self.assertEqual(rec.likes, 5)
        self.assertEqual(rec.comments, 1)
        # Pero impressions/reach quedan en 0 y se reporta el error
        self.assertEqual(rec.impressions, 0)
        self.assertIn('read_insights', rec.fetch_error or '')

    def test_history_snapshot_created_on_success(self):
        """Cada _fetch_stats exitoso crea un snapshot en el historial."""
        post_resp = _mock_resp(200, {
            'r_likes': {'summary': {'total_count': 10}},
            'r_loves': {'summary': {'total_count': 0}},
            'r_hahas': {'summary': {'total_count': 0}},
            'r_wows':  {'summary': {'total_count': 0}},
            'r_sads':  {'summary': {'total_count': 0}},
            'r_angries': {'summary': {'total_count': 0}},
            'comments': {'summary': {'total_count': 0}},
            'shares': {'count': 0},
        })
        ins_resp = _mock_resp(200, {'data': []})

        with patch('odoo.addons.estate_social.models.estate_facebook_stats.request_with_retry',
                   side_effect=[post_resp, ins_resp]):
            rec = self._make_stats(post_id='98765_43210')
            rec._fetch_stats()

        snaps = self.History.search([('stats_id', '=', rec.id)])
        self.assertEqual(len(snaps), 1)
        self.assertEqual(snaps.total_reactions, 10)

    def test_age_gender_demographics_parsed(self):
        """Verifica que post_impressions_by_age_gender_unique se guarde como JSON."""
        post_resp = _mock_resp(200, {
            'r_likes': {'summary': {'total_count': 0}},
            'r_loves': {'summary': {'total_count': 0}},
            'r_hahas': {'summary': {'total_count': 0}},
            'r_wows':  {'summary': {'total_count': 0}},
            'r_sads':  {'summary': {'total_count': 0}},
            'r_angries': {'summary': {'total_count': 0}},
            'comments': {'summary': {'total_count': 0}},
            'shares': {'count': 0},
        })
        ins_resp = _mock_resp(200, {
            'data': [{
                'name': 'post_impressions_by_age_gender_unique',
                'values': [{'value': {'M.25-34': 150, 'F.25-34': 120, 'M.35-44': 90}}],
            }],
        })
        with patch('odoo.addons.estate_social.models.estate_facebook_stats.request_with_retry',
                   side_effect=[post_resp, ins_resp]):
            rec = self._make_stats(post_id='age_test_001')
            rec._fetch_stats()

        import json
        parsed = json.loads(rec.gender_age_data or '{}')
        self.assertEqual(parsed.get('M.25-34'), 150)
        self.assertEqual(parsed.get('F.25-34'), 120)
        self.assertEqual(parsed.get('M.35-44'), 90)
