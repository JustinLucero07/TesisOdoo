from markupsafe import Markup

from odoo import models, fields, api
from odoo.tools.misc import clean_context
from odoo.exceptions import UserError, ValidationError

from ..tools.invoice_modes import (
    INVOICE_MODES, find_tax, is_invoiced, payment_journal, vat_amount)

# Los pasos del negocio que pueden cobrar comisión. Se definen aquí porque los
# usan tanto la comisión como sus líneas de reparto.
EstateCommissionSplit_ROLES = [
    ('capture', 'Captación'),
    ('reception', 'Recepción'),
    ('visit', 'Visita'),
    ('closing', 'Cierre'),
    ('all', 'Todos los pasos'),
    ('other', 'Otro'),
]


class EstateCommission(models.Model):
    _name = 'estate.commission'
    _description = 'Comisión Inmobiliaria'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, parent_commission_id, role_sequence, id desc'

    name = fields.Char(string='Referencia', required=True, copy=False, readonly=True, default='NUEVO')
    lead_id = fields.Many2one(
        'crm.lead', string='Oportunidad (CRM)', tracking=True,
        help='Oportunidad o Lead del CRM de donde proviene esta comisión.')
    property_id = fields.Many2one('estate.property', string='Propiedad', required=False)
    user_id = fields.Many2one('res.users', string='Asesor', required=True, default=lambda self: self.env.user)

    sale_amount = fields.Float(string='Monto de la Venta/Renta',
                               help='Valor total de la transacción que genera esta comisión.')
    commission_pct = fields.Float(string='Porcentaje de Comisión (%)', default=5.0,
                                  help='Porcentaje aplicado sobre el monto de la venta.')
    amount = fields.Float(string='Monto de Comisión', required=True,
                          compute='_compute_commission_amount', store=True, readonly=False)
    company_currency = fields.Many2one(
        'res.currency', string='Moneda',
        default=lambda self: self.env.company.currency_id)
    date = fields.Date(string='Fecha', default=fields.Date.context_today)

    type = fields.Selection([
        ('sale', 'Venta'),
        ('rent', 'Arrendamiento (1er mes)'),
        ('bonus', 'Bono/Premio')
    ], string='Tipo de Comisión', required=True, default='sale')

    role = fields.Selection(
        EstateCommissionSplit_ROLES, string='Rol en el negocio', tracking=True,
        help='Por qué paso del negocio se le paga a este asesor.')
    role_pct = fields.Float(
        string='% de los honorarios', tracking=True,
        help='Porcentaje de los honorarios de la agencia que corresponde a este rol.')

    role_sequence = fields.Integer(
        compute='_compute_role_sequence', store=True,
        help='Orden del rol dentro del negocio, para listarlos como ocurren.')
    deal_total_amount = fields.Monetary(
        string='Comisión total del negocio', compute='_compute_deal_total',
        store=True, currency_field='company_currency',
        help='Honorarios completos de esta propiedad. El monto de cada asesor es '
             'su porcentaje sobre este total.')

    parent_commission_id = fields.Many2one(
        'estate.commission', string='Comisión repartida', index=True,
        ondelete='cascade', copy=False,
        help='Comisión total del negocio de la que salió esta parte.')
    child_commission_ids = fields.One2many(
        'estate.commission', 'parent_commission_id', string='Comisiones por asesor')
    child_count = fields.Integer(compute='_compute_split_totals', store=True)

    # --- Reparto entre los asesores que participaron ---
    split_line_ids = fields.One2many(
        'estate.commission.split', 'commission_id', string='Reparto entre asesores')
    split_count = fields.Integer(compute='_compute_split_totals', store=True)
    amount_assigned = fields.Monetary(
        string='Repartido a asesores', compute='_compute_split_totals', store=True,
        currency_field='company_currency')
    amount_office = fields.Monetary(
        string='Queda en la oficina', compute='_compute_split_totals', store=True,
        currency_field='company_currency',
        help='Honorarios menos lo repartido a los asesores. Solo tiene sentido en '
             'el total del negocio: en la comisión de un asesor es cero.')
    is_deal_total = fields.Boolean(
        string='Es el total del negocio', compute='_compute_split_totals', store=True,
        help='Marca la comisión que representa los honorarios completos, para no '
             'sumar dos veces al analizar las ganancias.')
    pct_assigned = fields.Float(
        string='% repartido', compute='_compute_split_totals', store=True)
    is_exclusive = fields.Boolean(
        string='Captación en exclusividad', related='property_id.is_exclusive',
        readonly=True)

    _ROLE_ORDER = {'capture': 1, 'reception': 2, 'visit': 3, 'closing': 4,
                   'all': 5, 'other': 9}

    @api.depends('role')
    def _compute_role_sequence(self):
        for rec in self:
            rec.role_sequence = self._ROLE_ORDER.get(rec.role, 0)

    @api.depends('amount', 'parent_commission_id.amount')
    def _compute_deal_total(self):
        for rec in self:
            rec.deal_total_amount = (rec.parent_commission_id.amount
                                     if rec.parent_commission_id else rec.amount)

    @api.depends('split_line_ids.amount', 'split_line_ids.percentage', 'amount',
                 'child_commission_ids.amount', 'parent_commission_id')
    def _compute_split_totals(self):
        for rec in self:
            rec.split_count = len(rec.split_line_ids)
            rec.child_count = len(rec.child_commission_ids)
            # Una vez generadas las comisiones por asesor, mandan ellas.
            if rec.child_commission_ids:
                rec.amount_assigned = sum(rec.child_commission_ids.mapped('amount'))
                rec.pct_assigned = sum(rec.child_commission_ids.mapped('role_pct'))
            else:
                rec.amount_assigned = sum(rec.split_line_ids.mapped('amount'))
                rec.pct_assigned = sum(rec.split_line_ids.mapped('percentage'))
            # La oficina solo gana en el total del negocio. En la comisión de un
            # asesor no queda nada, y en una comisión suelta (las de antes del
            # reparto por roles) se le pagó todo al asesor.
            if rec.parent_commission_id:
                rec.amount_office = 0.0
                rec.is_deal_total = False
            elif rec.child_commission_ids or rec.split_line_ids:
                rec.amount_office = (rec.amount or 0.0) - rec.amount_assigned
                rec.is_deal_total = True
            else:
                rec.amount_office = 0.0
                rec.is_deal_total = True

    def _guess_split_users(self):
        """Quién hizo cada paso, con lo que el sistema ya sabe del negocio.

        Captación: el captador de la propiedad. Recepción: el asesor del lead.
        Visita: quien hizo la última visita realizada con ese cliente a esta
        propiedad. Cierre: el asesor responsable de la venta. Todo se puede
        corregir en el reparto antes de pagar.
        """
        self.ensure_one()
        prop = self.property_id
        lead = self.lead_id
        Users = self.env['res.users']
        capture = prop.exclusive_user_id or prop.user_id or self.user_id
        reception = lead.user_id if lead else Users
        visit = Users
        Event = self.env['calendar.event']
        if prop and {'property_id', 'visit_state', 'appointment_type'} <= set(Event._fields):
            domain = [('property_id', '=', prop.id), ('appointment_type', '=', 'visit'),
                      ('visit_state', '=', 'done')]
            client = (lead.partner_id if lead else False) or prop.buyer_id
            if lead and 'lead_id' in Event._fields:
                visits = Event.sudo().search(domain + [('lead_id', '=', lead.id)],
                                             order='start desc', limit=1)
            else:
                visits = Event
            if not visits and client and 'client_id' in Event._fields:
                visits = Event.sudo().search(domain + [('client_id', '=', client.id)],
                                             order='start desc', limit=1)
            visit = visits.user_id
        closing = prop.user_id or self.user_id
        return {'capture': capture, 'reception': reception or closing,
                'visit': visit or reception or closing, 'closing': closing}

    def _default_split_values(self):
        """Los cuatro pasos del negocio con los porcentajes configurados y el
        asesor que probablemente hizo cada uno (se puede cambiar)."""
        self.ensure_one()
        company = self.env.company
        pct_captacion = (company.estate_pct_capture_exclusive
                         if self.property_id.is_exclusive
                         else company.estate_pct_capture)
        users = self._guess_split_users()
        pcts = {'capture': pct_captacion, 'reception': company.estate_pct_reception,
                'visit': company.estate_pct_visit, 'closing': company.estate_pct_closing}
        return [
            {'sequence': seq, 'role': role, 'percentage': pcts[role],
             'user_id': users[role].id if users[role] else False}
            for seq, role in ((10, 'capture'), (20, 'reception'), (30, 'visit'), (40, 'closing'))
        ]

    def action_generate_split(self):
        """Rellena el reparto con los cuatro roles y sus porcentajes."""
        # Un "default_amount" de la pantalla anterior se colaba en cada línea
        # y le ponía el monto completo en vez de su porcentaje.
        self = self.with_context(clean_context(self.env.context))
        for rec in self:
            if rec.split_line_ids:
                raise UserError(
                    'Esta comisión ya tiene un reparto. Borra las líneas si '
                    'quieres volver a generarlo.')
            rec.split_line_ids = [(0, 0, vals) for vals in rec._default_split_values()]
        return True

    def action_split_into_commissions(self):
        """Convierte el reparto en una comisión por asesor, pagable por separado.

        Cada línea con asesor se vuelve su propia comisión aprobada, así el pago
        y la factura de cada uno siguen el mismo circuito de siempre. Esta queda
        como el total del negocio, marcada como Repartida.
        """
        self.ensure_one()
        self = self.with_context(clean_context(self.env.context))
        if self.state == 'paid':
            raise UserError('Esta comisión ya está pagada; no se puede repartir.')
        if self.child_commission_ids:
            raise UserError(
                'Esta comisión ya fue repartida. Revisa las comisiones por asesor.')
        lineas = self.split_line_ids.filtered(lambda l: l.user_id and l.amount > 0)
        if not lineas:
            raise UserError(
                'Asigna al menos un asesor con monto en el reparto antes de generarlo.')
        # "Guardar reparto (sin pagar)" solo registra quién hizo cada paso.
        cobrada = (self.client_collection_state != 'pending'
                   and not self.env.context.get('estate_split_only'))
        if cobrada and not self.payment_method:
            raise UserError(
                'Indica la Forma de Pago en "Pago al Asesor (Constancia)": al '
                'generar el reparto se paga y factura a cada asesor.')

        etiquetas = dict(EstateCommissionSplit_ROLES)
        creadas = self.env['estate.commission']
        for linea in lineas:
            creadas |= self.create({
                'property_id': self.property_id.id,
                'lead_id': self.lead_id.id,
                'user_id': linea.user_id.id,
                'sale_amount': self.sale_amount,
                'commission_pct': self.commission_pct * ((linea.percentage or 0.0) / 100.0),
                'amount': linea.amount,
                'role': linea.role,
                'role_pct': linea.percentage,
                'type': self.type,
                'date': self.date,
                'state': 'approved',
                'parent_commission_id': self.id,
            })
        self.state = 'split'
        detalle = ' · '.join(
            '%s: %s ${:,.2f}'.format(l.amount) % (etiquetas.get(l.role, l.role), l.user_id.name)
            for l in lineas)
        self.message_post(body=(
            '<b>Comisión repartida</b> en %d parte(s) — %s · Oficina ${:,.2f}'
            .format(self.amount_office) % (len(lineas), detalle)))

        if not cobrada:
            # Queda el reparto hecho; el pago se hace después con "Pagar pendientes".
            motivo = ('el propietario todavía no ha pagado la comisión'
                      if self.client_collection_state == 'pending'
                      else 'se pagará más tarde')
            self.message_post(body=(
                'Reparto guardado <b>sin pagar</b>: %s. Para pagar a los asesores usa '
                '"Pagar pendientes".' % motivo))
            return self.action_view_children()

        # Repartir y pagar es un solo paso: no tiene sentido entrar a cada
        # comisión a repetir la misma forma de pago.
        self.action_pay_all_children()
        return self.action_view_children()

    def action_pay_all_children(self):
        """Paga de una sola vez a todos los asesores del reparto.

        Cada uno recibe su propia factura de proveedor, igual que si se pagaran
        uno por uno; esto solo evita entrar cuatro veces. Las que ya estaban
        pagadas se saltan.
        """
        self.ensure_one()
        if self.state != 'split':
            raise UserError('Esta comisión no está repartida entre asesores.')
        self._check_client_collected()
        if not self.payment_method:
            raise UserError(
                'Indica la Forma de Pago en "Pago al Asesor (Constancia)" antes '
                'de pagar a todos.')
        pendientes = self.child_commission_ids.filtered(
            lambda c: c.state in ('draft', 'approved'))
        if not pendientes:
            raise UserError('Todas las comisiones de este reparto ya están pagadas.')

        fecha = self.payment_date or fields.Date.context_today(self)
        for hija in pendientes:
            hija.write({
                'payment_method': self.payment_method,
                'payment_date': hija.payment_date or fecha,
                'payment_reference': hija.payment_reference or self.payment_reference,
            })
            hija.action_register_payment()

        total = sum(pendientes.mapped('amount'))
        self.message_post(body=(
            '<b>Pagadas %d comisiones</b> por un total de $%s. '
            'Cada asesor tiene su propia factura de proveedor.'
            % (len(pendientes), '{:,.2f}'.format(total))))
        return self.action_view_children()

    def action_open_payout_wizard(self):
        """Antes de pagar pide cómo se pagó (efectivo, transferencia…)."""
        self.ensure_one()
        if self.state in ('paid', 'cancelled'):
            raise UserError('Esta comisión ya está pagada o cancelada.')
        self._check_client_collected()
        if self.state == 'split':
            mode = 'pending'
        elif self.parent_commission_id:
            mode = 'single'
        else:
            mode = 'split'
        return {
            'type': 'ir.actions.act_window',
            'name': 'Pagar a los asesores',
            'res_model': 'estate.commission.payout.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_commission_id': self.id, 'default_mode': mode},
        }

    def action_view_children(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Comisiones por asesor',
            'res_model': 'estate.commission',
            'view_mode': 'list,form',
            'domain': [('parent_commission_id', '=', self.id)],
        }

    def action_undo_split(self):
        """Deshace el reparto, incluso si ya se pagó.

        Como generar el reparto paga de inmediato, un asesor mal asignado se
        descubre cuando el pago ya está hecho. Se anula la factura de cada
        comisión pagada y se borran todas para volver a empezar. El pago
        contable queda como movimiento suelto y hay que conciliarlo a mano.
        """
        self.ensure_one()
        if self.state != 'split':
            raise UserError('Esta comisión no está repartida.')

        anuladas = []
        for hija in self.child_commission_ids:
            factura = hija.invoice_id
            if factura and factura.state != 'cancel':
                try:
                    if factura.state == 'posted':
                        factura.button_draft()
                    factura.button_cancel()
                    anuladas.append(factura.name)
                except Exception as e:
                    raise UserError(
                        'No se pudo anular la factura %s de %s: %s\n\n'
                        'Anúlala a mano desde Facturación y vuelve a intentarlo.'
                        % (factura.name, hija.user_id.name, e)) from None

        self.child_commission_ids.unlink()
        self.state = 'approved'
        detalle = (' Facturas anuladas: %s. El pago contable queda suelto y debe '
                   'conciliarse o revertirse a mano.' % ', '.join(anuladas)
                   if anuladas else '')
        self.message_post(body='<b>Reparto deshecho</b> por %s.%s'
                               % (self.env.user.name, detalle))
        return True

    @api.constrains('split_line_ids', 'amount')
    def _check_split_not_over(self):
        for rec in self:
            if not rec.split_line_ids:
                continue
            # Se compara con una holgura de un centavo por el redondeo.
            if rec.amount_assigned > (rec.amount or 0.0) + 0.01:
                raise ValidationError(
                    'El reparto (%.2f) supera el monto de la comisión (%.2f). '
                    'Ajusta los porcentajes o los montos.'
                    % (rec.amount_assigned, rec.amount or 0.0))

    @api.depends('sale_amount', 'commission_pct')
    def _compute_commission_amount(self):
        for rec in self:
            # Siempre hay que asignar: el campo es obligatorio y almacenado, y
            # dejarlo sin valor rompía la creación por código con NOT NULL.
            if rec.sale_amount and rec.commission_pct:
                rec.amount = rec.sale_amount * (rec.commission_pct / 100.0)
            elif not rec.amount:
                rec.amount = 0.0

    @api.onchange('lead_id')
    def _onchange_lead_id_autofill(self):
        """Al seleccionar una oportunidad/lead del CRM, autocompleta la propiedad,
        el asesor, el tipo de comisión, el monto de la venta/renta y el porcentaje."""
        if not self.lead_id:
            return
        lead = self.lead_id
        if lead.target_property_id:
            self.property_id = lead.target_property_id
            prop = lead.target_property_id
            self.type = 'rent' if prop.offer_type == 'rent' else 'sale'
            if self.type == 'rent':
                self.sale_amount = lead.client_budget or prop.rental_price or prop.price or 0.0
            else:
                self.sale_amount = lead.client_budget or prop.price or 0.0
            if prop.commission_percentage:
                pct = prop.commission_percentage
                if prop.is_allied_property:
                    allied_ratio = (prop.allied_split_pct or 50.0) / 100.0
                    pct = pct * allied_ratio
                if prop.co_user_id and lead.user_id == prop.co_user_id and 0 < prop.commission_split_pct < 100:
                    pct = pct * (prop.commission_split_pct / 100.0)
                elif prop.co_user_id and lead.user_id == prop.user_id and 0 < prop.commission_split_pct < 100:
                    pct = pct * ((100.0 - prop.commission_split_pct) / 100.0)
                self.commission_pct = pct
        else:
            if lead.client_budget:
                self.sale_amount = lead.client_budget
            if lead.expected_commission and lead.client_budget:
                self.commission_pct = (lead.expected_commission / lead.client_budget) * 100.0
                
        if lead.user_id:
            self.user_id = lead.user_id

    @api.onchange('property_id', 'type')
    def _onchange_property_autofill(self):
        """Al elegir la propiedad, trae automáticamente su monto (precio o canon
        de arriendo) y su porcentaje de comisión. El Monto de Comisión se
        recalcula solo (sale_amount × commission_pct)."""
        if not self.property_id:
            return
        prop = self.property_id
        if self.type == 'rent':
            self.sale_amount = prop.rental_price or prop.price or 0.0
        else:
            self.sale_amount = prop.price or 0.0
        if prop.commission_percentage:
            pct = prop.commission_percentage
            if prop.is_allied_property:
                allied_ratio = (prop.allied_split_pct or 50.0) / 100.0
                pct = pct * allied_ratio
            self.commission_pct = pct
        if not self.user_id and prop.user_id:
            self.user_id = prop.user_id

    state = fields.Selection([
        ('draft', 'Borrador'),
        ('approved', 'Aprobada'),
        ('split', 'Repartida'),
        ('paid', 'Pagada'),
        ('cancelled', 'Cancelada')
    ], string='Estado', default='draft', tracking=True)

    invoice_id = fields.Many2one(
        'account.move', string='Factura de Comisión',
        readonly=True, copy=False,
        domain=[('move_type', '=', 'in_invoice')])
    client_collected = fields.Boolean(
        string='Cobrada al propietario', compute='_compute_client_collected',
        search='_search_client_collected',
        help='La venta de esta propiedad ya tiene la comisión cobrada al propietario '
             '(ver Ventas → Ventas cobradas). Recién ahí se puede pagar a los asesores.')
    client_collection_state = fields.Selection([
        ('none', 'Sin venta registrada'),
        ('pending', 'Por cobrar al propietario'),
        ('collected', 'Cobrada al propietario'),
    ], string='Cobro al propietario', compute='_compute_client_collected')

    def _sale_orders_by_property(self):
        orders = self.env['sale.order'].sudo().search([
            ('property_id', 'in', self.property_id.ids), ('state', '=', 'sale'),
        ]) if self.property_id else self.env['sale.order']
        result = {}
        for order in orders:
            result.setdefault(order.property_id.id, self.env['sale.order'])
            result[order.property_id.id] |= order
        return result

    def _compute_client_collected(self):
        by_property = self._sale_orders_by_property()
        for rec in self:
            orders = by_property.get(rec.property_id.id)
            if rec.type != 'sale' or not orders:
                rec.client_collection_state = 'none'
            elif any(orders.mapped('estate_commission_collected')):
                rec.client_collection_state = 'collected'
            else:
                rec.client_collection_state = 'pending'
            rec.client_collected = rec.client_collection_state == 'collected'

    def _search_client_collected(self, operator, value):
        if operator not in ('=', '!=') or not isinstance(value, bool):
            return NotImplemented
        orders = self.env['sale.order'].sudo().search([
            ('property_id', '!=', False), ('state', '=', 'sale'),
            ('estate_commission_collected', '=', True),
        ])
        positive = (operator == '=') == value
        return [('property_id', 'in' if positive else 'not in', orders.property_id.ids)]

    def _check_client_collected(self):
        """No se paga a los asesores lo que el propietario aún no ha pagado."""
        self.invalidate_recordset(['client_collected', 'client_collection_state'])
        pendientes = self.filtered(lambda c: c.client_collection_state == 'pending')
        if pendientes:
            raise UserError(
                'Todavía no se ha cobrado al propietario la comisión de "%s", así que '
                'no se puede pagar a los asesores.\n\nPuedes dejar listo el reparto '
                '(quién hizo captación, recepción, visita y cierre). Cuando te paguen, '
                'márcala en Ventas → Comisiones por cobrar y vuelve aquí a pagar.'
                % pendientes[0].property_id.display_name)

    invoice_state = fields.Selection(
        related='invoice_id.payment_state', string='Estado de Factura', readonly=True)

    # --- Constancia del pago al asesor ---
    payment_date = fields.Date(string='Fecha de Pago', default=fields.Date.context_today, copy=False,
        help='Fecha en que se pagó la comisión al asesor.')
    payment_method = fields.Selection([
        ('transfer', 'Transferencia'),
        ('cash', 'Efectivo'),
        ('deposit', 'Depósito'),
        ('check', 'Cheque'),
        ('other', 'Otro'),
    ], string='Forma de Pago', copy=False)
    payment_reference = fields.Char(string='Comprobante / Referencia', copy=False,
        help='Nº de transferencia, recibo o comprobante del pago.')
    paid_by_id = fields.Many2one('res.users', string='Pagado por', readonly=True, copy=False)

    has_invoice = fields.Selection(
        INVOICE_MODES, string='Factura', default='without', copy=False)
    amount_tax = fields.Monetary(
        string='IVA', currency_field='company_currency', copy=False)
    payment_id = fields.Many2one(
        'account.payment', string='Pago contable', readonly=True, copy=False,
        help='El pago registrado en Facturación (con o sin factura).')
    amount_total = fields.Monetary(
        string='Total pagado', currency_field='company_currency', copy=False)

    @api.constrains('amount', 'sale_amount')
    def _check_positive_amounts(self):
        for rec in self:
            if rec.amount < 0:
                raise UserError('El monto de la comisión no puede ser negativo.')
            if rec.sale_amount < 0:
                raise UserError('El monto de venta/renta no puede ser negativo.')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'NUEVO') == 'NUEVO':
                vals['name'] = self.env['ir.sequence'].next_by_code('estate.commission') or 'COM'
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        if 'split_line_ids' in vals:
            for rec in self.filtered(lambda c: c.state == 'split'):
                rec._sync_split_to_children()
        return res

    def _sync_split_to_children(self):
        """Sincroniza los cambios hechos en el reparto (porcentajes o asesores)
        con las comisiones hijas correspondientes."""
        for rec in self:
            roles_in_split = []
            for line in rec.split_line_ids:
                if not line.user_id or line.amount <= 0:
                    continue
                roles_in_split.append(line.role)
                child = rec.child_commission_ids.filtered(lambda c: c.role == line.role)
                if child:
                    if any(c.state == 'paid' for c in child):
                        continue
                    child.write({
                        'user_id': line.user_id.id,
                        'amount': line.amount,
                        'role_pct': line.percentage,
                        'commission_pct': rec.commission_pct * ((line.percentage or 0.0) / 100.0),
                    })
                else:
                    self.create({
                        'property_id': rec.property_id.id,
                        'lead_id': rec.lead_id.id,
                        'user_id': line.user_id.id,
                        'sale_amount': rec.sale_amount,
                        'commission_pct': rec.commission_pct * ((line.percentage or 0.0) / 100.0),
                        'amount': line.amount,
                        'role': line.role,
                        'role_pct': line.percentage,
                        'type': rec.type,
                        'date': rec.date,
                        'state': 'approved',
                        'parent_commission_id': rec.id,
                    })
            orphan_children = rec.child_commission_ids.filtered(
                lambda c: c.role not in roles_in_split and c.state in ('draft', 'approved'))
            if orphan_children:
                orphan_children.unlink()

    def action_approve(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError('Solo se pueden aprobar comisiones en estado Borrador.')
            if rec.amount <= 0:
                raise UserError('No se puede aprobar una comisión cuyo monto sea $0.00 o negativo.')
        self.write({'state': 'approved'})

    def action_cancel(self):
        for rec in self:
            if rec.state == 'paid':
                raise UserError('No se puede cancelar una comisión ya pagada.')
            if rec.state == 'draft' and rec.invoice_id and rec.invoice_id.state != 'cancel':
                rec.invoice_id.button_cancel()
        self.write({'state': 'cancelled'})

    def action_open_pay_wizard(self):
        """Abre el desglose por rol antes de pagarle a un único asesor."""
        self.ensure_one()
        if self.state == 'paid':
            raise UserError('Esta comisión ya está pagada.')
        if self.state == 'cancelled':
            raise UserError('No se puede pagar una comisión cancelada.')
        self._check_client_collected()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Pagar comisión al asesor',
            'res_model': 'estate.commission.pay.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_id': self.id},
        }

    def action_register_payment(self):
        """Paga las comisiones y deja todo registrado en Facturación.

        Las comisiones de un mismo asesor pagadas con los mismos datos (por
        ejemplo recepción, visita y cierre) se pagan juntas: una factura con
        una línea por rol y un solo pago, para un solo comprobante.
        - Con factura 15% / 0%: factura de proveedor del asesor con ese IVA,
          validada y pagada (el pago queda conciliado con la factura).
        - Sin factura: pago directo al asesor por el monto neto, sin factura."""
        self._check_client_collected()
        for rec in self:
            if rec.state == 'paid':
                raise UserError('Esta comisión ya está marcada como Pagada.')
            if rec.state == 'cancelled':
                raise UserError('No se puede pagar una comisión cancelada.')
            if rec.state == 'split':
                raise UserError(
                    'Esta comisión está repartida entre asesores: paga cada una '
                    'de las comisiones por asesor, no el total.')
            if rec.amount <= 0:
                raise UserError('No se puede registrar pago para una comisión cuyo monto sea $0.00 o negativo.')
            if not rec.payment_method:
                raise UserError(
                    'Indica la Forma de Pago en la sección "Pago al Asesor (Constancia)" antes de registrar el pago.')
            if not rec.user_id.partner_id:
                raise UserError('El asesor no tiene un contacto (partner) asociado.')

        groups = {}
        for rec in self:
            key = (rec.user_id.id, rec.has_invoice or 'without', rec.payment_method,
                   rec.payment_date, rec.payment_reference or '', rec.property_id.id)
            groups.setdefault(key, self.browse())
            groups[key] |= rec
        for group in groups.values():
            group._register_payment_group()
        return True

    def _register_payment_group(self):
        first = self[0]
        partner = first.user_id.partner_id
        mode = first.has_invoice or 'without'
        fecha = first.payment_date or fields.Date.context_today(first)
        journal = payment_journal(self.env, first.payment_method)
        if not journal:
            raise UserError('No hay un diario de Banco o Caja configurado en Facturación.')
        metodo = dict(self._fields['payment_method'].selection).get(first.payment_method, '')
        roles = dict(self._fields['role'].selection)
        base = round(sum(self.mapped('amount')), 2)
        for rec in self:
            rec.amount_tax = vat_amount(rec.amount, mode)
            rec.amount_total = round(rec.amount + rec.amount_tax, 2)
        iva = round(sum(self.mapped('amount_tax')), 2)
        nombres = ', '.join(self.mapped('name'))
        estate_vals = {
            'estate_kind': 'advisor',
            'estate_invoice_mode': mode,
            'estate_property_id': first.property_id.id,
            'estate_commission_id': first.id,
            'estate_base_amount': base,
            'estate_vat_amount': iva,
            'estate_method_label': metodo,
        }

        if is_invoiced(mode):
            invoice = self.mapped('invoice_id')[:1]
            if not invoice:
                account = self.env['account.account'].search([
                    ('account_type', '=', 'expense'),
                    ('company_ids', 'in', self.env.company.id),
                ], limit=1)
                tax = find_tax(self.env, 'purchase', mode)
                invoice = self.env['account.move'].create({
                    'move_type': 'in_invoice',
                    'partner_id': partner.id,
                    'invoice_date': fecha,
                    'ref': first.payment_reference or nombres,
                    'estate_transaction_type': 'commission',
                    'property_id': first.property_id.id,
                    'invoice_line_ids': [(0, 0, {
                        'name': 'Comisión %s%s — %s' % (
                            dict(rec._fields['type'].selection)[rec.type],
                            ' (%s)' % roles[rec.role] if rec.role else '',
                            rec.property_id.title or rec.name),
                        'quantity': 1.0,
                        'price_unit': rec.amount,
                        'account_id': account.id or False,
                        'tax_ids': [(6, 0, tax.ids)],
                    }) for rec in self],
                    'narration': 'Comisión %s para %s' % (nombres, partner.name),
                })
            self.invoice_id = invoice
            if invoice.state == 'draft':
                invoice.action_post()
            payments = self.env['account.payment']
            if invoice.payment_state not in ('paid', 'in_payment'):
                payments = self.env['account.payment.register'].with_context(
                    active_model='account.move', active_ids=invoice.ids,
                ).create({
                    'payment_date': fecha,
                    'journal_id': journal.id,
                    'communication': first.payment_reference or invoice.name,
                })._create_payments()
            if payments:
                payments.write(estate_vals)
                self.payment_id = payments[:1]
            detalle = 'Factura <b>%s</b> (%s) pagada.' % (invoice.name, dict(INVOICE_MODES)[mode])
        else:
            payment = self.env['account.payment'].create(dict(estate_vals, **{
                'payment_type': 'outbound',
                'partner_type': 'supplier',
                'partner_id': partner.id,
                'amount': base,
                'date': fecha,
                'journal_id': journal.id,
                'memo': '%s · %s' % (nombres, first.payment_reference or 'Comisión sin factura'),
            }))
            payment.action_post()
            self.payment_id = payment
            detalle = 'Pago sin factura <b>%s</b>.' % payment.name

        self.write({'state': 'paid', 'payment_date': fecha, 'paid_by_id': self.env.user.id})
        ref = ' (Ref: %s)' % first.payment_reference if first.payment_reference else ''
        for rec in self:
            rec.message_post(body=Markup(
                '<b>Comisión PAGADA</b> a <b>%s</b>: $%s%s el %s vía %s%s. %s Registrado por %s.') % (
                rec.user_id.name, '{:,.2f}'.format(rec.amount_total),
                Markup(' (base $%s + IVA $%s)') % ('{:,.2f}'.format(rec.amount), '{:,.2f}'.format(rec.amount_tax))
                if rec.amount_tax else '',
                fecha.strftime('%d/%m/%Y'), metodo, ref, Markup(detalle), self.env.user.name))

    def action_view_payment(self):
        self.ensure_one()
        if not self.payment_id:
            raise UserError('Esta comisión todavía no tiene un pago registrado.')
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'res_id': self.payment_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_print_receipt(self):
        """Comprobante de pago para que el asesor lo firme."""
        paid = self.filtered(lambda c: c.state == 'paid')
        if not paid:
            raise UserError('Solo se puede imprimir el comprobante de comisiones pagadas.')
        if all(paid.mapped('payment_id')):
            return self.env.ref('estate_management.action_report_estate_payment_receipt').report_action(
                paid.mapped('payment_id'))
        return self.env.ref('estate_management.action_report_commission_receipt').report_action(paid)

    def action_reset_to_approved(self):
        """Revierte un pago registrado por error (vuelve a Aprobada).
        Si el pago cubría varias comisiones del asesor, se revierten todas."""
        shared = self.mapped('payment_id') and self.search([
            ('payment_id', 'in', self.mapped('payment_id').ids), ('state', '=', 'paid')])
        for rec in self | (shared or self.browse()):
            if rec.state != 'paid':
                raise UserError('Solo se pueden revertir comisiones Pagadas.')
            # Se anula también lo contable, para que en Facturación no quede
            # un pago que ya no existe.
            if rec.payment_id and rec.payment_id.state != 'canceled':
                rec.payment_id.action_draft()
                rec.payment_id.action_cancel()
            if rec.invoice_id and rec.invoice_id.state != 'cancel':
                if rec.invoice_id.payment_state in ('paid', 'in_payment', 'partial'):
                    rec.invoice_id._get_reconciled_payments().filtered(
                        lambda p: p.state != 'canceled').action_cancel()
                if rec.invoice_id.state == 'posted':
                    rec.invoice_id.button_draft()
                rec.invoice_id.button_cancel()
            rec.write({'state': 'approved', 'payment_date': False,
                       'payment_method': False, 'payment_reference': False,
                       'paid_by_id': False, 'payment_id': False,
                       'invoice_id': False, 'amount_tax': 0.0, 'amount_total': 0.0})
            rec.message_post(body=f"Pago de comisión REVERTIDO por {self.env.user.name}.")
        return True

    def action_generate_invoice(self):
        """Genera una factura de proveedor (vendor bill) para pagar la comisión al asesor."""
        self.ensure_one()
        if self.invoice_id:
            raise UserError('Esta comisión ya tiene una factura generada.')
        if self.state not in ('approved', 'draft'):
            raise UserError('Solo se puede generar factura para comisiones en borrador o aprobadas.')

        partner = self.user_id.partner_id
        if not partner:
            raise UserError('El asesor no tiene un contacto (partner) asociado.')

        # Buscar cuenta de comisiones o usar la genérica de gastos
        commission_account = self.env['account.account'].search([
            ('account_type', '=', 'expense'),
            ('company_ids', 'in', self.env.company.id),
        ], limit=1)

        invoice_vals = {
            'move_type': 'in_invoice',
            'partner_id': partner.id,
            'invoice_date': self.date or fields.Date.context_today(self),
            'estate_transaction_type': 'commission',
            'invoice_line_ids': [(0, 0, {
                'name': f'Comisión {dict(self._fields["type"].selection)[self.type]} — {self.property_id.title or self.name}',
                'quantity': 1.0,
                'price_unit': self.amount,
                'account_id': commission_account.id if commission_account else False,
            })],
            'narration': f'Comisión generada desde {self.name} para {partner.name}',
        }
        invoice = self.env['account.move'].create(invoice_vals)
        self.write({'invoice_id': invoice.id, 'state': 'approved'})
        self.message_post(
            body=f'Factura de comisión <b>{invoice.name or "borrador"}</b> generada para <b>{partner.name}</b>.',
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_invoice(self):
        self.ensure_one()
        if not self.invoice_id:
            raise UserError('No hay factura generada para esta comisión.')
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
        }


class EstateCommissionSplit(models.Model):
    """Reparto de una comisión entre los asesores que participaron.

    Los roles no se fijan en la propiedad porque varían negocio a negocio: uno
    recibe el contacto, otro hace la visita, otro cierra y la captación puede
    ser de un cuarto. Por eso se asignan aquí, al momento de pagar.
    """
    _name = 'estate.commission.split'
    _description = 'Reparto de comisión por rol'
    _order = 'sequence, id'

    commission_id = fields.Many2one(
        'estate.commission', string='Comisión', required=True,
        ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    role = fields.Selection(
        EstateCommissionSplit_ROLES, string='Rol', required=True, default='other')
    user_id = fields.Many2one(
        'res.users', string='Asesor', domain=[('share', '=', False)],
        help='Quien realizó este paso del negocio. Déjalo vacío si no aplica: '
             'ese porcentaje se queda en la oficina.')
    percentage = fields.Float(
        string='% de los honorarios', required=True, default=0.0,
        help='Porcentaje sobre los honorarios de la agencia, no sobre el precio '
             'de venta.')
    amount = fields.Monetary(
        string='A pagar', compute='_compute_amount', store=True, readonly=False,
        currency_field='company_currency')
    company_currency = fields.Many2one(
        'res.currency', related='commission_id.company_currency', readonly=True)
    note = fields.Char(string='Observación')

    @api.depends('percentage', 'commission_id.amount')
    def _compute_amount(self):
        for line in self:
            base = line.commission_id.amount or 0.0
            line.amount = base * ((line.percentage or 0.0) / 100.0)

    @api.constrains('percentage')
    def _check_percentage(self):
        for line in self:
            if not (0.0 <= line.percentage <= 100.0):
                raise ValidationError('El porcentaje del rol debe estar entre 0 y 100.')

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for com in records.mapped('commission_id').filtered(lambda c: c.state == 'split'):
            com._sync_split_to_children()
        return records

    def write(self, vals):
        res = super().write(vals)
        if any(f in vals for f in ('percentage', 'user_id', 'amount', 'role')):
            for com in self.mapped('commission_id').filtered(lambda c: c.state == 'split'):
                com._sync_split_to_children()
        return res

    def unlink(self):
        comms = self.mapped('commission_id').filtered(lambda c: c.state == 'split')
        res = super().unlink()
        for com in comms:
            com._sync_split_to_children()
        return res

