from odoo import models, fields, api
from odoo.exceptions import UserError


class EstateTenantRequest(models.Model):
    """Solicitudes de mantenimiento y reparación del inquilino."""
    _name = 'estate.tenant.request'
    _description = 'Solicitud de Mantenimiento / Inquilino'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_requested desc, priority desc'

    name = fields.Char(string='Referencia', readonly=True, copy=False, default='Nuevo')
    contract_id = fields.Many2one('estate.contract', string='Contrato', required=True, tracking=True)
    property_id = fields.Many2one(related='contract_id.property_id', string='Propiedad', store=True, readonly=True)
    partner_id = fields.Many2one(related='contract_id.partner_id', string='Inquilino', store=True, readonly=True)
    user_id = fields.Many2one('res.users', string='Asesor Responsable',
                              default=lambda self: self.env.user, tracking=True)

    request_type = fields.Selection([
        ('repair',      'Reparación'),
        ('maintenance', 'Mantenimiento Preventivo'),
        ('emergency',   'Emergencia'),
        ('cleaning',    'Limpieza/Fumigación'),
        ('other',       'Otro'),
    ], string='Tipo de Solicitud', required=True, default='repair', tracking=True)

    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Urgente'),
        ('2', 'Muy Urgente'),
    ], string='Prioridad', default='0')

    description = fields.Text(string='Descripción del Problema', required=True)
    resolution_notes = fields.Text(string='Notas de Resolución')

    date_requested = fields.Date(string='Fecha de Solicitud', default=fields.Date.today, required=True)
    date_scheduled = fields.Date(string='Fecha Programada', tracking=True)
    date_resolved = fields.Date(string='Fecha de Resolución', tracking=True)

    estimated_cost = fields.Float(string='Costo Estimado', tracking=True)
    actual_cost = fields.Float(string='Costo Real', tracking=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    responsible_party = fields.Selection([
        ('owner',  'A cargo del Propietario'),
        ('tenant', 'A cargo del Inquilino'),
        ('agency', 'A cargo de la Agencia'),
    ], string='Responsable del Costo', default='owner', tracking=True)

    state = fields.Selection([
        ('new',         'Nueva'),
        ('in_progress', 'En Proceso'),
        ('resolved',    'Resuelta'),
        ('cancelled',   'Cancelada'),
    ], string='Estado', default='new', tracking=True, required=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code('estate.tenant.request') or 'MANT-001'
        return super().create(vals_list)

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_resolve(self):
        self.write({'state': 'resolved', 'date_resolved': fields.Date.today()})

    def action_cancel(self):
        self.write({'state': 'cancelled'})


class EstateContractDeposit(models.Model):
    """Control del depósito/garantía de un contrato de arriendo."""
    _name = 'estate.contract.deposit'
    _description = 'Depósito / Garantía de Contrato'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'contract_id, id'

    contract_id = fields.Many2one('estate.contract', string='Contrato', required=True, ondelete='cascade')
    property_id = fields.Many2one(related='contract_id.property_id', store=True, readonly=True)
    partner_id = fields.Many2one(related='contract_id.partner_id', string='Inquilino', store=True, readonly=True)

    amount_received = fields.Float(string='Depósito Recibido', required=True, tracking=True)
    date_received = fields.Date(string='Fecha de Recepción', default=fields.Date.today, required=True)

    amount_returned = fields.Float(string='Depósito Devuelto', tracking=True)
    date_returned = fields.Date(string='Fecha de Devolución', tracking=True)
    deductions = fields.Float(string='Deducciones', tracking=True,
                              help='Monto descontado del depósito por daños o pendientes.')
    deduction_reason = fields.Text(string='Motivo de Deducciones')

    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    state = fields.Selection([
        ('held',     'En Custodia'),
        ('returned', 'Devuelto'),
        ('partial',  'Devuelto Parcialmente'),
        ('forfeited','Retenido por Daños'),
    ], string='Estado', default='held', tracking=True)

    balance = fields.Float(string='Saldo Pendiente', compute='_compute_balance', store=True)

    @api.depends('amount_received', 'amount_returned', 'deductions')
    def _compute_balance(self):
        for rec in self:
            rec.balance = rec.amount_received - (rec.amount_returned or 0) - (rec.deductions or 0)

    def action_return_full(self):
        """Devolver depósito completo al inquilino."""
        for rec in self:
            if rec.state != 'held':
                raise UserError('Solo se puede devolver un depósito en custodia.')
            rec.write({
                'state': 'returned',
                'amount_returned': rec.amount_received,
                'date_returned': fields.Date.today(),
            })

    def action_return_partial(self):
        """Devolver depósito parcial (con deducciones ya registradas)."""
        for rec in self:
            if rec.state != 'held':
                raise UserError('Solo se puede devolver un depósito en custodia.')
            if not rec.deductions:
                raise UserError('Registre las deducciones antes de devolver parcialmente.')
            rec.write({
                'state': 'partial',
                'amount_returned': rec.amount_received - rec.deductions,
                'date_returned': fields.Date.today(),
            })

    def action_forfeit(self):
        """Retener depósito completo por daños."""
        for rec in self:
            if rec.state != 'held':
                raise UserError('Solo se puede retener un depósito en custodia.')
            rec.write({
                'state': 'forfeited',
                'deductions': rec.amount_received,
                'date_returned': fields.Date.today(),
            })
