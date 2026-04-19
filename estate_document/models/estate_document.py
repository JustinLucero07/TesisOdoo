import base64

from odoo import models, fields, api
from odoo.exceptions import ValidationError

ALLOWED_EXTENSIONS = ('.pdf', '.doc', '.docx', '.xls', '.xlsx', '.jpg', '.jpeg', '.png', '.gif', '.webp')
MAX_FILE_SIZE_MB = 10


class EstateDocument(models.Model):
    _name = 'estate.document'
    _description = 'Documento Inmobiliario'
    _order = 'date desc, id desc'

    name = fields.Char(string='Nombre del Documento', required=True)
    document_type = fields.Selection([
        ('contract', 'Contrato'),
        ('legal', 'Documento Legal'),
        ('identification', 'Identificación'),
        ('deed', 'Escritura'),
        ('certificate', 'Certificado'),
        ('other', 'Otro'),
    ], string='Tipo de Documento', required=True, default='other')

    property_id = fields.Many2one(
        'estate.property', string='Propiedad')
    partner_id = fields.Many2one(
        'res.partner', string='Cliente / Contacto')
    lead_id = fields.Many2one(
        'crm.lead', string='Oportunidad / Lead')

    file = fields.Binary(string='Archivo', required=True)
    filename = fields.Char(string='Nombre del Archivo')
    file_size = fields.Float(string='Tamaño (MB)', compute='_compute_file_size', store=True)

    date = fields.Date(
        string='Fecha', default=fields.Date.today)
    notes = fields.Text(string='Notas')
    active = fields.Boolean(string='Activo', default=True)

    @api.depends('file')
    def _compute_file_size(self):
        for rec in self:
            if rec.file:
                rec.file_size = round(len(base64.b64decode(rec.file)) / (1024 * 1024), 2)
            else:
                rec.file_size = 0.0

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


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    document_ids = fields.One2many(
        'estate.document', 'lead_id', string='Documentos Inmobiliarios')

class EstateProperty(models.Model):
    _inherit = 'estate.property'

    document_ids = fields.One2many('estate.document', 'property_id', string='Documentos')
    document_count = fields.Integer(compute='_compute_document_count')

    def _compute_document_count(self):
        for rec in self:
            rec.document_count = len(rec.document_ids)

    def action_view_documents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documentos',
            'view_mode': 'list,form',
            'res_model': 'estate.document',
            'domain': [('property_id', '=', self.id)],
            'context': {'default_property_id': self.id},
        }

class ResPartner(models.Model):
    _inherit = 'res.partner'

    document_ids = fields.One2many('estate.document', 'partner_id', string='Documentos Inmobiliarios')
    document_count = fields.Integer(compute='_compute_document_count')

    def _compute_document_count(self):
        for rec in self:
            rec.document_count = len(rec.document_ids)

    def action_view_documents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documentos',
            'view_mode': 'list,form',
            'res_model': 'estate.document',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }
