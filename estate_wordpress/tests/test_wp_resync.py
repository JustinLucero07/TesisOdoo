from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'estate_wp_resync')
class TestWpResync(TransactionCase):
    """Marca de re-sincronización de WordPress (wp_needs_sync)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ptype = cls.env['estate.property.type'].create({'name': 'Casa Test WP'})
        # Las propiedades nacen en Borrador; la re-sincronización aplica a las
        # que están en el mercado.
        cls.prop = cls.env['estate.property'].create({
            'title': 'Casa WP', 'price': 100000.0,
            'property_type_id': cls.ptype.id,
            'state': 'available',
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

    def test_unpublish_al_marcar_vendida(self):
        self.prop.with_context(no_wp_sync=True).write({'wp_published': True, 'wp_post_id': 0})
        self.prop.write({'state': 'sold'})
        self.assertFalse(self.prop.wp_published,
                         "Al marcar como vendida debe despublicarse automáticamente")

    def test_cron_unpublish_sold_properties(self):
        # Desactivar integración activa para test local síncrono limpio
        self.env['ir.config_parameter'].sudo().set_param('estate_wp.active', 'False')
        self.prop.with_context(no_wp_sync=True).write({
            'state': 'sold',
            'wp_published': True,
        })
        self.env['estate.property']._cron_unpublish_sold_properties()
        self.assertFalse(self.prop.wp_published,
                         "El cron debe limpiar wp_published en propiedades vendidas")


    def test_asesor_de_la_web_es_el_captador(self):
        Users = self.env['res.users']
        responsable = Users.create({'name': 'Responsable WP', 'login': 'resp_wp@test.com'})
        captador = Users.create({'name': 'Captador WP', 'login': 'capt_wp@test.com'})
        agente = self.env['estate.wp.agent'].create({'wp_id': '9911', 'name': 'Captador WP'})
        captador.wp_agent_id = agente
        self.prop.write({'user_id': responsable.id, 'exclusive_user_id': captador.id})
        self.assertEqual(self.prop._wp_agent_user(), captador)
        meta = self.prop._build_houzez_meta(self.prop._get_wp_config(), False, [])
        self.assertEqual(meta.get('fave_agents'), '9911')
        # Sin captador, sale el responsable
        self.prop.exclusive_user_id = False
        self.assertEqual(self.prop._wp_agent_user(), responsable)

    def test_cambiar_captador_marca_re_sync(self):
        self.prop.with_context(no_wp_sync=True).write({'wp_published': True})
        otro = self.env['res.users'].create({'name': 'Otro captador', 'login': 'otro_wp@test.com'})
        self.prop.write({'exclusive_user_id': otro.id})
        self.assertTrue(self.prop.wp_needs_sync)
