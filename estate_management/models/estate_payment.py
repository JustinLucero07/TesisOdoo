import logging
import requests

from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class EstatePayment(models.Model):
    _name = 'estate.payment'
    _description = 'Pago Inmobiliario'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(
        string='Referencia', readonly=True, copy=False,
        default='Nuevo')
    contract_id = fields.Many2one(
        'estate.contract', string='Contrato', required=True, tracking=True,
        ondelete='cascade')
    property_id = fields.Many2one(
        related='contract_id.property_id', string='Propiedad', store=True, readonly=True)
    partner_id = fields.Many2one(
        related='contract_id.partner_id', string='Cliente', store=True, readonly=True)

    amount = fields.Float(string='Monto', required=True, tracking=True)
    currency_id = fields.Many2one(
        'res.currency', string='Moneda',
        default=lambda self: self.env.company.currency_id)
    date = fields.Date(string='Fecha de Pago', required=True,
                       default=fields.Date.today, tracking=True)

    payment_method = fields.Selection([
        ('cash', 'Efectivo'),
        ('bank', 'Transferencia Bancaria'),
        ('check', 'Cheque'),
        ('card', 'Tarjeta'),
        ('other', 'Otro'),
    ], string='Método de Pago', default='bank', required=True)

    state = fields.Selection([
        ('pending', 'Pendiente'),
        ('paid', 'Pagado'),
        ('cancelled', 'Anulado'),
    ], string='Estado', default='pending', tracking=True, required=True)

    notes = fields.Text(string='Notas')

    # --- Integración con Facturación ---
    invoice_id = fields.Many2one(
        'account.move', string='Factura', readonly=True, copy=False,
        help='Factura generada desde este pago.')
    invoice_state = fields.Selection(
        related='invoice_id.payment_state', string='Estado Factura', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code('estate.payment') or 'Nuevo'
        return super().create(vals_list)

    def action_confirm(self):
        for rec in self:
            if rec.state != 'pending':
                raise UserError('Solo se pueden confirmar pagos en estado Pendiente.')
            rec.state = 'paid'

    def action_cancel(self):
        for rec in self:
            if rec.state == 'paid':
                raise UserError('No se puede anular un pago ya confirmado. Cree una nota de crédito.')
            rec.state = 'cancelled'

    def action_reset(self):
        for rec in self:
            if rec.state != 'cancelled':
                raise UserError('Solo se pueden restablecer pagos anulados.')
            rec.state = 'pending'

    def action_create_invoice(self):
        """Genera una factura de cliente (account.move) desde este pago."""
        self.ensure_one()
        if self.invoice_id:
            # Ya tiene factura → abrirla directamente
            return {
                'type': 'ir.actions.act_window',
                'name': 'Factura',
                'res_model': 'account.move',
                'view_mode': 'form',
                'res_id': self.invoice_id.id,
            }
        if not self.partner_id:
            raise UserError('Este pago no tiene cliente asignado. Asegúrese de que el contrato tenga un cliente.')

        contract_type = self.contract_id.contract_type if self.contract_id else 'other'
        if contract_type == 'rent':
            line_name = f'Cuota de alquiler: {self.contract_id.name} ({self.date})'
            tx_type = 'rent'
        elif contract_type == 'sale':
            line_name = f'Pago compraventa: {self.contract_id.name} ({self.date})'
            tx_type = 'sale'
        else:
            line_name = f'Honorarios / Gestión: {self.contract_id.name} ({self.date})'
            tx_type = 'commission'

        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_origin': self.name,
            'invoice_line_ids': [(0, 0, {
                'name': line_name,
                'quantity': 1,
                'price_unit': self.amount,
            })],
        }
        # Heredar property_id y transaction_type si el modelo lo tiene
        if hasattr(self.env['account.move'], 'property_id') and self.property_id:
            invoice_vals['property_id'] = self.property_id.id
        if hasattr(self.env['account.move'], 'estate_transaction_type'):
            invoice_vals['estate_transaction_type'] = tx_type

        invoice = self.env['account.move'].create(invoice_vals)
        self.write({'invoice_id': invoice.id})

        return {
            'type': 'ir.actions.act_window',
            'name': 'Factura Generada',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': invoice.id,
            'target': 'current',
        }

    def _clean_phone(self, phone):
        """Normaliza número a formato internacional sin + (ej: 593981112222)."""
        clean = phone.replace(' ', '').replace('-', '').replace('+', '').replace('(', '').replace(')', '')
        if clean.startswith('0') and len(clean) == 10:
            clean = '593' + clean[1:]
        elif not clean.startswith('593'):
            clean = '593' + clean
        return clean

    def _send_whatsapp_overdue(self, phone, payment, days_late):
        """Envía alerta WhatsApp via Meta Cloud API para pago vencido."""
        ICP = self.env['ir.config_parameter'].sudo()
        phone_number_id = ICP.get_param('estate_calendar.whatsapp_phone_number_id', '')
        access_token = ICP.get_param('estate_calendar.whatsapp_access_token', '')

        if not phone_number_id or not access_token or not phone:
            return False

        clean_phone = self._clean_phone(phone)
        url = f'https://graph.facebook.com/v19.0/{phone_number_id}/messages'
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        }

        message = (
            f"PAGO VENCIDO — Sistema Inmobiliario\n"
            f"Referencia: {payment.name}\n"
            f"Cliente: {payment.partner_id.name or 'Sin cliente'}\n"
            f"Contrato: {payment.contract_id.name}\n"
            f"Monto: ${payment.amount:,.2f}\n"
            f"Vencido hace {days_late} dia(s) ({payment.date})\n"
            f"Por favor gestionar cobro."
        )
        payload = {
            'messaging_product': 'whatsapp',
            'to': clean_phone,
            'type': 'text',
            'text': {'body': message},
        }

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            data = resp.json()
            if resp.status_code == 200 and data.get('messages'):
                _logger.info("WhatsApp enviado a %s por pago vencido %s", clean_phone, payment.name)
                return True
            _logger.warning("WhatsApp falló (%s): %s", resp.status_code, resp.text[:300])
        except Exception as e:
            _logger.error("Error enviando WhatsApp de pago vencido: %s", e)
        return False

    @api.model
    def _cron_check_overdue_payments(self):
        """Detecta pagos pendientes con fecha vencida, crea actividades y envía WhatsApp (≥3 días)."""
        today = fields.Date.today()
        overdue = self.search([
            ('state', '=', 'pending'),
            ('date', '<', today),
        ])
        for payment in overdue:
            existing = self.env['mail.activity'].search([
                ('res_model', '=', 'estate.payment'),
                ('res_id', '=', payment.id),
                ('summary', 'ilike', 'pago vencido'),
            ], limit=1)
            days_late = (today - payment.date).days
            responsible = (
                payment.contract_id.user_id
                or payment.property_id.user_id
                or self.env.user
            )
            if not existing:
                payment.activity_schedule(
                    'mail.mail_activity_data_todo',
                    date_deadline=today,
                    summary=f'💸 Pago vencido hace {days_late} día(s)',
                    note=(
                        f'El pago <strong>{payment.name}</strong> por '
                        f'${payment.amount:,.2f} del contrato '
                        f'"{payment.contract_id.name}" venció el {payment.date}. '
                        f'Cliente: {payment.partner_id.name or "Sin cliente"}.'
                    ),
                    user_id=responsible.id,
                )

            # WhatsApp al asesor responsable si el pago lleva 3+ días vencido
            if days_late >= 3:
                agent_phone = (
                    responsible.partner_id.mobile
                    or responsible.partner_id.phone
                    or ''
                )
                self._send_whatsapp_overdue(agent_phone, payment, days_late)
