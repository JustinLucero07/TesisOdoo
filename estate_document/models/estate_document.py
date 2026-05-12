import base64
import json
import logging
import mimetypes
import re

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)

# Tipos de archivo que Gemini Vision puede procesar
_OCR_SUPPORTED_MIMES = {
    'image/jpeg', 'image/png', 'image/gif', 'image/webp', 'application/pdf',
}

try:
    from google import genai as _genai
    _GEMINI_OK = True
except ImportError:
    _GEMINI_OK = False

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

    # ── OCR ──────────────────────────────────────────────────────────────────
    ocr_result = fields.Text(
        string='Texto extraído (OCR)',
        readonly=True,
        help='Datos extraídos automáticamente del archivo mediante Gemini Vision.')

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

    # ── OCR con Gemini Vision ────────────────────────────────────────────────
    def action_ocr_extract(self):
        """Envía el archivo a Gemini Vision y almacena el texto extraído en ocr_result."""
        self.ensure_one()
        if not self.file:
            raise UserError('Sube un archivo antes de usar la extracción OCR.')

        filename = self.filename or 'documento'
        mime_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'

        if mime_type not in _OCR_SUPPORTED_MIMES:
            raise UserError(
                f'El formato "{mime_type}" no es compatible con OCR. '
                f'Usa imágenes (JPG, PNG, WEBP) o PDF.'
            )

        ICP = self.env['ir.config_parameter'].sudo()
        api_key = ICP.get_param('estate_ai.api_key', '')
        if not api_key:
            raise UserError(
                'No hay API Key de IA configurada. '
                'Ve a Ajustes → Agente IA y configura la clave.'
            )

        # Elige el prompt según la categoría del tipo de documento
        category = self.type_category or 'other'
        prompts = {
            'contract': (
                'Extrae los datos de este contrato en formato JSON con los campos: '
                'tipo_contrato, nombre_propietario, nombre_cliente, fecha_inicio, '
                'fecha_fin, monto, direccion_propiedad, clausulas_importantes.'
            ),
            'identity': (
                'Extrae los datos de este documento de identidad en formato JSON: '
                'nombre_completo, numero_identificacion, fecha_nacimiento, '
                'fecha_emision, fecha_vencimiento, direccion.'
            ),
            'property': (
                'Extrae los datos de este documento de propiedad en formato JSON: '
                'tipo_documento, numero_registro, direccion, propietario, '
                'area_m2, valor_catastral, fecha_registro.'
            ),
            'financial': (
                'Extrae los datos de este documento financiero en formato JSON: '
                'tipo_documento, monto, fecha, banco_o_entidad, '
                'numero_referencia, concepto, nombre_titular.'
            ),
            'legal': (
                'Extrae los datos de este documento legal en formato JSON: '
                'tipo_documento, partes_involucradas, fecha, notaria, '
                'numero_escritura, descripcion_acto.'
            ),
        }
        prompt = prompts.get(category,
            'Analiza este documento inmobiliario y extrae en JSON todos los datos '
            'relevantes que encuentres: nombres, fechas, montos, direcciones, '
            'números de referencia y cualquier información importante.')

        file_b64 = self.file.decode('utf-8') if isinstance(self.file, bytes) else self.file

        extracted_text = ''
        try:
            if not _GEMINI_OK:
                raise UserError(
                    'La librería google-genai no está instalada. '
                    'Ejecuta: pip install google-genai'
                )
            client = _genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[{
                    'parts': [
                        {'inline_data': {'mime_type': mime_type, 'data': file_b64}},
                        {'text': prompt},
                    ]
                }]
            )
            raw = response.text or ''
            # Intenta parsear JSON para mostrarlo formateado
            match = re.search(r'\{[\s\S]*\}', raw)
            if match:
                try:
                    parsed = json.loads(match.group())
                    extracted_text = json.dumps(parsed, ensure_ascii=False, indent=2)
                except json.JSONDecodeError:
                    extracted_text = raw
            else:
                extracted_text = raw
        except UserError:
            raise
        except Exception as e:
            _logger.exception('Error OCR Gemini en documento %s', self.id)
            raise UserError(f'Error al procesar el documento con IA: {e}')

        self.write({'ocr_result': extracted_text})
        self.message_post(
            body=f'🔍 <b>OCR completado con Gemini Vision.</b><br/>'
                 f'<pre style="font-size:12px">{extracted_text[:500]}{"..." if len(extracted_text) > 500 else ""}</pre>'
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'OCR completado',
                'message': 'Datos extraídos del documento correctamente.',
                'type': 'success',
                'sticky': False,
            },
        }


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
