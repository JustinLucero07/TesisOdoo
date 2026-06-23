# -*- coding: utf-8 -*-
"""Audit Log para Inmobi (adaptado a Odoo 19).

Registra quién creó, modificó o eliminó los registros clave del sistema,
con el detalle de los campos que cambiaron (valor anterior → nuevo).

Inspirado en el módulo OCA `auditlog` pero reescrito de forma ligera y
nativa para Odoo 19 (sin parcheo dinámico de métodos): un mixin que los
modelos auditados heredan.
"""
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)

# Campos que NUNCA se registran (ruido técnico)
_SKIP_FIELDS = {
    'write_date', 'write_uid', 'create_date', 'create_uid',
    '__last_update', 'display_name', 'access_token',
}


class EstateAuditLog(models.Model):
    _name = 'estate.audit.log'
    _description = 'Registro de Auditoría'
    _order = 'create_date desc'
    _rec_name = 'res_name'

    user_id = fields.Many2one('res.users', string='Usuario', index=True, readonly=True)
    model_name = fields.Char(string='Modelo', index=True, readonly=True)
    model_label = fields.Char(string='Tipo de Registro', readonly=True)
    res_id = fields.Integer(string='ID del Registro', index=True, readonly=True)
    res_name = fields.Char(string='Registro', readonly=True)
    method = fields.Selection([
        ('create', 'Creación'),
        ('write', 'Modificación'),
        ('unlink', 'Eliminación'),
    ], string='Acción', index=True, readonly=True)
    changes = fields.Text(string='Cambios', readonly=True)
    log_date = fields.Datetime(string='Fecha', readonly=True, default=fields.Datetime.now)

    def _check_admin(self):
        # Los logs no se editan ni borran manualmente (integridad de auditoría)
        return self.env.user.has_group('estate_management.estate_group_admin')

    def write(self, vals):
        if not self.env.context.get('audit_internal'):
            return True  # bloqueado: la auditoría es de solo lectura
        return super().write(vals)

    def unlink(self):
        if not self._check_admin():
            return True  # solo admin puede purgar
        return super().unlink()


class AuditLogMixin(models.AbstractModel):
    """Mixin que registra create/write/unlink en estate.audit.log."""
    _name = 'estate.audit.mixin'
    _description = 'Mixin de Auditoría'

    def _audit_enabled(self):
        ICP = self.env['ir.config_parameter'].sudo()
        return ICP.get_param('estate_audit.enabled', 'True') == 'True'

    def _audit_fmt(self, field, value):
        """Formato legible de un valor para el log."""
        try:
            f = self._fields.get(field)
            if value is False or value is None:
                return '∅'
            if f and f.type == 'many2one':
                return value.display_name if value else '∅'
            if f and f.type in ('one2many', 'many2many'):
                return f"{len(value)} reg."
            if f and f.type == 'selection':
                sel = dict(f._description_selection(self.env))
                return sel.get(value, str(value))
            if f and f.type == 'binary':
                return '[archivo]'
            s = str(value)
            return (s[:120] + '…') if len(s) > 120 else s
        except Exception:
            return str(value)

    def _audit_create(self, method, changes):
        for rec in self:
            self.env['estate.audit.log'].sudo().with_context(audit_internal=True).create({
                'user_id': self.env.uid,
                'model_name': rec._name,
                'model_label': self.env['ir.model']._get(rec._name).name or rec._name,
                'res_id': rec.id,
                'res_name': (rec.display_name or '')[:200],
                'method': method,
                'changes': changes or '',
                'log_date': fields.Datetime.now(),
            })

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if self._audit_enabled():
            try:
                records._audit_create('create', None)
            except Exception as e:
                _logger.warning("Audit create falló en %s: %s", self._name, e)
        return records

    def write(self, vals):
        audit = self._audit_enabled() and not self.env.context.get('audit_internal')
        before = {}
        if audit:
            # Se auditan los campos almacenados que el usuario puede modificar:
            # planos, o computados-editables (compute + readonly=False, patron
            # habitual en Odoo moderno como crm.lead.name). Se excluyen solo los
            # computados de solo-lectura para evitar ruido de recalculos.
            tracked = [f for f in vals if f not in _SKIP_FIELDS and f in self._fields
                       and self._fields[f].store
                       and (not self._fields[f].compute or not self._fields[f].readonly)]
            before = {rec.id: {f: rec[f] for f in tracked} for rec in self}
        res = super().write(vals)
        if audit and before:
            for rec in self:
                lines = []
                for f, old in before.get(rec.id, {}).items():
                    new = rec[f]
                    if old != new:
                        lines.append(f"{self._fields[f].string}: "
                                     f"{rec._audit_fmt(f, old)} → {rec._audit_fmt(f, new)}")
                if lines:
                    try:
                        rec._audit_create('write', '\n'.join(lines))
                    except Exception as e:
                        _logger.warning("Audit write falló en %s: %s", self._name, e)
        return res

    def unlink(self):
        if self._audit_enabled():
            try:
                self._audit_create('unlink', None)
            except Exception as e:
                _logger.warning("Audit unlink falló en %s: %s", self._name, e)
        return super().unlink()


# ── Aplicar la auditoría a los modelos clave ────────────────────────────────
class PropertyAudit(models.Model):
    _name = 'estate.property'
    _inherit = ['estate.property', 'estate.audit.mixin']


class ContractAudit(models.Model):
    _name = 'estate.contract'
    _inherit = ['estate.contract', 'estate.audit.mixin']


class PaymentAudit(models.Model):
    _name = 'estate.payment'
    _inherit = ['estate.payment', 'estate.audit.mixin']


class CommissionAudit(models.Model):
    _name = 'estate.commission'
    _inherit = ['estate.commission', 'estate.audit.mixin']


class OfferAudit(models.Model):
    _name = 'estate.property.offer'
    _inherit = ['estate.property.offer', 'estate.audit.mixin']


class LeadAudit(models.Model):
    _name = 'crm.lead'
    _inherit = ['crm.lead', 'estate.audit.mixin']
