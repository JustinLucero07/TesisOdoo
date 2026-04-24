from odoo import models, fields, api
from odoo.exceptions import UserError


class EstatePropertyOffer(models.Model):
    """Pipeline de ofertas y contraofertas sobre una propiedad."""
    _name = 'estate.property.offer'
    _description = 'Oferta sobre Propiedad'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string='Referencia', readonly=True, copy=False, default='Nuevo')
    property_id = fields.Many2one('estate.property', string='Propiedad', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Comprador/Interesado', required=True, tracking=True)
    lead_id = fields.Many2one('crm.lead', string='Lead de Origen',
                              domain="[('partner_id', '=', partner_id)]")
    user_id = fields.Many2one('res.users', string='Asesor', default=lambda self: self.env.user)

    # Montos
    asking_price = fields.Float(related='property_id.price', string='Precio Solicitado', readonly=True)
    property_bottom_price = fields.Float(related='property_id.bottom_price', string='Precio Mínimo (Tope)', readonly=True)
    offer_amount = fields.Float(string='Monto Ofertado', required=True, tracking=True)
    counteroffer_amount = fields.Float(string='Contraoferta', tracking=True)
    final_agreed_amount = fields.Float(string='Precio Final Acordado', tracking=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    discount_pct = fields.Float(string='Descuento (%)', compute='_compute_discount', store=True)

    date = fields.Date(string='Fecha de Oferta', default=fields.Date.today, required=True)
    date_expiry = fields.Date(string='Válida Hasta', tracking=True)

    financing_type = fields.Selection([
        ('cash',     'Contado'),
        ('mortgage', 'Hipotecario (BIESS/Banco)'),
        ('owner',    'Financiamiento del Vendedor'),
        ('other',    'Otro'),
    ], string='Tipo de Financiamiento', default='cash', tracking=True)

    appraisal_id = fields.Many2one(
        'estate.appraisal',
        string='Tasación Vinculada',
        domain="[('property_id', '=', property_id)]",
        help='Tasación de respaldo para esta oferta.',
    )

    notes = fields.Text(string='Observaciones')

    state = fields.Selection([
        ('draft',       'Borrador'),
        ('submitted',   'Presentada'),
        ('countered',   'Contraoferta Enviada'),
        ('accepted',    'Aceptada'),
        ('rejected',    'Rechazada'),
        ('expired',     'Vencida'),
    ], string='Estado', default='draft', tracking=True, required=True)

    # Related para usar en condiciones de vista sin dotted notation
    offer_type = fields.Selection(
        related='property_id.offer_type', string='Tipo de Oferta', store=True, readonly=True)

    @api.depends('asking_price', 'offer_amount')
    def _compute_discount(self):
        for rec in self:
            if rec.asking_price and rec.asking_price > 0:
                rec.discount_pct = ((rec.asking_price - rec.offer_amount) / rec.asking_price) * 100
            else:
                rec.discount_pct = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code('estate.property.offer') or 'OFERTA-001'
        return super().create(vals_list)

    def _advance_lead_stage(self, xmlid):
        """Avanza el lead vinculado (o el del partner) a la etapa indicada."""
        for rec in self:
            lead = rec.lead_id
            if not lead and rec.partner_id:
                lead = self.env['crm.lead'].sudo().search([
                    ('partner_id', '=', rec.partner_id.id),
                    ('stage_id.is_won', '=', False),
                ], limit=1)
            if lead:
                lead._advance_lead_to_stage(xmlid)

    def action_submit(self):
        self.write({'state': 'submitted'})
        # Auto-avanzar lead a "Oferta Presentada"
        self._advance_lead_stage('estate_crm.stage_lead4_estate_papeles')
        # Notificar al asesor de la propiedad
        for rec in self:
            if rec.property_id.user_id and rec.property_id.user_id != self.env.user:
                rec.property_id.message_post(
                    body=f'Nueva oferta de <b>{rec.partner_id.name}</b> por <b>${rec.offer_amount:,.2f}</b> '
                         f'({rec.discount_pct:.1f}% del precio solicitado).',
                    partner_ids=[rec.property_id.user_id.partner_id.id],
                )

    def action_counteroffer(self):
        self.write({'state': 'countered'})
        # Auto-avanzar lead a "En Negociación"
        self._advance_lead_stage('estate_crm.stage_lead5_estate_avaluo')
        
    def action_simulate_counteroffer(self):
        """Simula una contraoferta basada en el tope mínimo del propietario."""
        for rec in self:
            if rec.state not in ('draft', 'submitted'):
                raise UserError('Solo se puede simular contraofertas en ofertas Nuevas o Presentadas.')
            if not rec.property_bottom_price or rec.property_bottom_price == 0:
                raise UserError('La propiedad no tiene definido un "Precio Tope" (mínimo) para poder simular.')
                
            if rec.offer_amount >= rec.asking_price:
                # Si ofrece igual o más, lo ideal sería aceptar, pero podemos sólo igualarlo
                rec.counteroffer_amount = rec.offer_amount
                rec.message_post(body="La oferta supera o iguala el precio original. Se puede aceptar directamente.")
            elif rec.offer_amount >= rec.property_bottom_price:
                # Si está por encima del tope pero debajo del original, llegamos a un punto medio
                middle = (rec.offer_amount + rec.asking_price) / 2
                rec.counteroffer_amount = middle
                rec.message_post(body=f"La oferta ({rec.offer_amount}) está por encima del tope ({rec.property_bottom_price}). Se sugiere contraofertar un punto medio: {middle}.")
            else:
                # Si está por debajo del tope mínimo
                rec.counteroffer_amount = rec.property_bottom_price
                rec.message_post(body=f"La oferta ({rec.offer_amount}) es MENOR al tope aceptable ({rec.property_bottom_price}). Se sugiere contraofertar al tope mínimo.")

    def action_accept(self):
        self.ensure_one()
        if not self.final_agreed_amount:
            self.final_agreed_amount = self.counteroffer_amount or self.offer_amount
        self.write({'state': 'accepted'})
        # Auto-avanzar lead a "En Negociación" (si aún no está más avanzado)
        self._advance_lead_stage('estate_crm.stage_lead6_estate_minuta')
        # Reservar la propiedad automáticamente
        self.property_id.write({'state': 'reserved', 'buyer_id': self.partner_id.id})
        # Rechazar otras ofertas activas sobre la misma propiedad
        other_offers = self.search([
            ('property_id', '=', self.property_id.id),
            ('id', '!=', self.id),
            ('state', 'in', ('draft', 'submitted', 'countered')),
        ])
        other_offers.write({'state': 'rejected'})
        # Auto-crear contrato y abrir en formulario
        contract = self.action_create_contract()
        return contract

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_create_contract(self):
        """Genera un contrato a partir de la oferta aceptada.
        El tipo de contrato se determina automáticamente según la propiedad.
        """
        self.ensure_one()
        if self.state != 'accepted':
            raise UserError('Solo se puede generar un contrato desde una oferta ACEPTADA.')
        # Si ya existe un contrato vinculado a esta oferta, abrirlo
        existing = self.env['estate.contract'].search([('offer_id', '=', self.id)], limit=1)
        if existing:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Contrato Existente',
                'res_model': 'estate.contract',
                'view_mode': 'form',
                'res_id': existing.id,
            }
        # Tipo de contrato según tipo de propiedad (venta/arriendo)
        contract_type = 'rent' if self.property_id.offer_type == 'rent' else 'sale'
        contract = self.env['estate.contract'].create({
            'property_id': self.property_id.id,
            'partner_id': self.partner_id.id,
            'user_id': self.user_id.id,
            'offer_id': self.id,
            'contract_type': contract_type,
            'amount': self.final_agreed_amount or self.offer_amount,
            'date_start': fields.Date.today(),
        })
        # Notificar en chatter de la oferta, propiedad y lead
        self.message_post(body=f'📄 Contrato <b>{contract.name}</b> generado desde esta oferta.')
        self.property_id.message_post(
            body=f'📄 Contrato <b>{contract.name}</b> creado para <b>{self.partner_id.name}</b> '
                 f'(Oferta: {self.name}, Monto: ${contract.amount:,.2f}).')
        if self.lead_id:
            self.lead_id.message_post(
                body=f'📄 Contrato <b>{contract.name}</b> generado para la propiedad '
                     f'<b>{self.property_id.title}</b>.')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Contrato Generado',
            'res_model': 'estate.contract',
            'view_mode': 'form',
            'res_id': contract.id,
        }

    def action_create_sale_order(self):
        """Genera una Orden de Venta (Odoo nativo) desde la oferta aceptada.
        Solo aplica para propiedades en VENTA. Vincula automáticamente al lead de origen.
        """
        self.ensure_one()
        if self.state != 'accepted':
            raise UserError('Solo se puede crear una orden desde una oferta ACEPTADA.')
        if self.property_id.offer_type != 'sale':
            raise UserError('Las órdenes de venta son para propiedades en VENTA. Use "Generar Contrato" para arriendos.')

        order_vals = {
            'partner_id': self.partner_id.id,
            'property_id': self.property_id.id,
            'estate_transaction_type': 'sale',
            'lead_id': self.lead_id.id if self.lead_id else False,
        }
        if self.property_id.product_id:
            order_vals['order_line'] = [(0, 0, {
                'product_id': self.property_id.product_id.id,
                'name': self.property_id.title,
                'price_unit': self.final_agreed_amount or self.offer_amount,
                'product_uom_qty': 1,
            })]
        order = self.env['sale.order'].create(order_vals)
        # Notificar en chatter de la oferta, propiedad y lead de origen
        self.message_post(body=f'🛒 Orden de venta <b>{order.name}</b> creada desde esta oferta.')
        self.property_id.message_post(
            body=f'🛒 Orden de venta <b>{order.name}</b> creada para <b>{self.partner_id.name}</b> '
                 f'desde oferta <b>{self.name}</b> por ${self.final_agreed_amount or self.offer_amount:,.2f}.')
        if self.lead_id:
            self.lead_id.message_post(
                body=f'🛒 Orden de venta <b>{order.name}</b> generada para la propiedad '
                     f'<b>{self.property_id.title}</b>.')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Orden de Venta',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': order.id,
        }
