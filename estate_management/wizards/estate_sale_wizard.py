import logging
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class EstateSaleWizard(models.TransientModel):
    _name = 'estate.sale.wizard'
    _description = 'Asistente de Venta de Propiedad'

    property_id = fields.Many2one('estate.property', string='Propiedad', required=True, readonly=True)
    offer_type = fields.Selection(related='property_id.offer_type', readonly=True)
    buyer_id = fields.Many2one('res.partner', string='Comprador', required=True)
    sale_price = fields.Float(string='Precio de Cierre', required=True)
    date_sold = fields.Date(string='Fecha de Cierre', default=fields.Date.today, required=True)
    sold_by = fields.Selection([
        ('agency', 'Agencia'),
        ('owner', 'Propietario'),
        ('external', 'Externo'),
    ], string='Cerrado por', default='agency', required=True)
    commission_pct = fields.Float(string='Comisión (%)', required=True)
    commission_amount = fields.Float(string='Monto Comisión', compute='_compute_commission_amount')

    # --- Datos del Negocio Cerrado ---
    buyer_proxy_id = fields.Many2one('res.partner', string='Apoderado del Comprador')
    deal_deadline = fields.Date(string='Fecha Máxima de Cumplimiento')
    deal_earnest_amount = fields.Float(string='Seña / Arras ($)')
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

    @api.depends('sale_price', 'commission_pct')
    def _compute_commission_amount(self):
        for rec in self:
            rec.commission_amount = (rec.sale_price or 0.0) * (rec.commission_pct / 100.0)

    def action_confirm_sale(self):
        """Flujo de venta unificado y automático:
        1. Actualiza la propiedad (comprador, precio, comisión).
        2. Crea y CONFIRMA la orden de venta (sale.order → módulo Ventas).
        3. Genera y CONTABILIZA la factura (account.move → módulo Facturación).
        4. Marca la propiedad como Vendida.
        5. Registra la comisión del asesor.
        """
        self.ensure_one()
        prop = self.property_id
        if prop.state not in ('available', 'reserved'):
            raise UserError('Solo se puede vender una propiedad Disponible o Reservada.')
        if not self.buyer_id:
            raise UserError('Asigna un comprador para registrar la venta.')

        # Despublicar de WordPress antes de cerrar
        if prop.wp_published and prop.wp_post_id and hasattr(prop, 'action_unpublish_wordpress'):
            try:
                prop.action_unpublish_wordpress()
            except Exception as e:
                _logger.warning('WP unpublish al vender propiedad %s falló: %s', prop.id, e)

        # 1. Datos núcleo de la propiedad + datos del Negocio Cerrado (sin sync WP)
        prop_vals = {
            'offer_type': 'sale',
            'buyer_id': self.buyer_id.id,
            'price': self.sale_price,
            'commission_percentage': self.commission_pct,
            'date_sold': self.date_sold,
            'sold_by': self.sold_by,
            'deal_deadline': self.deal_deadline,
            'deal_earnest_amount': self.deal_earnest_amount,
            'deal_payment_type': self.deal_payment_type,
            'deal_payment_details': self.deal_payment_details,
            'deal_credit_institution': self.deal_credit_institution,
            'deal_credit_advisor': self.deal_credit_advisor,
            'deal_credit_advisor_phone': self.deal_credit_advisor_phone,
            'deal_observations': self.deal_observations,
        }
        if self.buyer_proxy_id:
            prop_vals['proxy_id'] = self.buyer_proxy_id.id
        prop.with_context(no_wp_sync=True).write(prop_vals)

        # 2-3. Orden de venta confirmada + factura contabilizada
        order, invoice = prop._process_native_sale(
            self.buyer_id, self.sale_price, self.commission_amount, self.commission_pct)

        # 4. Marcar vendida
        prop.with_context(no_wp_sync=True).write({'state': 'sold'})

        # 5. Comisión del asesor
        prop._create_commission_records('sale', self.commission_amount, self.sale_price, self.commission_pct)

        # Resumen en el chatter de la propiedad
        msg = ['<b>Venta registrada</b> mediante el flujo unificado:']
        if order:
            msg.append(f'• Orden de venta confirmada: <b>{order.name}</b>')
        if invoice:
            estado = 'contabilizada' if invoice.state == 'posted' else 'en borrador'
            msg.append(f'• Factura {estado}: <b>{invoice.name or invoice.id}</b>')
        msg.append(f'• Comisión registrada: <b>${self.commission_amount:,.2f}</b>')
        prop.message_post(body='<br/>'.join(msg))

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
