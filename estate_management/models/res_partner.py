from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # --- Campos de rol inmobiliario ---
    is_property_owner = fields.Boolean(
        string='Es Propietario',
        help='Marcar si este contacto es dueño de inmuebles en nuestra cartera.'
    )
    is_allied_agency = fields.Boolean(
        string='Es Agencia Aliada',
        help='Marcar si este contacto es parte de la Red de Aliados (Broker externo / Agencia partner).'
    )
    agency_commission_rate = fields.Float(
        string='% Comisión de Alianza',
        help='Porcentaje pactado para pagos de comisiones a este aliado.'
    )
    allied_specialty = fields.Selection([
        ('luxury',      'Lujo'),
        ('commercial',  'Comercial'),
        ('residential', 'Residencial'),
        ('industrial',  'Industrial'),
    ], string='Especialidad del Aliado')

    # --- Documentos de identidad ---
    id_type = fields.Selection([
        ('cedula',   'Cédula de Identidad'),
        ('ruc',      'RUC'),
        ('passport', 'Pasaporte'),
        ('other',    'Otro'),
    ], string='Tipo de Documento', default='cedula')
    id_number = fields.Char(string='Número de Documento')

    # --- Cuenta bancaria para pagos de arriendo ---
    bank_account_name = fields.Char(string='Titular de la Cuenta')
    bank_account_number = fields.Char(string='Número de Cuenta')
    bank_name = fields.Char(string='Banco')
    bank_account_type = fields.Selection([
        ('checking', 'Cuenta Corriente'),
        ('savings',  'Cuenta de Ahorros'),
    ], string='Tipo de Cuenta', default='savings')

    # --- Preferencias de comunicación ---
    preferred_contact = fields.Selection([
        ('phone',     'Llamada Telefónica'),
        ('whatsapp',  'WhatsApp'),
        ('email',     'Correo Electrónico'),
        ('any',       'Cualquier Canal'),
    ], string='Preferencia de Contacto', default='whatsapp')
    best_contact_time = fields.Selection([
        ('morning',   'Mañana (8h-12h)'),
        ('afternoon', 'Tarde (12h-17h)'),
        ('evening',   'Noche (17h-20h)'),
        ('anytime',   'Cualquier Hora'),
    ], string='Mejor Hora para Contactar', default='anytime')

    # --- Copropietarios ---
    co_owner_ids = fields.Many2many(
        'res.partner',
        'estate_partner_co_owner_rel',
        'partner_id', 'co_owner_id',
        string='Copropietarios',
        help='Otros propietarios que comparten la titularidad de los inmuebles.'
    )
    ownership_percentage = fields.Float(
        string='Porcentaje de Propiedad (%)', default=100.0,
        help='Porcentaje de titularidad de este contacto en los inmuebles compartidos.'
    )

    # --- Contadores computados (smart buttons) ---
    property_owned_count = fields.Integer(
        string='Propiedades (Propietario)',
        compute='_compute_estate_counts',
    )
    property_bought_count = fields.Integer(
        string='Propiedades (Comprador)',
        compute='_compute_estate_counts',
    )
    contract_count = fields.Integer(
        string='Contratos',
        compute='_compute_estate_counts',
    )
    estate_payment_count = fields.Integer(
        string='Pagos',
        compute='_compute_estate_counts',
    )

    def _compute_estate_counts(self):
        Property = self.env['estate.property']
        Contract = self.env['estate.contract']
        Payment  = self.env['estate.payment']
        for partner in self:
            partner.property_owned_count  = Property.search_count([('owner_id',   '=', partner.id)])
            partner.property_bought_count = Property.search_count([('buyer_id',   '=', partner.id)])
            partner.contract_count        = Contract.search_count([('partner_id', '=', partner.id)])
            partner.estate_payment_count  = Payment.search_count( [('partner_id', '=', partner.id)])

    # --- Acciones de smart buttons ---
    def action_view_owned_properties(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Propiedades de {self.name}',
            'res_model': 'estate.property',
            'view_mode': 'list,form',
            'domain': [('owner_id', '=', self.id)],
            'context': {'default_owner_id': self.id},
        }

    def action_view_bought_properties(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Compras de {self.name}',
            'res_model': 'estate.property',
            'view_mode': 'list,form',
            'domain': [('buyer_id', '=', self.id)],
        }

    def action_view_contracts(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Contratos de {self.name}',
            'res_model': 'estate.contract',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }

    def action_view_estate_payments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Pagos de {self.name}',
            'res_model': 'estate.payment',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
        }

    # --- Auto-etiquetado de categorías ---
    def _apply_estate_category(self, xmlid):
        """Agrega una categoría al contacto si no la tiene ya."""
        cat = self.env.ref(xmlid, raise_if_not_found=False)
        if cat:
            for partner in self:
                if cat.id not in partner.category_id.ids:
                    partner.sudo().write({'category_id': [(4, cat.id)]})
