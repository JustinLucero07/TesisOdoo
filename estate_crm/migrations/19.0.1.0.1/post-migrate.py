# -*- coding: utf-8 -*-
"""Rellena el nombre de los leads que quedaron sin título.

El bot creaba leads con el nombre vacío y el autorrellenado no se aplicaba.
Solo toca los que están en blanco: usa el contacto vinculado o, si no hay, el
nombre de contacto escrito en el lead. Ningún nombre existente se cambia.
"""


def migrate(cr, version):
    cr.execute("""
        UPDATE crm_lead l
           SET name = COALESCE(NULLIF(btrim(p.name), ''), NULLIF(btrim(l.contact_name), ''))
          FROM crm_lead l2
          LEFT JOIN res_partner p ON p.id = l2.partner_id
         WHERE l.id = l2.id
           AND (l.name IS NULL OR btrim(l.name) = '')
           AND COALESCE(NULLIF(btrim(p.name), ''), NULLIF(btrim(l.contact_name), '')) IS NOT NULL
    """)
