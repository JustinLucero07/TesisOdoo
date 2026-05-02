from odoo import models


class EstatePhoneMixin(models.AbstractModel):
    """Mixin con utilidades para normalización de números telefónicos a formato
    internacional E.164 sin '+' (formato esperado por Meta Cloud API).

    Uso: heredar en el modelo donde se necesite y llamar a `self._clean_phone(p)`.
    """
    _name = 'estate.phone.mixin'
    _description = 'Mixin de Utilidades de Teléfono'

    @staticmethod
    def _clean_phone(phone):
        """Normaliza número a formato internacional sin + (ej: '+593 98 111 2222' → '593981112222').

        Reglas:
          - Elimina espacios, guiones, paréntesis y signo +.
          - Si empieza con 0 y tiene 10 dígitos (formato local Ecuador), reemplaza el 0 por 593.
          - Si no empieza con 593, antepone 593 (asume número ecuatoriano).
        """
        if not phone:
            return ''
        clean = phone.replace(' ', '').replace('-', '').replace('+', '').replace('(', '').replace(')', '')
        if clean.startswith('0') and len(clean) == 10:
            clean = '593' + clean[1:]
        elif not clean.startswith('593'):
            clean = '593' + clean
        return clean
