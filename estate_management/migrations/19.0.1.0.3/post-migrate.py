# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Los pagos que ya existían en Facturación (facturas de asesores pagadas y
    facturas de cobro pagadas) se marcan como inmobiliarios para que salgan en
    Facturación → Inmobiliaria. No se crea ningún asiento nuevo: lo que no
    tenga pago se registra desde "Registrar cobros y pagos anteriores"."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['estate.commission'].search([
        ('state', '=', 'paid'), ('payment_id', '=', False), ('invoice_id', '!=', False),
    ])._estate_link_existing_payments()
    for order in env['sale.order'].search([('estate_commission_collected', '=', True)]):
        if order.estate_collection_payment_ids:
            continue
        invoices = order.invoice_ids.filtered(
            lambda m: m.move_type == 'out_invoice' and m.state == 'posted')
        pays = invoices._get_reconciled_payments().filtered(lambda p: p.state != 'canceled')
        if pays:
            # Reutiliza la misma lógica que "Ver cobro": encuentra el pago y lo marca.
            order._estate_collection_payments()
