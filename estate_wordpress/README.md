# estate_wordpress — Sincronización con WordPress / Houzez

Conecta Odoo con un sitio WordPress (típicamente con tema Houzez) para publicar propiedades y recibir leads desde formularios de contacto.

## Endpoints públicos

| Endpoint | Tipo | Propósito |
|---|---|---|
| `POST /estate_wordpress/lead/create` | JSONRPC | Crea lead desde WordPress/WhatsApp con token secreto. |
| `POST /estate_wordpress/webhook/contact` | JSONRPC | Webhook de formulario de contacto WP. |
| `POST /estate/wp/houzez/inquiry` | HTTP | Endpoint específico para Houzez `wp_remote_post()`. |

**Todos validan `estate_wp.webhook_secret`** vía body (`secret`) o header `X-WP-Secret`. Si el secret no está configurado, **rechazan la petición** (fail-closed).

## Modelos clave

| Modelo | Propósito |
|---|---|
| `estate.property` (extendido) | Adds: `wp_post_id`, `wp_published`, métodos `action_publish_wordpress` / `action_unpublish_wordpress`. |
| `estate.wordpress.config` | Configuración: URL, credenciales, tipo de post, mapping de campos. |
| `estate.wordpress.import.wizard` | Wizard para importar propiedades existentes desde WP. |

## Configuración necesaria
En *Ajustes → Redes Sociales → WordPress*:
- URL del sitio WP
- Usuario y App Password (o JWT token)
- Tipo de post (`property` por defecto en Houzez)
- `estate_wp.webhook_secret` (token que comparte con WP)

## Tests
`estate_wordpress/tests/` — 6 tests sobre validación de tokens (fail-closed, body, header).
