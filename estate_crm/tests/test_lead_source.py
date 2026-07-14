from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'estate_lead_source')
class TestLeadSource(TransactionCase):
    """Fuente del Lead: catálogo editable (antes era una lista fija)."""

    def test_seed_sources_existen(self):
        website = self.env.ref('estate_crm.lead_source_website')
        self.assertEqual(website.code, 'website')
        self.assertTrue(self.env.ref('estate_crm.lead_source_other'))

    def test_default_del_lead_es_sitio_web(self):
        lead = self.env['crm.lead'].create({'name': 'Lead Test Fuente'})
        self.assertEqual(lead.lead_source_id.code, 'website')

    def test_usuario_puede_crear_una_fuente_nueva(self):
        """Simula lo que hace el widget Many2one al elegir "Crear" en el
        desplegable: una fuente nueva, sin código técnico, usable de inmediato."""
        nueva = self.env['estate.crm.lead.source'].create({'name': 'Feria Inmobiliaria 2026'})
        lead = self.env['crm.lead'].create({
            'name': 'Lead Feria', 'lead_source_id': nueva.id,
        })
        self.assertEqual(lead.lead_source_id.name, 'Feria Inmobiliaria 2026')
        self.assertFalse(lead.lead_source_id.code, "Una fuente creada a mano no necesita código")
        self.assertEqual(lead.lead_source_code, False)

    def test_get_by_code_encuentra_la_fuente(self):
        Source = self.env['estate.crm.lead.source']
        self.assertEqual(Source.get_by_code('whatsapp').code, 'whatsapp')

    def test_get_by_code_cae_en_otro_si_no_existe(self):
        Source = self.env['estate.crm.lead.source']
        self.assertEqual(Source.get_by_code('canal_inexistente_xyz').code, 'other')

    def test_lead_source_code_related_se_actualiza(self):
        lead = self.env['crm.lead'].create({
            'name': 'Lead Test Related',
            'lead_source_id': self.env.ref('estate_crm.lead_source_whatsapp').id,
        })
        self.assertEqual(lead.lead_source_code, 'whatsapp')

    def test_migracion_es_segura_de_repetir(self):
        """Ya no existe la columna vieja; volver a llamar la migración no debe fallar."""
        self.env['crm.lead']._migrate_legacy_lead_source()

    def test_codigo_de_fuente_es_unico(self):
        with self.assertRaises(Exception):
            self.env['estate.crm.lead.source'].create({'name': 'Duplicado', 'code': 'whatsapp'})
            self.env.cr.flush()
