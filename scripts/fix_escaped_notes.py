#!/usr/bin/env python3
"""Script para limpiar notas y mensajes en Odoo que tengan HTML escapado.

Puede ejecutarse en Odoo Shell:
docker compose run --rm odoo /opt/odoo-src/odoo-bin shell -c /etc/odoo/odoo.conf -d inmobi_produccion < scripts/fix_escaped_notes.py
"""
import html

cr = env.cr
cr.execute("""
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
""")
rows = cr.fetchall()
print(f"Mensajes encontrados con HTML escapado: {len(rows)}")

count = 0
for msg_id, raw_body in rows:
    if raw_body:
        cleaned = html.unescape(raw_body)
        if '&lt;' in cleaned or '&gt;' in cleaned:
            cleaned = html.unescape(cleaned)
        cr.execute("UPDATE mail_message SET body = %s WHERE id = %s", (cleaned, msg_id))
        count += 1

cr.commit()
print(f"Limpieza completada exitosamente: {count} mensajes actualizados.")
