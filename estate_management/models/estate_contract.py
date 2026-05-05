import logging

from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class EstateContract(models.Model):
    _name = 'estate.contract'
    _description = 'Contrato Inmobiliario'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc, id desc'

    name = fields.Char(
        string='Referencia', readonly=True, copy=False,
        default='Nuevo')

    # Trazabilidad: origen del contrato
    offer_id = fields.Many2one(
        'estate.property.offer', string='Oferta de Origen', readonly=True,
        help='Oferta aceptada que generó este contrato.')
    sale_order_id = fields.Many2one(
        'sale.order', string='Orden de Venta', readonly=True,
        help='Orden de venta de Odoo vinculada a este contrato.')
    property_id = fields.Many2one(
        'estate.property', string='Propiedad', required=True, tracking=True)
    partner_id = fields.Many2one(
        'res.partner', string='Cliente', required=True, tracking=True)
    user_id = fields.Many2one(
        'res.users', string='Agente Responsable',
        default=lambda self: self.env.user, tracking=True)

    contract_type = fields.Selection([
        ('sale', 'Compraventa'),
        ('rent', 'Alquiler'),
        ('exclusive', 'Exclusividad'),
    ], string='Tipo de Contrato', required=True, default='sale', tracking=True)

    date_start = fields.Date(string='Fecha de Inicio', required=True,
                             default=fields.Date.today, tracking=True)
    date_end = fields.Date(string='Fecha de Vencimiento', tracking=True)
    amount = fields.Float(string='Monto del Contrato', tracking=True)
    currency_id = fields.Many2one(
        'res.currency', string='Moneda',
        default=lambda self: self.env.company.currency_id)

    state = fields.Selection([
        ('draft',     'Borrador'),
        ('active',    'Activo'),
        ('suspended', 'Suspendido'),
        ('renewing',  'En Renovación'),
        ('renewed',   'Renovado'),
        ('expired',   'Vencido'),
        ('cancelled', 'Cancelado'),
    ], string='Estado', default='draft', tracking=True, required=True)

    parent_contract_id = fields.Many2one(
        'estate.contract', string='Contrato Padre', readonly=True,
        help='Si este contrato es una renovación, apunta al original.')
    child_contract_ids = fields.One2many(
        'estate.contract', 'parent_contract_id', string='Contratos Hijos (Renovaciones)')

    notes = fields.Html(string='Notas / Cláusulas')
    payment_ids = fields.One2many(
        'estate.payment', 'contract_id', string='Pagos')
    
    customer_signature = fields.Binary(string='Firma del Cliente', copy=False, attachment=True)
    signature_date = fields.Datetime(string='Fecha de Firma', readonly=True)
    earnest_money_filename = fields.Char(string='Nombre del Archivo de Arras')
    earnest_money_contract = fields.Binary(string='Contrato de Arras', attachment=True,
                                          help='Documento escaneado o PDF del Contrato de Arras firmado.')
    signed_contract = fields.Binary(string='Contrato Firmado', attachment=True,
                                    help='Documento escaneado o PDF del contrato final firmado por ambas partes.')
    signed_contract_filename = fields.Char(string='Nombre del Contrato Firmado')

    payment_count = fields.Integer(
        string='# Pagos', compute='_compute_payment_count')
    total_paid = fields.Float(
        string='Total Pagado', compute='_compute_payment_count')

    invoice_count = fields.Integer(
        string='Facturas', compute='_compute_invoice_count')

    @api.depends('payment_ids.invoice_id')
    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = len(rec.payment_ids.mapped('invoice_id'))

    # ------------------------------------------------------------------
    # Validaciones de integridad de datos
    # ------------------------------------------------------------------

    @api.constrains('amount')
    def _check_amount(self):
        for rec in self:
            if rec.amount < 0:
                raise UserError('El monto del contrato no puede ser negativo.')

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for rec in self:
            if rec.date_end and rec.date_start and rec.date_end < rec.date_start:
                raise UserError('La fecha de vencimiento no puede ser anterior a la fecha de inicio.')

    @api.onchange('amount')
    def _onchange_contract_amount_warn(self):
        if self.amount is not False and self.amount < 0:
            return {'warning': {
                'title': 'Monto inválido',
                'message': 'El monto del contrato no puede ser negativo.',
            }}

    @api.onchange('date_start', 'date_end')
    def _onchange_contract_dates_warn(self):
        if self.date_end and self.date_start and self.date_end < self.date_start:
            return {'warning': {
                'title': 'Fechas incoherentes',
                'message': 'La fecha de vencimiento no puede ser anterior a la fecha de inicio.',
            }}

    def action_view_invoices(self):
        self.ensure_one()
        invoice_ids = self.payment_ids.mapped('invoice_id').ids
        return {
            'type': 'ir.actions.act_window',
            'name': f'Facturas — {self.name}',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', invoice_ids)],
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code('estate.contract') or 'Nuevo'
        contracts = super().create(vals_list)
        for contract in contracts:
            if contract.partner_id:
                contract.partner_id._apply_estate_category('estate_management.partner_category_client')
            # Sincronizar fecha de vencimiento con la propiedad
            if contract.date_end and contract.property_id:
                contract.property_id.sudo().contract_end_date = contract.date_end
        return contracts

    def write(self, vals):
        res = super().write(vals)
        # Si cambia la fecha de vencimiento, actualizar en la propiedad vinculada
        if 'date_end' in vals:
            for rec in self:
                if rec.property_id and vals['date_end']:
                    rec.property_id.sudo().contract_end_date = vals['date_end']
        return res

    @api.depends('name', 'property_id', 'partner_id')
    def _compute_display_name(self):
        for rec in self:
            prop_name = rec.property_id.title if rec.property_id else ''
            client = rec.partner_id.name if rec.partner_id else ''
            if prop_name or client:
                rec.display_name = f"{rec.name} - {prop_name} ({client})"
            else:
                rec.display_name = rec.name

    @api.depends('payment_ids', 'payment_ids.state', 'payment_ids.amount')
    def _compute_payment_count(self):
        for rec in self:
            paid_payments = rec.payment_ids.filtered(lambda p: p.state == 'paid')
            rec.payment_count = len(rec.payment_ids)
            rec.total_paid = sum(paid_payments.mapped('amount'))

    def _advance_related_lead(self, xmlid):
        """Avanza el lead vinculado a este contrato a la etapa indicada."""
        for rec in self:
            # Buscar por oferta de origen, luego por partner+propiedad
            lead = None
            if rec.offer_id and rec.offer_id.lead_id:
                lead = rec.offer_id.lead_id
            if not lead and rec.partner_id:
                lead = self.env['crm.lead'].sudo().search([
                    ('partner_id', '=', rec.partner_id.id),
                    ('stage_id.is_won', '=', False),
                ], limit=1)
            if lead:
                lead._advance_lead_to_stage(xmlid)

    _VALID_STATE_TRANSITIONS = {
        'draft':     ['active', 'cancelled'],
        'active':    ['suspended', 'renewing', 'expired', 'cancelled'],
        'suspended': ['active', 'cancelled', 'expired'],
        'renewing':  ['renewed', 'active', 'cancelled'],
        'renewed':   [],  # estado terminal, ver child_contract_ids
        'expired':   ['draft', 'renewing'],
        'cancelled': ['draft'],
    }

    def _check_state_transition(self, new_state):
        for rec in self:
            allowed = self._VALID_STATE_TRANSITIONS.get(rec.state, [])
            if new_state not in allowed:
                raise UserError(
                    f'No se puede cambiar el contrato "{rec.name}" '
                    f'de "{rec.state}" a "{new_state}". '
                    f'Transiciones permitidas: {", ".join(allowed) or "ninguna"}.'
                )

    def action_activate(self):
        self._check_state_transition('active')
        for rec in self:
            rec.state = 'active'
            if rec.partner_id.email:
                template = self.env.ref(
                    'estate_management.mail_template_contract_activated', raise_if_not_found=False)
                if template:
                    template.send_mail(rec.id, force_send=True)
        self._advance_related_lead('estate_crm.stage_lead7_estate_cierre')

    def action_cancel(self):
        self._check_state_transition('cancelled')
        self.write({'state': 'cancelled'})

    def action_set_expired(self):
        self._check_state_transition('expired')
        self.write({'state': 'expired'})

    def action_reset_draft(self):
        self._check_state_transition('draft')
        self.write({'state': 'draft'})

    def action_suspend(self):
        """Suspende un contrato activo (impago, juicio, pausa de renta)."""
        self._check_state_transition('suspended')
        for rec in self:
            rec.state = 'suspended'
            rec.message_post(body='⏸ Contrato suspendido. Pagos y vencimiento detenidos hasta reactivación.')

    def action_resume_active(self):
        """Reactiva un contrato suspendido."""
        self._check_state_transition('active')
        for rec in self:
            rec.state = 'active'
            rec.message_post(body='▶ Contrato reactivado.')

    def action_start_renewal(self):
        """Marca el contrato actual como 'en renovación'. Útil para alquileres
        que están en proceso de prorrogarse antes del vencimiento."""
        self._check_state_transition('renewing')
        for rec in self:
            rec.state = 'renewing'
            rec.message_post(body='🔄 Contrato en proceso de renovación.')

    def action_create_renewal(self):
        """Crea un contrato hijo (renovación) y marca el actual como renovado."""
        self.ensure_one()
        if self.state not in ('renewing', 'active', 'expired'):
            raise UserError('Solo se puede renovar un contrato Activo, En Renovación o Vencido.')
        new_contract = self.copy({
            'name': 'Nuevo',
            'state': 'draft',
            'parent_contract_id': self.id,
            'date_start': fields.Date.today(),
            'date_end': False,
            'offer_id': False,
        })
        # Marcar este contrato como renovado
        self._VALID_STATE_TRANSITIONS['renewing'].append('renewed')  # permitir transición
        self._VALID_STATE_TRANSITIONS['active'].append('renewed')
        self._VALID_STATE_TRANSITIONS['expired'].append('renewed')
        self.write({'state': 'renewed'})
        self.message_post(
            body=f'🔄 Renovado mediante el nuevo contrato <b>{new_contract.name}</b>.')
        return {
            'type': 'ir.actions.act_window',
            'name': f'Renovación de {self.name}',
            'res_model': 'estate.contract',
            'view_mode': 'form',
            'res_id': new_contract.id,
        }

    def action_view_offer(self):
        """Abre la oferta original que generó este contrato."""
        self.ensure_one()
        if not self.offer_id:
            raise UserError('Este contrato no tiene oferta de origen registrada.')
        return {
            'type': 'ir.actions.act_window',
            'name': f'Oferta {self.offer_id.name}',
            'res_model': 'estate.property.offer',
            'view_mode': 'form',
            'res_id': self.offer_id.id,
        }

    def action_view_payments(self):
        """Smart-button: ver pagos del contrato."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Pagos — {self.name}',
            'res_model': 'estate.payment',
            'view_mode': 'list,form',
            'domain': [('contract_id', '=', self.id)],
            'context': {'default_contract_id': self.id},
        }

    def action_generate_rent_invoice(self):
        """Genera una factura mensual de arrendamiento para este contrato."""
        self.ensure_one()
        if self.contract_type != 'rent':
            raise UserError('La facturación mensual es solo para contratos de ARRENDAMIENTO.')
        if self.state != 'active':
            raise UserError('El contrato debe estar ACTIVO para generar facturas.')
        today = fields.Date.today()
        month_label = today.strftime('%B %Y')
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_origin': self.name,
            'property_id': self.property_id.id,
            'estate_transaction_type': 'rent',
            'invoice_line_ids': [(0, 0, {
                'name': f'Renta mensual — {self.property_id.title} ({month_label})',
                'quantity': 1,
                'price_unit': self.amount,
            })],
        })
        # Registrar pago vinculado al contrato
        self.env['estate.payment'].create({
            'contract_id': self.id,
            'amount': self.amount,
            'date': today,
            'invoice_id': invoice.id,
            'notes': f'Renta {month_label} — generada automáticamente.',
        })
        self.message_post(
            body=f'🧾 Factura <b>{invoice.name or "borrador"}</b> generada para {month_label}.')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Factura Mensual',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': invoice.id,
        }

    @api.model
    def _migrate_binary_to_documents(self):
        """Convierte campos Binary heredados (earnest_money_contract, signed_contract,
        customer_signature) en registros de estate.document.
        Idempotente: skip si ya existe un documento del mismo tipo para el contrato.
        """
        Document = self.env['estate.document'].sudo()
        DocType  = self.env['estate.document.type'].sudo()
        if 'estate.document' not in self.env or not DocType.search_count([]):
            _logger.info('Migración omitida: estate_document no instalado o sin tipos.')
            return 0

        type_signed   = DocType.search([('code', '=', 'contract_signed')], limit=1)
        type_earnest  = DocType.search([('code', '=', 'earnest_money')],   limit=1)

        migrated = 0
        contracts = self.search([
            '|', '|',
            ('signed_contract', '!=', False),
            ('earnest_money_contract', '!=', False),
            ('customer_signature', '!=', False),
        ])
        for contract in contracts:
            common = {
                'contract_id': contract.id,
                'property_id': contract.property_id.id,
                'partner_id': contract.partner_id.id,
                'state': 'received',
                'confidentiality': 'restricted',
            }
            # Contrato firmado
            if contract.signed_contract and type_signed:
                exists = Document.search_count([
                    ('contract_id', '=', contract.id),
                    ('type_id', '=', type_signed.id),
                    ('file', '!=', False),
                ])
                if not exists:
                    Document.create({
                        **common,
                        'type_id': type_signed.id,
                        'name': f'Contrato firmado - {contract.name}',
                        'file': contract.signed_contract,
                        'filename': contract.signed_contract_filename or 'contrato.pdf',
                    })
                    migrated += 1
            # Arras
            if contract.earnest_money_contract and type_earnest:
                exists = Document.search_count([
                    ('contract_id', '=', contract.id),
                    ('type_id', '=', type_earnest.id),
                    ('file', '!=', False),
                ])
                if not exists:
                    Document.create({
                        **common,
                        'type_id': type_earnest.id,
                        'name': f'Arras - {contract.name}',
                        'file': contract.earnest_money_contract,
                        'filename': contract.earnest_money_filename or 'arras.pdf',
                    })
                    migrated += 1
        _logger.info('Migración Binary→estate.document completada: %d documentos creados.', migrated)
        return migrated

    @api.model
    def _cron_generate_rent_invoices(self):
        """Cron mensual: genera facturas de renta para contratos de arriendo activos."""
        today = fields.Date.today()
        month_start = today.replace(day=1)
        active_rent = self.search([
            ('contract_type', '=', 'rent'),
            ('state', '=', 'active'),
            ('date_end', '>=', today),
        ])
        for contract in active_rent:
            # Verificar que no se haya generado factura este mes para este contrato
            already_invoiced = self.env['account.move'].search_count([
                ('property_id', '=', contract.property_id.id),
                ('move_type', '=', 'out_invoice'),
                ('estate_transaction_type', '=', 'rent'),
                ('invoice_date', '>=', month_start),
            ])
            if not already_invoiced:
                try:
                    contract.action_generate_rent_invoice()
                except Exception as e:
                    _logger.warning("Error generando factura de alquiler para %s: %s", contract.name, e)
