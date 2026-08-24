# -*- coding: utf-8 -*-
"""Migración puntual: carga el celular del usuario Administrator si está
vacío, para que el recordatorio de WhatsApp de las citas pueda avisarle
como asesor. Se detectó el hueco porque `res.partner.mobile` del contacto
vinculado a `base.user_admin` estaba en blanco (probablemente porque el
número se cargó por error en OTRO contacto duplicado llamado igual
"Administrator", no en el que usa el sistema).

Corre una sola vez al actualizar el módulo a esta versión — no pisa el
valor si el asesor ya tiene un celular cargado (real o cambiado a mano
después de esta migración).
"""
import logging

_logger = logging.getLogger(__name__)

# Número real del asesor "Administrator" en producción, confirmado con el
# usuario — ver hilo de soporte sobre recordatorios de WhatsApp.
ADMIN_MOBILE = '0992555864'


def migrate(cr, version):
    cr.execute("""
        SELECT rp.id, rp.mobile
        FROM res_users ru
        JOIN res_partner rp ON rp.id = ru.partner_id
        JOIN ir_model_data imd ON imd.model = 'res.users' AND imd.res_id = ru.id
        WHERE imd.module = 'base' AND imd.name = 'user_admin'
    """)
    row = cr.fetchone()
    if not row:
        _logger.info(
            'Migración estate_calendar 19.0.1.0.1: no se encontró el usuario '
            'base.user_admin en esta base, no se aplica el ajuste de celular.'
        )
        return

    partner_id, mobile = row
    if mobile:
        _logger.info(
            'Migración estate_calendar 19.0.1.0.1: el contacto #%s ya tiene '
            'celular (%s), no se sobrescribe.', partner_id, mobile,
        )
        return

    cr.execute(
        "UPDATE res_partner SET mobile = %s WHERE id = %s",
        (ADMIN_MOBILE, partner_id),
    )
    _logger.info(
        'Migración estate_calendar 19.0.1.0.1: celular %s cargado al '
        'contacto #%s (Administrator) — antes estaba vacío.',
        ADMIN_MOBILE, partner_id,
    )
