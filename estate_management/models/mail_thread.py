import html
import logging
import re
from markupsafe import Markup
from odoo import api, models

_logger = logging.getLogger(__name__)

HTML_TAG_REGEX = re.compile(r'<[a-zA-Z/][^>]*>')
ESCAPED_HTML_REGEX = re.compile(
    r'&lt;(?:b|strong|i|em|p|br|div|span|ul|ol|li|a)\b', re.IGNORECASE
)


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    @api.model
    def _register_hook(self):
        super()._register_hook()
        self._clean_legacy_escaped_messages()

    @api.model
    def _clean_legacy_escaped_messages(self):
        """Limpia notas y mensajes históricos en chatter que quedaron guardados

        con HTML escapado (&lt;b&gt;, &lt;br/&gt;, etc.) para que se muestren
        con su formato enriquecido en Odoo y en la app móvil.
        """
        try:
            self.env.cr.execute("""
                SELECT id, body FROM mail_message
                WHERE body LIKE '%&lt;b&gt;%'
                   OR body LIKE '%&lt;strong&gt;%'
                   OR body LIKE '%&lt;br/%'
                   OR body LIKE '%&lt;br&gt;%'
                   OR body LIKE '%&lt;p&gt;%'
                   OR body LIKE '%&lt;div%'
                   OR body LIKE '%&lt;/b&gt;%'
                   OR body LIKE '%&lt;/strong&gt;%'
                   OR body LIKE '%&lt;/p&gt;%'
                LIMIT 10000
            """)
            rows = self.env.cr.fetchall()
            if rows:
                _logger.info(
                    'Limpiando %d mensajes con HTML escapado en mail_message...',
                    len(rows),
                )
                for msg_id, raw_body in rows:
                    if raw_body:
                        cleaned = html.unescape(raw_body)
                        if '&lt;' in cleaned or '&gt;' in cleaned:
                            cleaned = html.unescape(cleaned)
                        self.env.cr.execute(
                            'UPDATE mail_message SET body = %s WHERE id = %s',
                            (cleaned, msg_id),
                        )
                _logger.info('Limpieza de mail_message completada exitosamente.')
        except Exception as e:
            _logger.warning(
                'No se pudo ejecutar la limpieza automática de mail_message: %s',
                e,
            )

    def message_post(self, *, body='', **kwargs):
        """Asegura que cualquier mensaje o nota que contenga etiquetas HTML

        se marque como Markup seguro. Esto evita que Odoo 19 lo escape a
        &lt;b&gt;...&lt;/b&gt; y se visualice como código HTML crudo.
        """
        if body and isinstance(body, str):
            if ESCAPED_HTML_REGEX.search(body):
                body = html.unescape(body)
                if '&lt;' in body or '&gt;' in body:
                    body = html.unescape(body)
            if HTML_TAG_REGEX.search(body):
                body = Markup(body)
        return super().message_post(body=body, **kwargs)
