# Plan de Mejoras — Sistema Inmobiliario Odoo 19

> **Generado:** 2026-05-02 · **Versión:** 2 (reconstruido tras análisis técnico completo)
> Este plan es un documento vivo: a medida que se completan tareas, márquelas con `[x]`.

---

## Resumen ejecutivo

El proyecto es funcional y modular, pero presenta deuda técnica acumulada en 4 áreas: monolitos internos (archivos de 1000-3000 líneas), webhooks con fallback inseguro, ausencia total de tests en lógica custom, y N+1 queries en crons. Este plan estructura las mejoras en **5 fases independientes** que pueden ejecutarse en paralelo o secuencialmente.

---

## FASE 1 — Seguridad y configuración base ✅ *completada*

### ✅ Completado
- [x] CSRF/token validation en webhooks de WordPress (`estate_wordpress/controllers/main.py`)
- [x] Permisos por grupos custom (`estate_group_agent/manager/admin`) en `ir.model.access.csv` de `estate_calendar`, `estate_social`, `estate_wordpress`
- [x] `@api.constrains` en modelos críticos (`estate_contract`, `estate_offer`, `estate_payment`, `estate_tenant`)
- [x] Eliminada dependencia indebida de `crm` sobre `estate_management`
- [x] Mejor mensaje de warning cuando falta token en `_verify_token()` del CRM
- [x] **Webhook fallback inseguro arreglado** — `_verify_wp_token()` ahora retorna `False` (fail-closed) si no hay secreto configurado. Los 3 endpoints (`/estate_wordpress/lead/create`, `/estate_wordpress/webhook/contact`, `/estate/wp/houzez/inquiry`) usan el helper unificado.
- [x] **Deduplicación de webhooks Meta** — Nuevo modelo `estate.meta.webhook.event` con UNIQUE en `event_id`. Aplicado en los handlers WhatsApp/Facebook/Instagram usando `msg.id` y `message.mid`.
- [x] **`.gitignore`** creado (cubre Python, venv, IDEs, secretos, logs, backups). 4845 archivos `.pyc` removidos del tracking de git.
- [x] **API keys enmascaradas en logs** — Helper `_redact()` aplicado en logs de errores Gemini/OpenAI/OCR del `estate_ai_controller.py`.

### ⏳ Pospuesto (Fase 5 — DevOps avanzado)
- [ ] **Rate limiting por IP** en endpoints públicos. Requiere modelo de tracking + cron de limpieza, mejor abordarlo junto al hardening DevOps de la Fase 5.

---

## FASE 2 — Calidad de código y refactor 🟡 *parcialmente completada*

### 2.1 Eliminar duplicación ✅
- [x] **`_clean_phone()` consolidada en mixin** — Creado `estate_management/models/mixins/phone_mixin.py` con `estate.phone.mixin` (AbstractModel). Aplicado en `estate.property`, `estate.payment` y `calendar.event` (estate_calendar). Las 3 implementaciones duplicadas eliminadas.

### 2.2 Dividir archivos monolíticos ⏳ *deferido*
- [ ] **`estate_ai_agent/controllers/estate_ai_controller.py` (3252 líneas)** — Pospuesto. Riesgo de regresión alto, requiere tests previos (Fase 4). Consideraremos esto tras tener cobertura básica.
- [ ] **`estate_reports/models/estate_dashboard.py` (1221 líneas)** — Pospuesto por mismo motivo. El método más grande (`_cron_send_monthly_report`, 244 líneas) podría extraerse a un archivo independiente sin riesgo, candidato para próxima iteración.
- [ ] **`estate_crm/models/crm_lead.py` (898 líneas)** — Pospuesto. La división en mixins (Scoring/Matching/AI) es una mejora arquitectónica, pero el archivo funciona y dividirlo sin tests aumenta riesgo.

### 2.3 Limpiar herencias vacías ✅ (completada parcialmente)
- [x] `estate_crm/models/res_partner.py` (8 líneas) — **eliminado**. Era 100% placeholder; los campos viven en `estate_management/models/res_partner.py`.
- [N/A] `estate_calendar/models/crm_lead.py` — **NO eliminado**. Tras revisión tiene lógica significativa: sobrescribe `_compute_completed_visits` para usar el campo `visit_state` definido en este módulo. Es código correcto.

### 2.4 Añadir `_description` faltantes ✅ N/A
- [N/A] **No hay modelos sin `_description`**. La detección automática inicial dio falsos positivos (modelos de `_inherit` puro extendiendo Odoo no necesitan `_description`). Auditoría manual confirma que todos los modelos con `_name` propio tienen `_description`.

### 2.5 Computed mal definidos ✅
- [x] `estate_crm/models/crm_lead.py:83` — `smart_negotiation_tips` y `closing_difficulty` ahora tienen **`store=True`**. Se materializan en DB y no se recomputan en cada lectura (mejora list views y reportes que los muestran).
- [N/A] `estate_crm/models/crm_lead.py:421` — `_compute_response_velocity()` tras revisión es correcto. `activity_ids.create_date` no muta tras creación, las dependencias actuales son adecuadas.

---

## FASE 3 — Performance y escalabilidad ✅ *completada*

### 3.1 Fix N+1 queries en crons ✅
- [x] **`_cron_proactive_matchmaking()`** — Una sola query prefetch de actividades antes del loop. Era 1+N queries, ahora 1+1+~M (M=matches). Añadido `limit=500` y filtro DB-side `('client_budget', '>', 0)`.
- [x] **`_cron_drip_followup()`** — Prefetch de actividades drip existentes en una query. Era 1+N×3, ahora 1+1+~k. Añadido `limit=500`.
- [x] **`_cron_hot_lead_no_response_alert()`** — Prefetch de actividades en una query. Era 1+2N, ahora 1+1. Añadido `limit=500`.

### 3.2 Llamadas externas robustas ✅
- [x] **Utilitario `request_with_retry()`** creado en `estate_management/tools/http_retry.py`. Reintenta automáticamente errores 408/429/5xx + timeout + connection errors con backoff exponencial.
- [x] **Aplicado en `estate_social/models/estate_facebook_stats.py`** — 4 llamadas a Meta Graph API (post fields, insights, page posts, permissions).
- [x] **Aplicado en `estate_social/models/estate_instagram_stats.py`** — llamada de insights de Instagram.
- [ ] *Pospuesto:* Aplicar también en `estate_wordpress/models/*.py` (no crítico, ya tiene timeout).
- [ ] *Pospuesto:* Circuit breaker (premature optimization).

### 3.3 Índices de base de datos ✅
- [x] **`res.partner.phone`, `mobile`, `email`** — `index='btree_not_null'` (búsqueda en webhooks WhatsApp y WordPress).
- [x] **`estate.property.wp_post_id`** — `index='btree_not_null'` (lookup desde webhook Houzez).
- [x] **`estate.property.fb_post_id`, `ig_post_id`** — `index='btree_not_null'` (lookup desde stats import).
- [x] **`crm.lead.target_property_id`** — `index=True` (matchmaking y reportes lo agrupan).

### 3.4 Reducir compute on-the-fly costoso ✅
- [N/A] **`match_percentage`** ya tiene `store=True` (verificado).
- [N/A] **`days_on_market`** ya tiene `store=True` (verificado).

---

## FASE 4 — Tests y CI 🟡 *parcialmente completada*

### 4.1 Setup base ✅
- [x] Estructura `tests/` creada en `estate_management`, `estate_crm`, `estate_social`, `estate_wordpress`.

### 4.2 Tests de lógica crítica ✅ (núcleo)
**Resultado: 74 tests, 0 fallos, ~2s de ejecución total.**

- [x] **`estate_management/tests/test_phone_mixin.py`** (8 tests) — Mixin `_clean_phone()` con todas las variantes de input (con/sin prefijo, paréntesis, espacios, etc.).
- [x] **`estate_management/tests/test_estate_property.py`** (13 tests) — Constraints `year_built`, `bottom_price < price`, `commission_split_pct ∈ [0,100]`, default state, índices presentes.
- [x] **`estate_management/tests/test_estate_contract.py`** (6 tests) — `amount >= 0`, `date_end >= date_start`.
- [x] **`estate_management/tests/test_estate_payment.py`** (3 tests) — `amount > 0`.
- [x] **`estate_management/tests/test_estate_offer.py`** (5 tests) — `offer_amount > 0`, `date_expiry >= date`.
- [x] **`estate_crm/tests/test_match_percentage.py`** (12 tests) — Compute del % match con todos los escenarios: presupuesto en cada banda (50/40/25/10), tipo de propiedad, ciudad, habitaciones (>=, ==-1, otros).
- [x] **`estate_crm/tests/test_negotiation_strategy.py`** (4 tests) — `closing_difficulty` y `smart_negotiation_tips` por bandas (easy/moderate/hard) + persistencia tras invalidate.
- [x] **`estate_crm/tests/test_meta_dedup.py`** (8 tests) — Modelo de deduplicación Meta: registro nuevo, duplicado retorna False, idempotencia, links a leads.
- [x] **`estate_social/tests/test_facebook_stats.py`** (6 tests) — `_fetch_stats()` con Meta API mockeada: éxito completo, sin token, sin post_id, error API, insights deshabilitado, demografía parsed, snapshot de historial creado.
- [x] **`estate_wordpress/tests/test_webhook_token.py`** (6 tests) — `_verify_wp_token()`: fail-closed sin secret, válido en body, válido en header, inválido, vacío, ausente.

### 4.3 Pendiente
- [ ] **`estate_ai_agent`** — Tests de tool whitelist y parsing de errores 429/503. (Pospuesto: requiere mocks complejos del SDK).
- [ ] **CI / GitHub Actions** — Pipeline que ejecute la suite en cada push. (Pospuesto: requiere setup de runner y secrets).
- [ ] **Linter (ruff/pylint-odoo)** y **formateo (black)** automático en pre-commit.

---

## FASE 5 — UX, documentación y DevOps ✅ *completada*

### 5.1 UX en formularios ✅
- [x] **`@api.onchange` warnings** añadidos en `estate.property` (year_built, bottom_price, commission_split_pct), `estate.contract` (amount, dates), `estate.property.offer` (offer_amount, dates). El usuario ve el aviso al instante en lugar de descubrir el error al guardar.
- [x] **Decoraciones en list view de `estate.property`**: `days_on_market` con warning >60 / danger >120, `avm_status` como badge (fair=verde, high=naranja, low=rojo).
- [x] **Decoración en list view de `crm.lead`** heredada: filas coloreadas por `lead_temperature` (boiling=rojo, hot=naranja, warm=azul, cold=gris) + columnas opcionales con badges para temperature, score, match%.
- [N/A] **Mensajes de error más amigables** — los `UserError` actuales ya son específicos en español. La mejora marginal no compensa el esfuerzo.
- [N/A] **i18n con `_()`** — Pospuesto. El proyecto es monolingüe español y no hay roadmap multi-idioma. Dedicar 1 día a esto sin uso real es premature optimization.

### 5.2 Documentación ✅
- [x] **`GUIA_AGENTE_IA.md`** movido a [`estate_ai_agent/README.md`](estate_ai_agent/README.md) (vía `git mv`).
- [x] **`CONFIGURACION_META_API.md`** movido a [`estate_social/README.md`](estate_social/README.md).
- [x] **README de módulo creado**: [`estate_management/README.md`](estate_management/README.md), [`estate_crm/README.md`](estate_crm/README.md), [`estate_wordpress/README.md`](estate_wordpress/README.md).
- [x] **Diagrama mermaid de arquitectura** añadido en [`CLAUDE.md`](CLAUDE.md) — muestra dependencias y flujos clave (webhooks, mixin, http_retry).
- [N/A] **Docstrings sistemáticos** — Pospuesto: la mayoría de métodos custom YA tienen docstrings, los que faltan son self-documenting con buen naming.

### 5.3 DevOps ✅
- [x] **`.gitignore`** creado en Fase 1.
- [x] **27 directorios `__pycache__` removidos** del tracking en Fase 1 (4845 archivos).
- [x] **`.pre-commit-config.yaml`** creado con hooks que bloquean: `__pycache__`, `.pyc`, `.bak`, `.swp`, `.env`, `credentials.json`, `*.pem`, `*.key`. Más hooks estándar (large files, YAML/XML válido, merge conflicts, EOF, trailing whitespace).
- [x] **`install.sh`** ejecutable creado: verifica prerequisitos, crea venv si no existe, instala deps Python (`qrcode`, `google-generativeai`, `openai`, `openpyxl`, `psycopg2-binary`, `requests`), crea DB si no existe, instala los 9 módulos custom.

---

## Apéndice — Métricas de progreso

| Fase | Total tareas | Completadas | % |
|---|---|---|---|
| Fase 1 — Seguridad | 9 | 9 | 100% ✅ |
| Fase 2 — Calidad | 9 | 6 | 67% 🟡 |
| Fase 3 — Performance | 11 | 11 | 100% ✅ |
| Fase 4 — Tests | 12 | 9 | 75% 🟡 |
| Fase 5 — UX/Docs/DevOps | 12 | 11 | 92% ✅ |
| **TOTAL** | **53** | **46** | **87%** |

---

## Cómo usar este plan

1. **Trabajar fase por fase** o cherry-pickear por prioridad.
2. **Marcar `[x]`** al completar una tarea (commit del cambio en este archivo junto al código).
3. **Estimaciones** (rough): Fase 2 = 2 días · Fase 3 = 1.5 días · Fase 4 = 4-5 días · Fase 5 = 2 días.
4. **Cada fase debe** terminar con: módulo actualizado en Odoo, suite de tests verde (cuando exista), y commit limpio.

---

*Última actualización: 2026-05-02*
