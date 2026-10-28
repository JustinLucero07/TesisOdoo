# -*- coding: utf-8 -*-
"""Opciones de factura para cobros (propietario) y pagos (asesores)."""

INVOICE_MODES = [
    ('with', 'Con factura 15%'),
    ('with_incl', 'Con factura 15% (IVA incluido)'),
    ('with_0', 'Con factura 0%'),
    ('without', 'Sin factura'),
]

# Porcentaje de IVA de cada opción con factura.
VAT_RATE = {'with': 15.0, 'with_incl': 15.0, 'with_0': 0.0}

# IVA incluido: el monto no cambia, se desglosa el IVA de adentro
# (ej. 3.000 = 2.608,70 + 391,30 de IVA).
VAT_INCLUDED = {'with_incl'}


def is_invoiced(mode):
    return mode in VAT_RATE


def split_amounts(amount, mode):
    """(base sin IVA, IVA, total) de `amount` según la opción elegida."""
    amount = round(amount or 0.0, 2)
    rate = VAT_RATE.get(mode, 0.0) / 100.0
    if mode in VAT_INCLUDED:
        base = round(amount / (1.0 + rate), 2)
        return base, round(amount - base, 2), amount
    vat = round(amount * rate, 2)
    return amount, vat, round(amount + vat, 2)


def vat_amount(base, mode):
    """IVA que corresponde a `base` según la opción elegida."""
    return split_amounts(base, mode)[1]


def find_tax(env, use, mode, company=None):
    """Impuesto de Odoo para la opción (`use` = 'sale' o 'purchase').
    Para 0% devuelve el impuesto 0% si existe; si no, ninguno (línea sin IVA).
    Para IVA incluido usa (o crea) el 15% con el precio con impuesto incluido."""
    if not is_invoiced(mode):
        return env['account.tax']
    company = company or env.company
    Tax = env['account.tax']
    domain = [('type_tax_use', '=', use), ('amount_type', '=', 'percent'),
              ('amount', '=', VAT_RATE[mode])]
    included = mode in VAT_INCLUDED
    candidates = (Tax.search(domain + [('company_id', 'in', (company.id, False))])
                  or Tax.search(domain))
    tax = candidates.filtered(lambda t: bool(t.price_include) == included)[:1]
    if tax or not included:
        return tax
    base_tax = candidates[:1]
    if not base_tax:
        return Tax
    return base_tax.sudo().copy({
        'name': '%s (IVA incluido)' % base_tax.name,
        'price_include_override': 'tax_included',
    })


def payment_journal(env, method, company=None):
    """Diario de banco o caja según la forma de pago."""
    company = company or env.company
    Journal = env['account.journal']
    jtype = 'cash' if method == 'cash' else 'bank'
    return (Journal.search([('type', '=', jtype), ('company_id', '=', company.id)], limit=1)
            or Journal.search([('type', 'in', ('bank', 'cash')), ('company_id', '=', company.id)], limit=1))
