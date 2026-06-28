from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'estate_doc_expiry')
class TestDocumentExpiry(TransactionCase):
    """Aviso de documentos próximos a vencer (cron + reinicio de la marca)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dtype = cls.env['estate.document.type'].search([], limit=1)
        if not cls.dtype:
            cls.dtype = cls.env['estate.document.type'].create({'name': 'Tipo Test'})

    def _doc(self, expiration):
        # Estado 'pending' evita la restricción de archivo obligatorio.
        return self.env['estate.document'].create({
            'name': 'Doc Test', 'type_id': self.dtype.id,
            'expiration_date': expiration, 'state': 'pending',
        })

    def test_cron_crea_aviso_y_marca(self):
        doc = self._doc(fields.Date.today() + timedelta(days=10))
        self.env['estate.document']._cron_notify_expiring_documents()
        self.assertTrue(doc.expiry_notified, "Un documento por vencer debe quedar notificado")
        self.assertTrue(doc.activity_ids, "Debe crear una actividad recordatorio")

    def test_no_notifica_vencimiento_lejano(self):
        doc = self._doc(fields.Date.today() + timedelta(days=200))
        self.env['estate.document']._cron_notify_expiring_documents()
        self.assertFalse(doc.expiry_notified, "Un vencimiento lejano no debe notificarse aún")

    def test_no_notifica_dos_veces(self):
        doc = self._doc(fields.Date.today() + timedelta(days=5))
        self.env['estate.document']._cron_notify_expiring_documents()
        n1 = len(doc.activity_ids)
        self.env['estate.document']._cron_notify_expiring_documents()
        self.assertEqual(len(doc.activity_ids), n1, "No debe duplicar el aviso")

    def test_reset_al_cambiar_fecha(self):
        doc = self._doc(fields.Date.today() + timedelta(days=5))
        self.env['estate.document']._cron_notify_expiring_documents()
        self.assertTrue(doc.expiry_notified)
        doc.write({'expiration_date': fields.Date.today() + timedelta(days=400)})
        self.assertFalse(doc.expiry_notified, "Cambiar la fecha de vencimiento reinicia el aviso")
