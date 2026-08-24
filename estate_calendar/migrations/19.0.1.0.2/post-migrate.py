# -*- coding: utf-8 -*-
"""Corrige el intervalo del cron de recordatorios de WhatsApp.

El cron corría cada 30 minutos escaneando citas con `start >= now`. Si el
recordatorio configurado en la cita era corto (ej. 10 minutos) y el tick del
cron no caía justo dentro de esa ventana, la cita quedaba en el pasado antes
del siguiente tick y salía del filtro de búsqueda para siempre: el aviso
automático nunca se enviaba (solo funcionaba el botón manual). Ver hilo de
soporte sobre recordatorios de WhatsApp que no llegaban solos.

Baja el intervalo a 5 minutos solo si sigue en el valor por defecto (30) —
no pisa el intervalo si alguien ya lo personalizó a mano.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("""
        SELECT c.id, c.interval_number, c.interval_type
        FROM ir_cron c
        JOIN ir_model_data imd ON imd.model = 'ir.cron' AND imd.res_id = c.id
        WHERE imd.module = 'estate_calendar' AND imd.name = 'ir_cron_whatsapp_reminders'
    """)
    row = cr.fetchone()
    if not row:
        _logger.info(
            'Migración estate_calendar 19.0.1.0.2: no se encontró el cron '
            'de recordatorios WhatsApp en esta base, no se aplica el ajuste.'
        )
        return

    cron_id, interval_number, interval_type = row
    if not (interval_type == 'minutes' and interval_number == 30):
        _logger.info(
            'Migración estate_calendar 19.0.1.0.2: el cron #%s ya tiene un '
            'intervalo personalizado (%s %s), no se sobrescribe.',
            cron_id, interval_number, interval_type,
        )
        return

    cr.execute(
        "UPDATE ir_cron SET interval_number = 5, interval_type = 'minutes' WHERE id = %s",
        (cron_id,),
    )
    _logger.info(
        'Migración estate_calendar 19.0.1.0.2: cron #%s de recordatorios '
        'WhatsApp bajado de cada 30 min a cada 5 min, para no perder citas '
        'con recordatorio corto.', cron_id,
    )
