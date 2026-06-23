from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'estate_audit_smoke')
class TestAuditLog(TransactionCase):
    """Pruebas de humo del registro de auditoría (mixin sobre crm.lead)."""

    def test_create_genera_log(self):
        Log = self.env['estate.audit.log']
        lead = self.env['crm.lead'].create({'name': 'Lead Auditoría Test'})
        logs = Log.search([
            ('model_name', '=', 'crm.lead'),
            ('res_id', '=', lead.id),
            ('method', '=', 'create'),
        ])
        self.assertTrue(
            logs, "Crear un crm.lead debe generar un log de auditoría 'create'")

    def test_write_campo_editable_genera_log(self):
        """Editar un campo computado-editable (crm.lead.name) debe auditarse."""
        Log = self.env['estate.audit.log']
        lead = self.env['crm.lead'].create({'name': 'Lead Audit Write'})
        lead.write({'name': 'Lead Audit Write Modificado'})
        logs = Log.search([
            ('model_name', '=', 'crm.lead'),
            ('res_id', '=', lead.id),
            ('method', '=', 'write'),
        ])
        self.assertTrue(
            logs, "Modificar crm.lead.name (computado-editable) debe generar un log 'write'")

    def test_unlink_genera_log(self):
        Log = self.env['estate.audit.log']
        lead = self.env['crm.lead'].create({'name': 'Lead Audit Unlink'})
        lead_id = lead.id
        lead.unlink()
        logs = Log.search([
            ('model_name', '=', 'crm.lead'),
            ('res_id', '=', lead_id),
            ('method', '=', 'unlink'),
        ])
        self.assertTrue(
            logs, "Eliminar un crm.lead debe generar un log de auditoría 'unlink'")

    def test_audit_desactivable(self):
        """Con estate_audit.enabled=False no se debe registrar."""
        ICP = self.env['ir.config_parameter'].sudo()
        ICP.set_param('estate_audit.enabled', 'False')
        try:
            lead = self.env['crm.lead'].create({'name': 'Lead Sin Auditoría'})
            logs = self.env['estate.audit.log'].search([
                ('model_name', '=', 'crm.lead'),
                ('res_id', '=', lead.id),
            ])
            self.assertFalse(logs, "Con la auditoría desactivada no debe haber log")
        finally:
            ICP.set_param('estate_audit.enabled', 'True')
