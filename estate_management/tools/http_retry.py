"""Utilidades de reintento exponencial para llamadas HTTP a servicios externos.

Uso típico:

    from odoo.addons.estate_management.tools.http_retry import request_with_retry

    resp = request_with_retry(
        'GET',
        'https://graph.facebook.com/v25.0/...',
        params={'access_token': token},
        timeout=15,
    )

Reintentos automáticos para errores transitorios (5xx, 429, conexión, timeout).
NO reintenta para errores 4xx (cliente) excepto 429.
"""
import logging
import time

import requests

_logger = logging.getLogger(__name__)

# Códigos HTTP transitorios donde reintentar tiene sentido
TRANSIENT_STATUS = {408, 429, 500, 502, 503, 504}


def request_with_retry(method, url, retries=3, backoff=1.5, **kwargs):
    """Ejecuta requests.request con reintento exponencial.

    Args:
        method: 'GET', 'POST', etc.
        url: URL de destino.
        retries: número total de intentos (incluyendo el primero). Default 3.
        backoff: multiplicador del tiempo de espera. tiempo = backoff ** intento.
        **kwargs: pasados directamente a requests.request (params, data, json, headers, timeout).

    Returns:
        requests.Response del intento exitoso, o el último Response si todos fallaron.

    Raises:
        requests.RequestException si todos los intentos fallan por excepción de red.
    """
    if 'timeout' not in kwargs:
        kwargs['timeout'] = 15

    last_exc = None
    last_resp = None

    for attempt in range(retries):
        try:
            resp = requests.request(method, url, **kwargs)
            last_resp = resp
            # 2xx / 3xx / 4xx no transitorio → devolver
            if resp.status_code not in TRANSIENT_STATUS:
                return resp
            # Transitorio → loguear y reintentar
            _logger.warning(
                'HTTP %s %s — %d (intento %d/%d). Reintentando...',
                method, url, resp.status_code, attempt + 1, retries)
        except (requests.Timeout, requests.ConnectionError) as e:
            last_exc = e
            _logger.warning(
                'HTTP %s %s — error de red: %s (intento %d/%d)',
                method, url, e, attempt + 1, retries)

        # Espera exponencial antes del siguiente intento (no después del último)
        if attempt < retries - 1:
            wait = backoff ** (attempt + 1)
            time.sleep(wait)

    # Agotados los reintentos
    if last_resp is not None:
        return last_resp
    if last_exc is not None:
        raise last_exc
    raise requests.RequestException(f'Falló {url} tras {retries} intentos')
