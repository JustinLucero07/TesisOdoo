# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'estate_postventa_price')
class TestPostventaDealPrice(TransactionCase):
    """En el embudo Postventa el lead muestra el precio de la propiedad."""

    def test_precio_en_negociacion_y_de_venta(self):
        ptype = self.env['estate.property.type'].create({'name': 'Tipo PV'})
        prop = self.env['estate.property'].create({
            'title': 'Casa PV', 'price': 125000.0, 'property_type_id': ptype.id,
            'state': 'available'})
        team = self.env.ref('estate_crm.crm_team_postventa')
        stage = self.env['crm.stage'].search([('team_ids', 'in', team.id)], limit=1)
        lead = self.env['crm.lead'].create({
            'name': 'Lead PV', 'type': 'opportunity', 'target_property_id': prop.id,
            'stage_id': stage.id})
        self.assertTrue(lead.estate_is_postventa)
        self.assertAlmostEqual(lead.estate_deal_price, 125000.0)
        self.assertFalse(lead.estate_deal_price_sold)
        prop.write({'state': 'sold', 'price': 120000.0})
        lead.invalidate_recordset(['estate_deal_price', 'estate_deal_price_sold'])
        self.assertAlmostEqual(lead.estate_deal_price, 120000.0)
        self.assertTrue(lead.estate_deal_price_sold)
        # Fuera de postventa no se muestra
        other = self.env['crm.lead'].create({'name': 'Lead normal', 'type': 'opportunity'})
        self.assertFalse(other.estate_is_postventa)
        other.read(['estate_deal_price'])
