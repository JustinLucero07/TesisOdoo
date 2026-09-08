# -*- coding: utf-8 -*-
"""La anticipación de los recordatorios pasó de 'días' fijos a valor + unidad.

Los recordatorios creados con la versión anterior guardaban `days_before`; se
traslada tal cual a (remind_value, 'days') para que sigan avisando igual.
"""


def migrate(cr, version):
    cr.execute("""
        SELECT column_name FROM information_schema.columns
         WHERE table_name = 'estate_reminder' AND column_name = 'days_before'
    """)
    if not cr.fetchone():
        return
    cr.execute("""
        UPDATE estate_reminder
           SET remind_value = COALESCE(days_before, 7),
               remind_unit = 'days'
         WHERE remind_unit IS NULL OR remind_value IS NULL
    """)
    cr.execute("ALTER TABLE estate_reminder DROP COLUMN days_before")
