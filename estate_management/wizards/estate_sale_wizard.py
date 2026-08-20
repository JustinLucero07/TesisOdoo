import logging
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class EstateSaleWizard(models.TransientModel):
    _name = 'estate.sale.wizard'
    _description = 'Asistente de Venta de Propiedad'

    property_id = fields.Many2one('estate.property', string='Propiedad', required=True, readonly=True)
    offer_type = fields.Selection(related='property_id.offer_type', readonly=True)
    buyer_id = fields.Many2one('res.partner', string='Comprador')
    sale_price = fields.Float(string='Precio de Cierre')
    date_sold = fields.Date(string='Fecha de Cierre', default=fields.Date.today, required=True)
    sold_by = fields.Selection([
        ('agency', 'Agencia'),
        ('owner', 'Propietario'),
        ('external', 'Externo'),
    ], string='Cerrado por', default='agency', required=True)
    user_id = fields.Many2one(
        'res.users', string='Asesor a Cargo (Vendedor)',
        default=lambda self: self._default_user_id(),
        help='Asesor responsable del cierre y comisiones.')

    def _default_user_id(self):
        if self.env.context.get('active_id'):
            prop = self.env['estate.property'].browse(self.env.context['active_id'])
            if prop.user_id:
                return prop.user_id
        return self.env.user

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if res.get('property_id') and self.env.context.get('edit_deal_mode'):
            prop = self.env['estate.property'].browse(res['property_id'])
            res.update({
                'buyer_id': prop.buyer_id.id if prop.buyer_id else False,
                'sale_price': prop.price,
                'commission_pct': prop.commission_percentage,
                'date_sold': prop.date_sold or fields.Date.today(),
                'sold_by': prop.sold_by or 'agency',
                'buyer_proxy_id': prop.proxy_id.id if prop.proxy_id else False,
                'deal_deadline': prop.deal_deadline,
                'deal_earnest_amount': prop.deal_earnest_amount,
                'deal_earnest_received_by_agency': prop.deal_earnest_received_by_agency,
                'deal_earnest_received_by_owner': prop.deal_earnest_received_by_owner,
                'deal_earnest_received_by_proxy': prop.deal_earnest_received_by_proxy,
                'deal_earnest_payment_cash': prop.deal_earnest_payment_cash,
                'deal_earnest_payment_transfer': prop.deal_earnest_payment_transfer,
                'deal_earnest_payment_deposit': prop.deal_earnest_payment_deposit,
                'deal_earnest_payment_other_check': prop.deal_earnest_payment_other_check,
                'deal_earnest_payment_other': prop.deal_earnest_payment_other,
                'deal_payment_type': prop.deal_payment_type,
                'deal_payment_details': prop.deal_payment_details,
                'deal_credit_institution': prop.deal_credit_institution,
                'deal_credit_advisor': prop.deal_credit_advisor,
                'deal_credit_advisor_phone': prop.deal_credit_advisor_phone,
                'deal_observations': prop.deal_observations,
            })
            return res

        if 'lead_id' in fields_list and not res.get('lead_id') and res.get('property_id'):
            lead = self.env['crm.lead'].search([
                ('target_property_id', '=', res['property_id']), ('type', '=', 'opportunity'),
            ], limit=1)
            if lead:
                res['lead_id'] = lead.id
                if 'buyer_id' in fields_list and not res.get('buyer_id') and lead.partner_id:
                    res['buyer_id'] = lead.partner_id.id
                if 'sale_price' in fields_list and not res.get('sale_price') and lead.client_budget:
                    res['sale_price'] = lead.client_budget
        return res

    is_edit_mode = fields.Boolean(
        string='Modo Edición',
        default=lambda self: self.env.context.get('edit_deal_mode', False))

    commission_pct = fields.Float(string='Comisión (%)')
    commission_amount = fields.Float(string='Monto Comisión', compute='_compute_commission_amount')
    lead_id = fields.Many2one(
        'crm.lead', string='Lead de Origen (CRM)',
        domain="[('type', '=', 'opportunity')]",
        help='Si esta venta viene de un lead del CRM, selecciónalo para completar '
             'comprador y precio automáticamente.')
    invoice_mode = fields.Selection([
        ('commission', 'Facturar Solo Comisión de Corretaje (Honorarios de Agencia)'),
        ('total', 'Facturar Valor Total del Inmueble (Proyecto Propio / Constructora)'),
        ('none', 'Sin Factura de Venta (Solo Registro Interno en Inmobi)')
    ], string='Modo de Facturación al Cliente', default='commission', required=True,
       help='En corretaje tradicional, la agencia factura únicamente sus honorarios/comisión al cliente. En proyectos propios, la constructora factura el valor total de la propiedad.')
    apply_vat = fields.Boolean(
        string='Aplicar IVA 15%', default=False,
        help='Si se marca, la línea de la factura de esta venta lleva IVA 15%. '
             'Si no, queda con el impuesto por defecto del producto (0%).')

    # --- Datos del Negocio Cerrado ---
    buyer_proxy_id = fields.Many2one('res.partner', string='Apoderado del Comprador')
    deal_deadline = fields.Date(string='Fecha Máxima de Cumplimiento')
    deal_earnest_amount = fields.Float(string='Seña / Arras ($)')
    deal_earnest_received_by_agency = fields.Boolean(string='Recibió Inmobiliaria')
    deal_earnest_received_by_owner = fields.Boolean(string='Recibió Dueño')
    deal_earnest_received_by_proxy = fields.Boolean(string='Recibió Apoderado')
    deal_earnest_payment_cash = fields.Boolean(string='Efectivo')
    deal_earnest_payment_transfer = fields.Boolean(string='Transferencia')
    deal_earnest_payment_deposit = fields.Boolean(string='Depósito')
    deal_earnest_payment_other_check = fields.Boolean(string='Otro')
    deal_earnest_payment_other = fields.Char(string='Detalles del Pago (Banco, Cheque, etc.)')
    deal_payment_type = fields.Selection([
        ('cash', 'Contado'),
        ('mortgage', 'Hipotecario (BIESS/Banco)'),
        ('owner', 'Financiamiento del Vendedor'),
        ('mixed', 'Mixto'),
        ('other', 'Otro'),
    ], string='Forma de Pago', default='cash')
    deal_payment_details = fields.Text(string='Detalles del Negocio')
    deal_credit_institution = fields.Char(string='Institución de Crédito')
    deal_credit_advisor = fields.Char(string='Asesor de Crédito')
    deal_credit_advisor_phone = fields.Char(string='Teléfono Asesor de Crédito')
    deal_observations = fields.Text(string='Observaciones')

    def _deal_note_lines(self):
        """Líneas con los datos del Negocio Cerrado para volcar en la Orden de
        Venta (aparecen impresas en la cotización/factura), incluida la seña."""
        lines = []
        if self.deal_payment_details:
            lines.append(f"Detalles de Pago: {self.deal_payment_details}")
        if self.deal_earnest_amount:
            rec_list = []
            if self.deal_earnest_received_by_agency: rec_list.append('Inmobiliaria')
            if self.deal_earnest_received_by_owner: rec_list.append('Dueño')
            if self.deal_earnest_received_by_proxy: rec_list.append('Apoderado')
            received_by = ', '.join(rec_list) if rec_list else 'N/A'

            meth_list = []
            if self.deal_earnest_payment_cash: meth_list.append('Efectivo')
            if self.deal_earnest_payment_transfer: meth_list.append('Transferencia')
            if self.deal_earnest_payment_deposit: meth_list.append('Depósito')
            if self.deal_earnest_payment_other_check: meth_list.append('Otro')
            method_str = ', '.join(meth_list) if meth_list else 'N/A'
            if (self.deal_earnest_payment_transfer or self.deal_earnest_payment_deposit or self.deal_earnest_payment_other_check) and self.deal_earnest_payment_other:
                method_str += f" - {self.deal_earnest_payment_other}"
            lines.append(f"Seña/Arras: ${self.deal_earnest_amount:,.2f} (Recibido por: {received_by} - Vía: {method_str})")
        if self.deal_observations:
            lines.append(f"Observaciones: {self.deal_observations}")
        return lines

    @api.onchange('lead_id')
    def _onchange_lead_id(self):
        for rec in self:
            if not rec.lead_id:
                continue
            lead = rec.lead_id
            if lead.partner_id:
                rec.buyer_id = lead.partner_id
            if lead.client_budget:
                rec.sale_price = lead.client_budget
            if lead.user_id:
                rec.user_id = lead.user_id

    @api.depends('sale_price', 'commission_pct', 'sold_by')
    def _compute_commission_amount(self):
        for rec in self:
            # "Externo" se trata igual que "Propietario": la agencia no
            # intermedió en el cierre, así que no genera comisión propia.
            if rec.sold_by in ('owner', 'external'):
                rec.commission_amount = 0.0
            elif rec.sale_price and rec.commission_pct:
                rec.commission_amount = rec.sale_price * (rec.commission_pct / 100.0)
            else:
                rec.commission_amount = 0.0

    def action_confirm_sale(self):
        """
        Confirma la venta, actualiza la propiedad con los datos de cierre,
        genera la orden de venta nativa + factura de cliente y crea las comisiones.
        """
        self.ensure_one()
        prop = self.property_id
        if self.env.context.get('edit_deal_mode') or self.is_edit_mode:
            if prop.state != 'sold':
                raise UserError('Solo se pueden modificar los datos de propiedades ya vendidas.')
        else:
            if prop.state not in ('available', 'reserved'):
                raise UserError('Solo se puede vender una propiedad Disponible o Reservada.')
        if self.sold_by not in ('owner', 'external'):
            if not self.buyer_id:
                raise UserError('Asigna un comprador para registrar la venta (a menos que haya sido venta directa por el propietario o un cierre externo).')
            if self.sale_price <= 0:
                raise UserError('El precio de cierre de la propiedad debe ser mayor a 0.')
            if not (0 < self.commission_pct <= 100):
                raise UserError('El porcentaje de comisión debe estar entre 0.1% y 100%.')
        if prop.owner_id and self.buyer_id and self.buyer_id == prop.owner_id:
            raise UserError('El comprador no puede ser el mismo propietario del inmueble.')

        # Despublicar de WordPress antes de cerrar
        if prop.wp_published and prop.wp_post_id and hasattr(prop, 'action_unpublish_wordpress'):
            try:
                prop.action_unpublish_wordpress()
            except Exception as e:
                _logger.warning('WP unpublish al vender propiedad %s falló: %s', prop.id, e)

        # Origen del lead (Facebook, Sitio Web, Referido, etc.), si el lead
        # seleccionado en el wizard tiene una fuente registrada en el CRM.
        lead_origin = False
        if self.lead_id and hasattr(self.lead_id, 'lead_source_id') and self.lead_id.lead_source_id:
            lead_origin = self.lead_id.lead_source_id.name

        if self.env.context.get('edit_deal_mode') or self.is_edit_mode:
            prop_vals = {
                'buyer_id': self.buyer_id.id,
                'price': self.sale_price,
                'commission_percentage': self.commission_pct,
                'date_sold': self.date_sold,
                'sold_by': self.sold_by,
                'user_id': self.user_id.id if self.user_id else False,
                'deal_deadline': self.deal_deadline,
                'deal_earnest_amount': self.deal_earnest_amount,
                'deal_earnest_received_by_agency': self.deal_earnest_received_by_agency,
                'deal_earnest_received_by_owner': self.deal_earnest_received_by_owner,
                'deal_earnest_received_by_proxy': self.deal_earnest_received_by_proxy,
                'deal_earnest_payment_cash': self.deal_earnest_payment_cash,
                'deal_earnest_payment_transfer': self.deal_earnest_payment_transfer,
                'deal_earnest_payment_deposit': self.deal_earnest_payment_deposit,
                'deal_earnest_payment_other_check': self.deal_earnest_payment_other_check,
                'deal_earnest_payment_other': self.deal_earnest_payment_other,
                'deal_payment_type': self.deal_payment_type,
                'deal_payment_details': self.deal_payment_details,
                'deal_credit_institution': self.deal_credit_institution,
                'deal_credit_advisor': self.deal_credit_advisor,
                'deal_credit_advisor_phone': self.deal_credit_advisor_phone,
                'deal_observations': self.deal_observations,
            }
            if lead_origin:
                prop_vals['deal_lead_origin'] = lead_origin
            if self.buyer_proxy_id:
                prop_vals['proxy_id'] = self.buyer_proxy_id.id
            prop.with_context(no_wp_sync=True).write(prop_vals)

            # Sincronizar la comisión ya generada con los datos corregidos: el
            # asesor pudo cambiar, o el precio/porcentaje pudo corregirse
            # después de la venta original. No se tocan comisiones ya pagadas
            # (son un registro histórico de un pago que ya se hizo).
            commissions = self.env['estate.commission'].search([
                ('property_id', '=', prop.id),
                ('state', 'in', ('draft', 'approved')),
            ])
            if len(commissions) == 1:
                commissions.write({
                    'user_id': self.user_id.id,
                    'sale_amount': self.sale_price,
                    'commission_pct': self.commission_pct,
                })
            elif len(commissions) > 1:
                prop.message_post(
                    body='<b>Aviso:</b> hay varias comisiones (reparto con co-asesor) vinculadas '
                         'a este negocio y no se sincronizaron automáticamente al editar — revísalas '
                         'manualmente en el menú Comisiones si el asesor o el monto cambiaron.')

            # Actualizar también las notas en la orden de venta (sale.order) y factura si existen
            orders = self.env['sale.order'].search([('property_id', '=', prop.id)])
            for ord in orders:
                ord_vals = {}
                if self.user_id:
                    ord_vals['user_id'] = self.user_id.id
                notes = self._deal_note_lines()
                if notes:
                    ord_vals['note'] = "\n\n".join(notes)
                if ord_vals:
                    ord.write(ord_vals)

            prop.message_post(body='<b>Datos del Negocio Cerrado y documentos actualizados exitosamente.</b>')
            return {'type': 'ir.actions.act_window_close'}

        # 1. Datos núcleo de la propiedad + datos del Negocio Cerrado (sin sync WP)
        prop_vals = {
            'offer_type': 'sale',
            'buyer_id': self.buyer_id.id,
            'price': self.sale_price,
            'commission_percentage': self.commission_pct,
            'date_sold': self.date_sold,
            'sold_by': self.sold_by,
            'user_id': self.user_id.id if self.user_id else False,
            'deal_deadline': self.deal_deadline,
            'deal_earnest_amount': self.deal_earnest_amount,
            'deal_earnest_received_by_agency': self.deal_earnest_received_by_agency,
            'deal_earnest_received_by_owner': self.deal_earnest_received_by_owner,
            'deal_earnest_received_by_proxy': self.deal_earnest_received_by_proxy,
            'deal_earnest_payment_cash': self.deal_earnest_payment_cash,
            'deal_earnest_payment_transfer': self.deal_earnest_payment_transfer,
            'deal_earnest_payment_deposit': self.deal_earnest_payment_deposit,
            'deal_earnest_payment_other_check': self.deal_earnest_payment_other_check,
            'deal_earnest_payment_other': self.deal_earnest_payment_other,
            'deal_payment_type': self.deal_payment_type,
            'deal_payment_details': self.deal_payment_details,
            'deal_credit_institution': self.deal_credit_institution,
            'deal_credit_advisor': self.deal_credit_advisor,
            'deal_credit_advisor_phone': self.deal_credit_advisor_phone,
            'deal_observations': self.deal_observations,
        }
        if lead_origin:
            prop_vals['deal_lead_origin'] = lead_origin
        if self.buyer_proxy_id:
            prop_vals['proxy_id'] = self.buyer_proxy_id.id
        prop.with_context(no_wp_sync=True).write(prop_vals)

        # 2-3. Orden de venta confirmada + factura contabilizada
        order, invoice = False, False
        if self.sold_by not in ('owner', 'external'):
            order, invoice = prop._process_native_sale(
                self.buyer_id, self.sale_price, self.commission_amount, self.commission_pct,
                invoice_mode=self.invoice_mode, user_id=self.user_id, apply_vat=self.apply_vat)
        else:
            # "Propietario" y "Externo" comparten el mismo registro: una orden
            # de venta de $0 para que cuente como venta en el Dashboard, sin
            # generar comisiones (la agencia no intermedió en el cierre).
            partner = self.buyer_id or prop.owner_id
            if partner:
                order = self.env['sale.order'].create({
                    'partner_id': partner.id,
                    'property_id': prop.id,
                    'estate_transaction_type': 'sale',
                    'state': 'sale',
                    'user_id': self.user_id.id if self.user_id else False,
                    'lead_id': self.lead_id.id if self.lead_id else False,
                })
                origin_label = 'Propietario' if self.sold_by == 'owner' else 'Externo'
                self.env['sale.order.line'].create({
                    'order_id': order.id,
                    'name': f"Registro de Venta Directa ({origin_label}): {prop.title}",
                    'price_unit': 0.0,
                    'product_uom_qty': 1,
                })

        # Volcar los datos del Negocio Cerrado (incl. seña) como nota de la
        # orden, para que también aparezcan al imprimir la cotización/factura.
        if order:
            notes = self._deal_note_lines()
            if notes:
                order.write({'note': "\n\n".join(notes)})

        # 4. Marcar vendida
        prop.with_context(no_wp_sync=True).write({'state': 'sold'})

        # 5. Comisión del asesor
        if self.sold_by not in ('owner', 'external'):
            target_lead = self.lead_id or (order.lead_id if order and hasattr(order, 'lead_id') else False)
            prop._create_commission_records('sale', self.commission_amount, self.sale_price, self.commission_pct, lead_id=target_lead.id if target_lead else False)

        # Resumen en el chatter de la propiedad
        if self.sold_by in ('owner', 'external'):
            origin_label = 'el Propietario' if self.sold_by == 'owner' else 'un Cierre Externo'
            msg = [f'<b>Venta registrada</b> (Cerrado por {origin_label}):']
            msg.append('• No se generó orden de venta ni comisiones para la agencia.')
        else:
            msg = ['<b>Venta registrada</b> mediante el flujo unificado:']
            if order:
                msg.append(f'• Orden de venta confirmada: <b>{order.name}</b>')
            if invoice:
                estado = 'contabilizada' if invoice.state == 'posted' else 'en borrador'
                msg.append(f'• Factura {estado}: <b>{invoice.name or invoice.id}</b>')
            msg.append(f'• Comisión registrada: <b>${self.commission_amount:,.2f}</b>')
        prop.message_post(body='<br/>'.join(msg))

        # 6. Marcar oportunidad de CRM como ganada si está vinculada
        target_lead = self.lead_id or (order.lead_id if order and hasattr(order, 'lead_id') else False)
        if target_lead and hasattr(target_lead, 'action_set_won_rainbowman'):
            try:
                target_lead.action_set_won_rainbowman()
            except Exception:
                pass
        if target_lead:
            target_lead.message_post(body=f'Venta de propiedad <b>{prop.title}</b> confirmada por <b>${self.sale_price:,.2f}</b> con comisión de <b>${self.commission_amount:,.2f}</b>.')

        # Abrir la factura generada (o la orden si no hubo factura)
        if invoice:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Factura de la Venta',
                'res_model': 'account.move',
                'view_mode': 'form',
                'res_id': invoice.id,
                'target': 'current',
            }
        if order:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Orden de Venta',
                'res_model': 'sale.order',
                'view_mode': 'form',
                'res_id': order.id,
                'target': 'current',
            }
        return {'type': 'ir.actions.act_window_close'}
