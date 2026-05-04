# estate_crm — CRM Inmobiliario

Extiende el CRM estándar de Odoo (`crm.lead`) con lógica de matchmaking propiedad↔lead, scoring inteligente, captación multi-canal y deduplicación de webhooks.

## Modelos clave

| Modelo | Propósito |
|---|---|
| `crm.lead` (extendido) | Adds: `target_property_id`, `client_budget`, `match_percentage`, `lead_score`, `lead_temperature`, `closing_difficulty`, `smart_negotiation_tips`, `lead_velocity_days`, etc. |
| `estate.property` (extendido) | Adds: `lead_count` y vínculos. |
| `estate.client.interaction` | Bitácora de interacciones con clientes (visitas, llamadas, emails). |
| `estate.property.match` | Cruces propiedad↔lead generados por el matchmaker. |
| `estate.meta.webhook.event` | **Tabla de idempotencia** para webhooks de Meta (UNIQUE en `event_id`). |

## Características destacadas
- **Matchmaking automático**: compute `_compute_match_percentage` evalúa presupuesto (50%), ciudad (20%), tipo (20%), habitaciones (10%).
- **Lead temperature**: `cold/warm/hot/boiling` basado en actividad reciente.
- **Crons inteligentes** (todos optimizados sin N+1):
  - `_cron_proactive_matchmaking`: notifica al asesor cuando aparece propiedad acorde al lead
  - `_cron_drip_followup`: actividades automáticas a los 2/7/14 días
  - `_cron_hot_lead_no_response_alert`: alerta si lead hirviendo lleva 48h sin actividad
  - `_cron_cool_down_inactive_leads`: degrada temperatura tras 14 días sin contacto
- **Webhooks Meta** (`/meta/webhook`): WhatsApp + Facebook Messenger + Instagram DMs con deduplicación por `event_id`.

## Configuración necesaria
- `estate_crm.meta_verify_token` en *Ajustes → Parámetros del Sistema* (token que Meta usa para verificar el webhook).

## Tests
`estate_crm/tests/` — 30 tests: matching, scoring, dedup, negotiation strategy.

```bash
python odoo-bin -c odoo19.conf -d tesis_odoo19 \
  --test-enable --stop-after-init -u estate_crm
```
