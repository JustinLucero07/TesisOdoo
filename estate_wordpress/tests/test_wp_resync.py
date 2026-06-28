from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'estate_wp_resync')
class TestWpResync(TransactionCase):
    """Marca de re-sincronización de WordPress (wp_needs_sync)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ptype = cls.env['estate.property.type'].create({'name': 'Casa Test WP'})
        cls.prop = cls.env['estate.property'].create({
            'title': 'Casa WP', 'price': 100000.0,
            'property_type_id': cls.ptype.id,
        })

    def test_no_marca_si_no_publicada(self):
        self.prop.write({'price': 120000})
        self.assertFalse(self.prop.wp_needs_sync,
                         "Una propiedad no publicada no debe marcarse para re-sync")

    def test_marca_al_cambiar_campo_relevante_publicada(self):
        self.prop.with_context(no_wp_sync=True).write({'wp_published': True})
        self.prop.write({'price': 130000})
        self.assertTrue(self.prop.wp_needs_sync,
                        "Un cambio relevante en una propiedad publicada marca re-sync")

    def test_no_marca_con_contexto_no_wp_sync(self):
        self.prop.with_context(no_wp_sync=True).write(
            {'wp_published': True, 'wp_needs_sync': False})
        self.prop.with_context(no_wp_sync=True).write({'price': 140000})
        self.assertFalse(self.prop.wp_needs_sync,
                         "Con contexto no_wp_sync no debe re-marcarse")

    def test_cron_respeta_toggle_desactivado(self):
        self.env['ir.config_parameter'].sudo().set_param('estate_wp.auto_resync', 'False')
        # No debe fallar ni sincronizar nada cuando el toggle está apagado.
        self.env['estate.property']._cron_wp_resync()
