# -*- coding: utf-8 -*-
"""Sector/barrio en WordPress (taxonomía property_area de Houzez).

Bug: la web mostraba solo "Cuenca, Azuay, Ecuador" y se perdía el sector
("Racar"). Houzez arma la línea de ubicación con las TAXONOMÍAS, y el código
solo enviaba property_type/property_status/property_city: nunca property_area.
"""
from unittest.mock import patch, MagicMock

from odoo.tests.common import TransactionCase, tagged


def _resp(status, payload):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = payload
    r.text = str(payload)
    return r


@tagged('post_install', '-at_install', 'estate_wp_area')
class TestWpAreaTaxonomy(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ptype = cls.env['estate.property.type'].create({'name': 'Casa Test WP Area'})
        cls.prop = cls.env['estate.property'].create({
            'title': 'Casa En Venta, Sector Racar',
            'property_type_id': cls.ptype.id,
            'price': 125000.0,
            'street': 'Racar',
            'city': 'Cuenca',
            'sector_keywords': 'Racar',
            'latitude': -2.8552132,
            'longitude': -79.0386519,
        })
        cls.cfg = {
            'url': 'https://wp.test', 'auth': ('u', 'p'), 'headers': {},
            'active': 'True', 'post_type': 'property', 'agent_id': '',
        }

    def test_sector_existente_se_reutiliza(self):
        """Si el término ya existe en WordPress, se usa su ID (no se duplica)."""
        with patch('odoo.addons.estate_wordpress.models.estate_wordpress_sync.requests') as rq:
            rq.get.return_value = _resp(200, [{'id': 77, 'name': 'Racar'}])
            ids = self.prop._get_houzez_area_ids(self.cfg)
        self.assertEqual(ids, [77])
        rq.post.assert_not_called()

    def test_sector_nuevo_se_crea(self):
        """Si no existe, se crea el término y se usa el ID devuelto."""
        with patch('odoo.addons.estate_wordpress.models.estate_wordpress_sync.requests') as rq:
            rq.get.return_value = _resp(200, [])
            rq.post.return_value = _resp(201, {'id': 91, 'name': 'Racar'})
            ids = self.prop._get_houzez_area_ids(self.cfg)
        self.assertEqual(ids, [91])

    def test_varios_sectores_separados_por_coma(self):
        self.prop.sector_keywords = 'Racar, El Valle'
        with patch('odoo.addons.estate_wordpress.models.estate_wordpress_sync.requests') as rq:
            rq.get.side_effect = [
                _resp(200, [{'id': 10, 'name': 'Racar'}]),
                _resp(200, [{'id': 20, 'name': 'El Valle'}]),
            ]
            ids = self.prop._get_houzez_area_ids(self.cfg)
        self.assertEqual(ids, [10, 20])

    def test_usa_la_calle_si_no_hay_sector(self):
        self.prop.sector_keywords = False
        with patch('odoo.addons.estate_wordpress.models.estate_wordpress_sync.requests') as rq:
            rq.get.return_value = _resp(200, [{'id': 55, 'name': 'Racar'}])
            self.prop._get_houzez_area_ids(self.cfg)
        # Se buscó por la calle ("Racar"), no quedó vacío
        self.assertEqual(rq.get.call_args.kwargs['params']['search'], 'Racar')

    def test_respeta_el_toggle_de_publicar_ubicacion(self):
        self.prop.wp_publish_location = False
        with patch('odoo.addons.estate_wordpress.models.estate_wordpress_sync.requests') as rq:
            ids = self.prop._get_houzez_area_ids(self.cfg)
        self.assertEqual(ids, [], "Si no se publica la ubicación, no se manda el sector")
        rq.get.assert_not_called()

    def test_el_post_incluye_la_taxonomia_property_area(self):
        """El payload que se envía a WordPress debe llevar property_area."""
        captured = {}

        def _fake_post(url, json=None, **kw):
            if url.endswith('/property'):        # creación del post
                captured.update(json or {})
                return _resp(201, {'id': 123})
            return _resp(201, {'id': 1})

        with patch('odoo.addons.estate_wordpress.models.estate_wordpress_sync.requests') as rq:
            rq.get.return_value = _resp(200, [{'id': 77, 'name': 'Racar'}])
            rq.post.side_effect = _fake_post
            self.prop._wp_create_or_update_post(self.cfg, featured_id=0)

        self.assertIn('property_area', captured,
                      "El post debe incluir la taxonomía del sector")
        self.assertEqual(captured['property_area'], [77])
        self.assertEqual(captured['title'], 'Casa En Venta, Sector Racar')
