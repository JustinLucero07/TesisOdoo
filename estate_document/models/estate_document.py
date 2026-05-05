import base64

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError

ALLOWED_EXTENSIONS = ('.pdf', '.doc', '.docx', '.xls', '.xlsx',
                      '.jpg', '.jpeg', '.png', '.gif', '.webp')
MAX_FILE_SIZE_MB = 10


class EstateDocument(models.Model):
    _name = 'estate.document'
    _description = 'Documento Inmobiliario'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    # ── Identificación ───────────────────────────────────────────────────────
    name = fields.Char(
        string='Nombre del Documento', required=True, tracking=True)
    type_id = fields.Many2one(
        'estate.document.type', string='Tipo', required=True,
        index=True, tracking=True,
        help='Tipo específico del documento (ej: Contrato firmado, Avalúo, etc.).')
    type_category = fields.Selection(
        related='type_id.category', store=True, string='Categoría',
        help='Categoría heredada del tipo. Útil para filtros y kanban.')

    # ── Vinculación a entidades del negocio ──────────────────────────────────
    property_id = fields.Many2one(
        'estate.property', string='Propiedad', index=True)
    partner_id = fields.Many2one(
        'res.partner', string='Cliente / Contacto', index=True)
    lead_id = fields.Many2one(
        'crm.lead', string='Oportunidad / Lead', index=True)
    contract_id = fields.Many2one(
        'estate.contract', string='Contrato', index=True, ondelete='set null',
        help='Contrato al que pertenece este documento (si aplica).')

    # ── Archivo ──────────────────────────────────────────────────────────────
    file = fields.Binary(string='Archivo', attachment=True,
        help='Opcional si el documento está en estado Pendiente (placeholder).')
    filename = fields.Char(string='Nombre del Archivo')
    file_size = fields.Float(
        string='Tamaño (MB)', compute='_compute_file_size', store=True)

    # ── Ciclo de vida ────────────────────────────────────────────────────────
    state = fields.Selection([
        ('pending',   'Pendiente'),
        ('received',  'Recibido'),
        ('verified',  'Verificado'),
        ('rejected',  'Rechazado'),
        ('archived',  'Archivado'),
    ], string='Estado', default='received', tracking=True, required=True,
        help='Pendiente: aún no llega · Recibido: cargado pero sin verificar · '
             'Verificado: validado por un manager · Rechazado: documento inválido · '
             'Archivado: finalizado.')
    verified_by = fields.Many2one(
        'res.users', string='Verificado por', readonly=True, tracking=True)
    verified_date = fields.Datetime(
        string='Fecha de verificación', readonly=True, tracking=True)
    rejection_reason = fields.Char(
        string='Razón de rechazo', tracking=True,
        help='Por qué fue rechazado el documento (visible al cargarlo de nuevo).')

    # ── Confidencialidad ─────────────────────────────────────────────────────
    confidentiality = fields.Selection([
        ('public',       'Público'),
        ('internal',     'Interno (todos los asesores)'),
        ('restricted',   'Restringido (asesor responsable + manager)'),
        ('confidential', 'Confidencial (solo manager y admin)'),
    ], string='Confidencialidad', default='internal', required=True, tracking=True)

    # ── Metadata ─────────────────────────────────────────────────────────────
    date = fields.Date(
        string='Fecha del documento', default=fields.Date.today, tracking=True)
    expiration_date = fields.Date(
        string='Fecha de vencimiento',
        help='Para documentos con expiración (ej: certificados anuales).')
    notes = fields.Text(string='Notas')
    uploaded_by = fields.Many2one(
        'res.users', string='Cargado por',
        default=lambda self: self.env.user, readonly=True)
    active = fields.Boolean(string='Activo', default=True)

    # ── Computed ─────────────────────────────────────────────────────────────
    @api.depends('file')
    def _compute_file_size(self):
        for rec in self:
            if rec.file:
                rec.file_size = round(len(base64.b64decode(rec.file)) / (1024 * 1024), 2)
            else:
                rec.file_size = 0.0

    # ── Validaciones ─────────────────────────────────────────────────────────
    @api.constrains('file', 'state')
    def _check_file_required_when_not_pending(self):
        for rec in self:
            if rec.state != 'pending' and not rec.file:
                raise ValidationError(
                    f'El documento "{rec.name}" debe tener un archivo cargado para pasar '
                    f'del estado Pendiente. Sube el archivo o vuelve a estado Pendiente.'
                )

    @api.constrains('file', 'filename')
    def _check_file_type_and_size(self):
        for rec in self:
            if rec.filename:
                ext = '.' + rec.filename.rsplit('.', 1)[-1].lower() if '.' in rec.filename else ''
                if ext not in ALLOWED_EXTENSIONS:
                    raise ValidationError(
                        f'Tipo de archivo no permitido: "{ext}". '
                        f'Formatos aceptados: {", ".join(ALLOWED_EXTENSIONS)}')
            if rec.file:
                size_mb = len(base64.b64decode(rec.file)) / (1024 * 1024)
                if size_mb > MAX_FILE_SIZE_MB:
                    raise ValidationError(
                        f'El archivo excede el tamaño máximo permitido de {MAX_FILE_SIZE_MB} MB '
                        f'(tamaño actual: {size_mb:.1f} MB).')

    # ── Auto-transición al subir archivo en placeholder ──────────────────────
    def write(self, vals):
        # Si se sube un archivo a un placeholder, pasar automáticamente a 'received'
        if 'file' in vals and vals['file']:
            for rec in self:
                if rec.state == 'pending':
                    vals = dict(vals)
                    vals.setdefault('state', 'received')
                    rec.message_post(body='📥 Documento cargado, marcado como Recibido.')
                    break
        return super().write(vals)

    # ── Acciones del ciclo de vida ───────────────────────────────────────────
    def action_mark_received(self):
        for rec in self:
            rec.state = 'received'

    def action_verify(self):
        """Marca como verificado. Solo managers/admins pueden hacerlo."""
        if not self.env.user.has_group('estate_management.estate_group_manager'):
            raise UserError('Solo un manager puede verificar documentos.')
        for rec in self:
            rec.write({
                'state': 'verified',
                'verified_by': self.env.user.id,
                'verified_date': fields.Datetime.now(),
                'rejection_reason': False,
            })
            rec.message_post(body=f'✅ Documento verificado por {self.env.user.name}.')

    def action_reject(self):
        """Abre wizard simple para indicar razón de rechazo."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Rechazar documento',
            'res_model': 'estate.document.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_document_id': self.id},
        }

    def action_archive_doc(self):
        for rec in self:
            rec.state = 'archived'
            rec.message_post(body=f'📦 Documento archivado por {self.env.user.name}.')

    def action_reset_to_pending(self):
        for rec in self:
            rec.write({
                'state': 'pending',
                'verified_by': False,
                'verified_date': False,
            })


class EstateDocumentRejectWizard(models.TransientModel):
    """Wizard simple para capturar la razón de rechazo de un documento."""
    _name = 'estate.document.reject.wizard'
    _description = 'Wizard de rechazo de documento'

    document_id = fields.Many2one('estate.document', required=True)
    reason = fields.Char(string='Razón del rechazo', required=True)

    def action_confirm_reject(self):
        self.ensure_one()
        self.document_id.write({
            'state': 'rejected',
            'rejection_reason': self.reason,
        })
        self.document_id.message_post(
            body=f'❌ Documento rechazado: {self.reason}')
        return {'type': 'ir.actions.act_window_close'}
