from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'estate_crm_dedup')
class TestMetaWebhookDedup(TransactionCase):
    """Tests para estate.meta.webhook.event (UNIQUE en event_id + idempotencia)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Dedup = cls.env['estate.meta.webhook.event']

    def test_register_new_event(self):
        rec = self.Dedup.register('msg-123', channel='whatsapp', summary='Hola')
        self.assertTrue(rec)
        self.assertEqual(rec.event_id, 'msg-123')
        self.assertEqual(rec.channel, 'whatsapp')

    def test_duplicate_event_returns_false(self):
        self.Dedup.register('msg-456', channel='facebook')
        # Segundo intento debe fallar (UNIQUE) y retornar False
        result = self.Dedup.register('msg-456', channel='facebook')
        self.assertFalse(result)

    def test_is_already_processed_true(self):
        self.Dedup.register('msg-789', channel='instagram')
        self.assertTrue(self.Dedup.is_already_processed('msg-789'))

    def test_is_already_processed_false_for_unknown(self):
        self.assertFalse(self.Dedup.is_already_processed('msg-noexist'))

    def test_empty_event_id_not_processed(self):
        self.assertFalse(self.Dedup.is_already_processed(''))
        self.assertFalse(self.Dedup.is_already_processed(None))

    def test_register_empty_event_id_returns_false(self):
        self.assertFalse(self.Dedup.register('', channel='whatsapp'))
        self.assertFalse(self.Dedup.register(None, channel='whatsapp'))

    def test_register_links_to_lead(self):
        lead = self.env['crm.lead'].create({'name': 'Lead test dedup'})
        rec = self.Dedup.register('msg-with-lead', channel='whatsapp', lead=lead)
        self.assertEqual(rec.lead_id.id, lead.id)

    def test_summary_truncated_to_255(self):
        long = 'X' * 500
        rec = self.Dedup.register('msg-long-summary', channel='whatsapp', summary=long)
        self.assertEqual(len(rec.payload_summary), 255)
