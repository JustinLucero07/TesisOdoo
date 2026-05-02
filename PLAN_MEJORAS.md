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

## FASE 3 — Performance y escalabilidad

### 3.1 Fix N+1 queries en crons
- [ ] **`estate_crm/models/crm_lead.py:701-733` — `_cron_proactive_matchmaking()`:**
  - Hace `mail.activity.search([...])` dentro de loop sobre leads (líneas 720, 777, 805, 811, 842).
  - **Solución:** prefetch con `read_group` o `mapped` antes del loop. Estimación: 10x speedup en bases con 1000+ leads.
- [ ] **Añadir `limit=500` y procesamiento por batches** a `_cron_proactive_matchmaking()` (línea 700, ahora sin límite).
- [ ] Auditar todos los crons (`grep -rn "_cron_" estate_*/models/`) por patrones similares.

### 3.2 Llamadas externas robustas
- [ ] **Añadir reintentos exponenciales** a las integraciones HTTP:
  - `estate_social/models/estate_facebook_stats.py` (Meta API)
  - `estate_social/models/estate_instagram_stats.py` (Meta API)
  - `estate_wordpress/models/estate_wordpress_*.py` (WP REST API)
  - `estate_ai_agent/controllers/estate_ai_controller.py` (Gemini/OpenAI)
- [ ] **Crear utilitario** `estate_management/tools/http_retry.py` con decorador `@retry_on_transient(retries=3, backoff=2)`.
- [ ] **Circuit breaker** opcional: si una API falla N veces en M minutos, suspender llamadas durante T minutos.

### 3.3 Índices de base de datos
- [ ] Añadir índices en campos de búsqueda frecuente:
  - `res.partner.phone` (lookup por webhooks WhatsApp)
  - `res.partner.email`
  - `estate.property.fb_post_id`
  - `estate.property.wp_post_id`
  - `crm.lead.target_property_id`
- [ ] Implementación: `index='btree'` en la definición del campo (Odoo 19 syntax).

### 3.4 Reducir compute on-the-fly costoso
- [ ] Evaluar si `match_percentage` en `crm.lead` merece `store=True` (se calcula en cada read).
- [ ] Lo mismo con `days_on_market` en `estate.property`.

---

## FASE 4 — Tests y CI

### 4.1 Setup base
- [ ] Crear estructura `tests/` en cada módulo custom:
  ```
  estate_<modulo>/tests/
    __init__.py
    test_<feature>.py
  ```
- [ ] Helpers comunes: factory para crear `estate.property`, `crm.lead`, etc.

### 4.2 Tests de lógica crítica (en orden de impacto)
- [ ] **`estate_crm`** — matchmaking lead↔property con diferentes presupuestos, score A/B/C, temperatura de lead.
- [ ] **`estate_management`** — state machine de propiedad (available → reserved → sold/rented), constraints de fechas/montos.
- [ ] **`estate_wordpress`** — sync bidireccional, mapping de campos, manejo de `wp_post_id` duplicados.
- [ ] **`estate_social`** — `_fetch_stats` con respuestas mockeadas de Meta (success, error de permisos, token expirado).
- [ ] **`estate_ai_agent`** — tool calling (whitelist), parsing de errores 429/503, fallback Gemini→OpenAI.
- [ ] **Webhooks** — `/meta/webhook`, `/estate_wordpress/lead/create` con tokens válidos/inválidos, payloads malformados.

### 4.3 CI
- [ ] GitHub Actions / pre-commit con:
  - Ejecutar tests Odoo (`--test-enable`)
  - Linter (`pylint-odoo` o `ruff`)
  - Formateo (`black`)

---

## FASE 5 — UX, documentación y DevOps

### 5.1 UX en formularios
- [ ] **`@api.onchange`** complementarios a `@api.constrains` para warning previo al guardar (ej: precio, año de construcción).
- [ ] **Estados visuales en list views** — decoraciones por `lead_temperature`, `avm_status`, `state` de propiedad.
- [ ] **Mensajes de error más amigables** en `UserError` — incluir sugerencia de acción.
- [ ] **Internacionalización** — wrap todos los `string=`, `raise UserError(...)`, `message_post(body=...)` con `_()` para preparar i18n.

### 5.2 Documentación
- [ ] **README.md por módulo** con: propósito, dependencias, modelos clave, hooks, configuración necesaria.
- [ ] **Consolidar `.md` raíz**:
  - `README.md` (406 líneas) — overview ejecutivo, install, quickstart
  - `INTEGRACIONES.md` (318) — mover dentro de cada módulo respectivo
  - `GUIA_AGENTE_IA.md` (317) → `estate_ai_agent/README.md`
  - `CONFIGURACION_META_API.md` (246) → `estate_social/README.md`
  - `GUIA_FUNCIONALIDADES.md` (244) — fusionar en README principal o eliminar
- [ ] **Docstrings** en todos los métodos públicos de modelos custom (estilo Google/Sphinx).
- [ ] **Diagrama de arquitectura** (mermaid en CLAUDE.md o README) — flujo de datos entre módulos.

### 5.3 DevOps
- [ ] **`.gitignore`** estándar Python + Odoo:
  ```
  __pycache__/
  *.pyc
  *.pyo
  .vscode/
  .idea/
  *.log
  .env
  venv*/
  ```
- [ ] Limpiar 27 directorios `__pycache__` versionados:
  ```bash
  find . -type d -name __pycache__ -exec git rm -r --cached {} +
  ```
- [ ] **Pre-commit hook** que impida volver a commitear `__pycache__`, `.pyc`, archivos `.bak`.
- [ ] **Script de instalación reproducible** (`install.sh`) que cree venv, instale deps, configure DB.

---

## Apéndice — Métricas de progreso

| Fase | Total tareas | Completadas | % |
|---|---|---|---|
| Fase 1 — Seguridad | 9 | 9 | 100% ✅ |
| Fase 2 — Calidad | 9 | 6 | 67% 🟡 |
| Fase 3 — Performance | 9 | 0 | 0% |
| Fase 4 — Tests | 9 | 0 | 0% |
| Fase 5 — UX/Docs/DevOps | 12 | 0 | 0% |
| **TOTAL** | **48** | **15** | **31%** |

---

## Cómo usar este plan

1. **Trabajar fase por fase** o cherry-pickear por prioridad.
2. **Marcar `[x]`** al completar una tarea (commit del cambio en este archivo junto al código).
3. **Estimaciones** (rough): Fase 2 = 2 días · Fase 3 = 1.5 días · Fase 4 = 4-5 días · Fase 5 = 2 días.
4. **Cada fase debe** terminar con: módulo actualizado en Odoo, suite de tests verde (cuando exista), y commit limpio.

---

*Última actualización: 2026-05-02*
