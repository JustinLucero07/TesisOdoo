# -*- coding: utf-8 -*-
"""Opciones de factura para cobros (propietario) y pagos (asesores)."""

INVOICE_MODES = [
    ('with', 'Con factura 15%'),
    ('with_0', 'Con factura 0%'),
    ('without', 'Sin factura'),
]

# Porcentaje de IVA de cada opción con factura.
VAT_RATE = {'with': 15.0, 'with_0': 0.0}


def is_invoiced(mode):
    return mode in VAT_RATE


def vat_amount(base, mode):
    """IVA que corresponde a `base` según la opción elegida."""
    return round((base or 0.0) * VAT_RATE.get(mode, 0.0) / 100.0, 2)


def find_tax(env, use, mode, company=None):
    """Impuesto de Odoo para la opción (`use` = 'sale' o 'purchase').
    Para 0% devuelve el impuesto 0% si existe; si no, ninguno (línea sin IVA)."""
    if not is_invoiced(mode):
        return env['account.tax']
    company = company or env.company
    Tax = env['account.tax']
    domain = [('type_tax_use', '=', use), ('amount_type', '=', 'percent'),
              ('amount', '=', VAT_RATE[mode])]
    return (Tax.search(domain + [('company_id', 'in', (company.id, False))], limit=1)
            or Tax.search(domain, limit=1))


def payment_journal(env, method, company=None):
    """Diario de banco o caja según la forma de pago."""
    company = company or env.company
    Journal = env['account.journal']
    jtype = 'cash' if method == 'cash' else 'bank'
    return (Journal.search([('type', '=', jtype), ('company_id', '=', company.id)], limit=1)
            or Journal.search([('type', 'in', ('bank', 'cash')), ('company_id', '=', company.id)], limit=1))
