# Plan de Mejoras — Reportes & Agentes IA

> Estado del análisis: 2026-06-10 · Módulos auditados: `estate_reports`, `estate_ai_agent`, `estate_management`

---

## ✅ Ya resuelto en esta iteración

| # | Problema | Solución aplicada |
|---|----------|-------------------|
| 1 | **Descripción IA se cortaba a la mitad** | Causa raíz: Gemini 2.5 Flash "piensa" por defecto y esos tokens consumían el presupuesto de salida. Se desactivó el thinking (`thinking_budget=0`) en generación/refinado/resumen + se subió `max_output_tokens` a 8192. Ahora genera completo. |
| 2 | **Subir imágenes una por una** | Nueva pestaña Imágenes: portada + zona de carga múltiple (`many2many_binary`, arrastra/selecciona varias) que se convierten automáticamente en `image_ids` al guardar. Galería visual en kanban. |
| 3 | **Emojis en la UI** | Reemplazados por iconos Font Awesome en: botones de propiedad IA, packs de marketing del chat, notificaciones, botones de gráficos. |
| 4 | **Análisis de imagen separado de la descripción** | Unificado en la pestaña Descripción. La condición/ambiente detectados ahora alimentan el prompt. |

---

## 🎯 Plan de mejoras pendientes

### A — Reportes / Dashboard

**Estado actual:** el dashboard se arma con ~15 campos `fields.Html` que devuelven strings HTML/SVG generados en Python (`estate_dashboard.py`, 1454 líneas). Funciona pero:
- No es reactivo (hay que recargar para refrescar)
- Gráficos son SVG inline difíciles de mantener
- Sin filtros de fecha interactivos
- Mezcla lógica de negocio + presentación en el mismo archivo

| Prioridad | Mejora | Beneficio |
|-----------|--------|-----------|
| 🔴 Alta | **Filtro de rango de fechas** en el dashboard (mes actual / trimestre / año / custom) que recalcule KPIs | Hoy los KPIs son fijos al período actual |
| 🔴 Alta | **Migrar gráficos a una librería real** (Chart.js, ya hay patrón en el chat) en vez de SVG string | Tooltips, animación, responsive, mantenible |
| 🟡 Media | **Separar `estate_dashboard.py`** en mixins: `_kpis.py`, `_charts.py`, `_rankings.py` | 1454 líneas en un archivo es difícil de mantener |
| 🟡 Media | **Exportar dashboard completo a PDF** (un clic, con los gráficos actuales) | Hoy solo exporta datos sueltos |
| 🟡 Media | **Comparativa período vs período** (este mes vs mes anterior, con flechas ▲▼ de variación) | Contexto de tendencia, no solo número absoluto |
| 🟢 Baja | **Caché de KPIs pesados** (TransientModel recalcula todo en cada apertura) | Velocidad de carga |
| 🟢 Baja | **Drill-down**: clic en un KPI abre la lista filtrada (ya existe parcialmente en algunos) | Navegación fluida |

### B — Agentes IA (profesionalización)

**Estado actual:** hay IA dispersa en varios puntos:
- `estate_ai_agent`: chat flotante + chat systray + descripción/resumen de propiedad
- `estate_document`: análisis de documentos
- `estate_reports`: pregunta IA al dashboard
- `estate_ai_contract`: generación de contratos

| Prioridad | Mejora | Beneficio |
|-----------|--------|-----------|
| 🔴 Alta | **Centralizar la config de Gemini** en un solo helper (`_get_genai_client()` + `thinking_budget`, retries, modelo) reutilizado por TODOS los módulos | Hoy cada módulo repite la config; el bug de thinking estaba en 3 sitios |
| 🔴 Alta | **Manejo robusto de `response.text` vacío** (si `finish_reason=MAX_TOKENS` o `SAFETY`, dar mensaje claro en vez de crashear) | Evita errores crípticos al usuario |
| 🟡 Media | **Streaming en la descripción** (ver el texto aparecer en vivo como en el chat) | Percepción de velocidad y profesionalismo |
| 🟡 Media | **Plantillas de prompt versionadas** en un campo de config editable, no hardcodeadas | El asesor ajusta el tono sin tocar código |
| 🟡 Media | **Registrar feedback 👍/👎** del chat en un modelo para mejorar prompts | Hoy el feedback es solo visual, no se guarda |
| 🟢 Baja | **Selector de modelo** (Flash para rápido / Pro para calidad) por tipo de tarea | Control costo/calidad |
| 🟢 Baja | **Indicador de costo/tokens** consumidos por sesión | Transparencia |

### C — Consistencia visual (todo el suite)

| Prioridad | Mejora |
|-----------|--------|
| 🟡 Media | Auditar y unificar **paleta de colores** (hoy hay `#004274`, `#1877F2`, gradientes varios) en variables SCSS |
| 🟡 Media | Reemplazar arrows tipográficos (→ ↑ ↓) de **botones** por iconos FA (los de texto de ayuda pueden quedar) |
| 🟢 Baja | Estandarizar **tarjetas/badges** con clases Bootstrap nativas de Odoo en vez de `style=` inline |

---

## Sugerencia de orden de ejecución

1. **Centralizar config Gemini** (B-alta) → arregla bugs de raíz en todos los módulos a la vez
2. **Filtro de fechas + comparativa período** (A-alta) → el cambio más visible para tu defensa de tesis
3. **Migrar gráficos a Chart.js** (A-alta) → calidad visual profesional
4. **Guardar feedback + plantillas de prompt** (B-media) → diferenciador "inteligente"

---

## ✅ Implementación completada (2026-06-10)

| Item | Qué se hizo |
|------|-------------|
| **B-alta** Centralizar Gemini | Nuevo `estate.genai.mixin` (AbstractModel en estate_management) con cliente, reintentos, **thinking desactivado** y extracción robusta. Refactorizados estate_property, estate_ai_contract, estate_document y estate_dashboard. El bug de truncamiento queda corregido en **todos** los módulos a la vez. |
| **B-alta** Manejo robusto | `_genai_generate` lanza mensaje claro con `finish_reason` si la IA no devuelve texto, en vez de crashear. |
| **B-media** Feedback persistente | Modelo `estate.ai.feedback` + endpoint `/estate_ai/feedback` + el chat guarda cada 👍/👎 con pregunta/respuesta. Vista y menú **Asistente IA → Feedback de Respuestas** (managers). |
| **B-media** Plantillas de prompt | Campo editable **Estilo de Descripciones** en Configuración → Agente IA, inyectado en el prompt sin tocar código. |
| **A-alta** Filtro de fechas | Ya existía: período (mes/trimestre/año/mes anterior/personalizado) con `_get_period_dates`. |
| **A-alta** Comparativa período | Ya existía: `_get_prev_period_dates` + tendencias con variación %. |
| **A-alta** Gráficos Chart.js | Nuevo widget OWL `dashboard_chart` (Chart.js incluido en Odoo) + pestaña **Gráficos** con ventas por mes y leads por fuente. |
| **A-media** PDF del dashboard | Reporte QWeb `report_dashboard_executive` + botón **Exportar a PDF** (KPIs, finanzas, tendencias, embudo, ranking). |
| **C** Consistencia visual | Paleta de marca centralizada en `brand_palette.scss` (variables `--inmobi-*`); botón con flecha → icono FA. |

**Pendiente opcional (baja prioridad):** caché de KPIs, drill-down extendido, streaming en descripción, selector de modelo Flash/Pro, indicador de tokens. Quedan documentados arriba para una siguiente iteración.
