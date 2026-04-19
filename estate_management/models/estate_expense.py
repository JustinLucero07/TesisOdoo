from odoo import models, fields, api


class EstatePropertyExpense(models.Model):
    """Gastos y costos asociados a una propiedad."""
    _name = 'estate.property.expense'
    _description = 'Gasto de Propiedad'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string='Descripción', required=True, tracking=True)
    property_id = fields.Many2one('estate.property', string='Propiedad', required=True, tracking=True)
    contract_id = fields.Many2one('estate.contract', string='Contrato Relacionado',
                                  domain="[('property_id', '=', property_id)]")

    expense_type = fields.Selection([
        ('maintenance',  'Mantenimiento / Reparación'),
        ('marketing',    'Marketing y Publicidad'),
        ('photography',  'Fotografía / Video'),
        ('legal',        'Honorarios Legales / Notariales'),
        ('tax',          'Impuestos / Tasas'),
        ('insurance',    'Seguros'),
        ('utilities',    'Servicios Básicos'),
        ('commission',   'Comisión Pagada a Tercero'),
        ('other',        'Otro'),
    ], string='Categoría', required=True, default='maintenance', tracking=True)

    amount = fields.Float(string='Monto', required=True, tracking=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    date = fields.Date(string='Fecha', default=fields.Date.today, required=True)

    paid_by = fields.Selection([
        ('agency', 'Agencia'),
        ('owner',  'Propietario'),
        ('tenant', 'Inquilino'),
    ], string='Pagado por', default='agency', tracking=True)

    reimbursable = fields.Boolean(string='Reembolsable', default=False,
                                  help='Marcar si este gasto será cobrado al propietario o inquilino.')
    reimbursed = fields.Boolean(string='Reembolsado', default=False, tracking=True)

    invoice_id = fields.Many2one('account.move', string='Factura Vinculada', readonly=True)
    notes = fields.Text(string='Notas')

    state = fields.Selection([
        ('draft',    'Borrador'),
        ('approved', 'Aprobado'),
        ('paid',     'Pagado'),
        ('cancelled','Cancelado'),
    ], string='Estado', default='draft', tracking=True)

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_mark_paid(self):
        self.write({'state': 'paid'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})
