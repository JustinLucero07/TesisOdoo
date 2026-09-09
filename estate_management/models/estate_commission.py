from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

# Los pasos del negocio que pueden cobrar comisión. Se definen aquí porque los
# usan tanto la comisión como sus líneas de reparto.
EstateCommissionSplit_ROLES = [
    ('capture', 'Captación'),
    ('reception', 'Recepción'),
    ('visit', 'Visita'),
    ('closing', 'Cierre'),
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
        currency_field='company_currency')
    pct_assigned = fields.Float(
        string='% repartido', compute='_compute_split_totals', store=True)
    is_exclusive = fields.Boolean(
        string='Captación en exclusividad', related='property_id.is_exclusive',
        readonly=True)

    _ROLE_ORDER = {'capture': 1, 'reception': 2, 'visit': 3, 'closing': 4, 'other': 9}

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
                 'child_commission_ids.amount')
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
            rec.amount_office = (rec.amount or 0.0) - rec.amount_assigned

    def _default_split_values(self):
        """Los cuatro pasos del negocio con los porcentajes configurados.

        El asesor queda vacío a propósito: se asigna al momento de pagar, que es
        cuando se sabe quién recibió, quién visitó y quién cerró.
        """
        self.ensure_one()
        company = self.env.company
        pct_captacion = (company.estate_pct_capture_exclusive
                         if self.property_id.is_exclusive
                         else company.estate_pct_capture)
        captador = (self.property_id.exclusive_user_id
                    or self.property_id.user_id or self.user_id)
        return [
            {'sequence': 10, 'role': 'capture', 'percentage': pct_captacion,
             'user_id': captador.id if captador else False},
            {'sequence': 20, 'role': 'reception', 'percentage': company.estate_pct_reception},
            {'sequence': 30, 'role': 'visit', 'percentage': company.estate_pct_visit},
            {'sequence': 40, 'role': 'closing', 'percentage': company.estate_pct_closing},
        ]

    def action_generate_split(self):
        """Rellena el reparto con los cuatro roles y sus porcentajes."""
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
        if self.state == 'paid':
            raise UserError('Esta comisión ya está pagada; no se puede repartir.')
        if self.child_commission_ids:
            raise UserError(
                'Esta comisión ya fue repartida. Revisa las comisiones por asesor.')
        lineas = self.split_line_ids.filtered(lambda l: l.user_id and l.amount > 0)
        if not lineas:
            raise UserError(
                'Asigna al menos un asesor con monto en el reparto antes de generarlo.')
        if not self.payment_method:
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
    invoice_state = fields.Selection(
        related='invoice_id.payment_state', string='Estado de Factura', readonly=True)

    # --- Constancia del pago al asesor ---
    payment_date = fields.Date(string='Fecha de Pago', default=fields.Date.context_today, copy=False,
        help='Fecha en que se pagó la comisión al asesor.')
    payment_method = fields.Selection([
        ('transfer', 'Transferencia'),
        ('cash', 'Efectivo'),
        ('check', 'Cheque'),
        ('other', 'Otro'),
    ], string='Forma de Pago', copy=False)
    payment_reference = fields.Char(string='Comprobante / Referencia', copy=False,
        help='Nº de transferencia, recibo o comprobante del pago.')
    paid_by_id = fields.Many2one('res.users', string='Pagado por', readonly=True, copy=False)

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

    def action_register_payment(self):
        """Registra el pago de la comisión al asesor y deja constancia.
        Si la factura de proveedor no ha sido creada, la genera automáticamente,
        la valida (action_post) y le registra el pago contable para dejarla en estado Pagado."""
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

            # 1. Generar factura de comisión si no existe
            if not rec.invoice_id:
                partner = rec.user_id.partner_id
                if not partner:
                    raise UserError('El asesor no tiene un contacto (partner) asociado.')
                commission_account = self.env['account.account'].search([
                    ('account_type', '=', 'expense'),
                    ('company_ids', 'in', self.env.company.id),
                ], limit=1)
                invoice_vals = {
                    'move_type': 'in_invoice',
                    'partner_id': partner.id,
                    'invoice_date': rec.payment_date or fields.Date.context_today(rec),
                    'estate_transaction_type': 'commission',
                    'invoice_line_ids': [(0, 0, {
                        'name': f'Comisión {dict(rec._fields["type"].selection)[rec.type]} — {rec.property_id.title or rec.name}',
                        'quantity': 1.0,
                        'price_unit': rec.amount,
                        'account_id': commission_account.id if commission_account else False,
                    })],
                    'narration': f'Comisión generada desde {rec.name} para {partner.name}',
                }
                invoice = self.env['account.move'].create(invoice_vals)
                rec.invoice_id = invoice.id

            # 2. Confirmar / Publicar la factura contable si está en borrador
            if rec.invoice_id.state == 'draft':
                rec.invoice_id.action_post()

            # 3. Registrar el pago contable en la factura (si no está ya pagada)
            if rec.invoice_id.payment_state not in ('paid', 'in_payment'):
                journal_type = 'bank' if rec.payment_method in ('transfer', 'check') else 'cash'
                journal = self.env['account.journal'].search([
                    ('type', '=', journal_type),
                    ('company_id', '=', self.env.company.id),
                ], limit=1)
                if not journal:
                    journal = self.env['account.journal'].search([
                        ('type', 'in', ('bank', 'cash')),
                        ('company_id', '=', self.env.company.id),
                    ], limit=1)
                if journal:
                    payment_register = self.env['account.payment.register'].with_context(
                        active_model='account.move',
                        active_ids=[rec.invoice_id.id]
                    ).create({
                        'payment_date': rec.payment_date or fields.Date.context_today(rec),
                        'journal_id': journal.id,
                        'communication': rec.payment_reference or rec.name,
                    })
                    payment_register._create_payments()

            # 4. Actualizar estado y constancia de la comisión
            rec.write({
                'state': 'paid',
                'payment_date': rec.payment_date or fields.Date.context_today(rec),
                'paid_by_id': self.env.user.id,
            })
            metodo = dict(rec._fields['payment_method'].selection).get(rec.payment_method, '')
            ref = f" (Ref: {rec.payment_reference})" if rec.payment_reference else ''
            rec.message_post(
                body=(f"<b>Comisión PAGADA</b> al asesor <b>{rec.user_id.name}</b> "
                      f"por <b>${rec.amount:,.2f}</b> el {rec.payment_date} "
                      f"vía {metodo}{ref}. Factura contable <b>{rec.invoice_id.name}</b> autogenerada y conciliada. "
                      f"Registrado por {self.env.user.name}."))
        return True

    def action_reset_to_approved(self):
        """Revierte un pago registrado por error (vuelve a Aprobada)."""
        for rec in self:
            if rec.state != 'paid':
                raise UserError('Solo se pueden revertir comisiones Pagadas.')
            rec.write({'state': 'approved', 'payment_date': False,
                       'payment_method': False, 'payment_reference': False,
                       'paid_by_id': False})
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
