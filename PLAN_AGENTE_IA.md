# Plan de Mejoras — Agente IA Inmobiliario
**Módulo:** `estate_ai_agent` | Odoo 19 Community | Fecha: 2026-04-09

---

## Estado actual del agente

### Herramientas activas (15 tools)
| Categoría | Tool | Acción |
|-----------|------|--------|
| Lectura | `search_properties` | Buscar propiedades con filtros |
| Lectura | `get_leads` | Consultar leads/oportunidades CRM |
| Lectura | `get_market_stats` | Estadísticas de mercado |
| Lectura | `get_payments_contracts` | Pagos y contratos vencidos |
| Lectura | `get_dashboard_summary` | Resumen ejecutivo |
| Lectura | `get_report_data` | 11 tipos de reportes agregados |
| Escritura | `create_property` | Nueva propiedad |
| Escritura | `create_lead` | Nuevo lead CRM |
| Escritura | `create_crm_activity` | Actividad de seguimiento |
| Escritura | `update_property` | Modificar precio/estado/descripción |
| Escritura | `update_lead` | Modificar etapa/temperatura/notas |
| Acción | `schedule_visit` | Agendar visita |
| Acción | `reserve_property` | Reservar propiedad |
| Acción | `sell_property` | Cerrar venta/alquiler |
| Acción | `send_whatsapp_lead` | Generar enlace WhatsApp |
| Acción | `archive_lead` | Archivar lead |

### Capacidades IA actuales
- **Dual provider:** Google Gemini (default) + OpenAI
- **Streaming SSE:** respuesta word-by-word
- **Historial:** últimos 8 mensajes en contexto
- **Vision AI:** analiza imagen principal de propiedad
- **Generación de texto:** descripciones de marketing (3 versiones) + borradores de contrato

### Brechas principales
- No puede eliminar registros
- No crea contratos, pagos, comisiones ni ofertas directamente
- No envía emails ni genera PDFs desde el chat
- Sin predicción ni ML — el scoring es por reglas fijas
- Sin memoria a largo plazo (resetea entre sesiones)
- Sin confirmación antes de acciones destructivas
- No opera en lote (un registro a la vez)

---

## Plan de Mejoras

### PRIORIDAD A — Alto impacto, implementación directa

---

#### A1 — CRUD Completo: Contratos, Pagos, Comisiones, Ofertas
**Qué hace:** El agente puede crear/consultar contratos, registrar pagos y aprobar comisiones directamente desde el chat sin salir del widget.

**Tools a añadir:**
```python
create_contract   # "Crea contrato de venta para Juan Pérez en Propiedad XYZ por $85,000"
update_contract   # "Activa el contrato CON-0023"
create_payment    # "Registra pago de $1,200 para contrato CON-0018, método transferencia"
approve_payment   # "Marca como pagado el pago PAG-0042"
create_offer      # "Crea oferta de $72,000 de María González para casa Quito-01"
create_commission # "Registra comisión de venta de $3,500 para el asesor Carlos Torres"
approve_commission # "Aprueba la comisión COM-0015"
```

**Archivos a modificar:**
- `controllers/estate_ai_controller.py` → añadir tools en `TOOLS_OPENAI` + handlers en `_execute_tool`
- Requiere confirmación del usuario antes de ejecutar (ver A3)

---

#### A2 — Herramienta: Generar y Descargar PDF desde el Chat
**Qué hace:** El agente puede lanzar cualquier reporte PDF del sistema (ficha técnica, estado de cuenta, comisiones, cotización) y devuelve un link de descarga directo en el chat.

**Tool a añadir:**
```python
generate_pdf_report  # "Genera el estado de cuenta del contrato CON-0015"
                     # "Descarga la ficha técnica de la propiedad PROP-0023"
                     # "Genera el PDF de comisiones de junio"
```

**Implementación:**
```python
# En _execute_tool → case 'generate_pdf_report':
report = env.ref(f'estate_reports.{report_xmlid}')
pdf_bytes, _ = report._render_qweb_pdf(record_ids)
attachment = env['ir.attachment'].create({
    'name': filename, 'datas': base64.b64encode(pdf_bytes),
    'res_model': model, 'res_id': record_id,
})
# Devolver URL: /web/content/{attachment.id}
```

**Archivos a modificar:**
- `controllers/estate_ai_controller.py`

---

#### A3 — Confirmación de Seguridad para Acciones Destructivas
**Qué hace:** Antes de ejecutar acciones que modifican estado (vender, reservar, eliminar, cerrar contrato), el agente muestra un resumen y espera confirmación explícita del usuario ("confirmar" / "cancelar").

**Implementación en el frontend (OWL):**
```javascript
// En ai_chat_float.js: detectar eventos de tipo 'confirm_action'
// Mostrar tarjeta con: ⚠️ Acción a realizar + [Confirmar] [Cancelar]
// Solo enviar segunda petición si usuario confirma
```

**Implementación en backend:**
```python
# En generate() del stream: si es acción destructiva y no hay flag 'confirmed'
# Emitir evento SSE tipo 'confirm_required' con resumen de la acción
# Guardar pending_action en sesión
```

**Acciones que requieren confirmación:**
- `sell_property`, `reserve_property`, `archive_lead`
- `update_property` (cambio de estado), `update_lead` (ganado/perdido)
- Cualquier nuevo tool de eliminación

---

#### A4 — Tool: Eliminar / Archivar Registros
**Qué hace:** Permite al agente archivar propiedades, leads, pagos cancelados u ofertas rechazadas cuando el usuario lo solicita explícitamente.

**Tools a añadir:**
```python
delete_property   # "Archiva la propiedad PROP-0045 que ya se vendió fuera de sistema"
delete_offer      # "Elimina la oferta OFR-0012, fue un duplicado"
cancel_payment    # "Cancela el pago PAG-0038 por error de registro"
```

**Reglas de seguridad:**
- Solo archivar (nunca `unlink`) para mantener trazabilidad
- Obligatorio pasar por confirmación A3
- Registrar en chatter del registro quién ordenó la acción y cuándo

---

#### A5 — Operaciones en Lote (Batch Actions)
**Qué hace:** El agente puede operar sobre múltiples registros de una sola instrucción.

**Ejemplos:**
```
"Actualiza el precio de todas las casas de Guayaquil disponibles con área > 200m² a $95,000"
"Archiva todos los leads fríos sin actividad en los últimos 60 días"
"Asigna el asesor Carlos Torres a las 3 propiedades que me mostraste"
```

**Implementación:**
```python
# Tools batch:
batch_update_properties  # domain + campos a actualizar
batch_update_leads       # domain + campos
batch_archive_leads      # domain de leads a archivar
```

**Limitación de seguridad:** máximo 50 registros por operación batch. Confirmar siempre.

---

#### A6 — Tool: Enviar Email desde el Chat
**Qué hace:** El agente puede enviar emails a clientes directamente (cotización, recordatorio de pago, confirmación de visita) usando las plantillas existentes.

**Tool a añadir:**
```python
send_email  # "Envía la cotización a juan@email.com del lead LEAD-0034"
            # "Manda recordatorio de pago vencido al cliente del contrato CON-0019"
```

**Implementación:**
```python
# Usar mail.template existente o generar cuerpo dinámico
# env['mail.mail'].create({...}).send()
# Registrar en chatter del registro
```

---

### PRIORIDAD B — Inteligencia Aumentada con IA/ML

---

#### B1 — Lead Scoring con IA (vs reglas fijas actuales)
**Problema actual:** El scoring es 100% por reglas hardcodeadas (presupuesto + contacto + visitas). No aprende ni se adapta.

**Mejora:**
1. **Scoring predictivo con LLM:** enviar perfil completo del lead al LLM y pedir probabilidad de cierre con justificación
2. **Análisis de patrones históricos:** comparar lead actual con leads ganados/perdidos para dar score contextual
3. **Tool `analyze_lead_probability`:**
```python
# Input: lead_id
# Proceso: recopilar historial de leads cerrados → construir prompt con contexto
# Output: probabilidad 0-100%, clasificación A/B/C, 3 factores clave, acción recomendada
```

**Prompt de ejemplo:**
```
Tienes acceso a 50 ventas cerradas. El nuevo lead tiene: presupuesto $120k, 
2 visitas completadas, email verificado, ciudad Quito, tipo casa, 
respondió en 2h. Dado el patrón histórico, ¿cuál es la probabilidad de cierre?
Responde con: {"probability": 78, "score": "A", "factors": [...], "next_action": "..."}
```

---

#### B2 — Predicción de Churn de Inquilinos
**Qué hace:** Analiza contratos de arriendo activos y detecta señales de riesgo de abandono: pagos tardíos, solicitudes de mantenimiento frecuentes, contratos próximos a vencer sin renovación.

**Tool a añadir:**
```python
analyze_churn_risk  # "¿Qué inquilinos tienen más riesgo de no renovar?"
```

**Señales que analiza el agente:**
- Pagos vencidos en los últimos 90 días (estate.payment)
- Solicitudes de mantenimiento abiertas (estate.tenant.request)
- Días para vencimiento del contrato (< 45 días = alerta)
- Ausencia de interacciones CRM en los últimos 30 días
- Lead_temperature en CRM

**Output:** tabla con riesgo Alto/Medio/Bajo por inquilino + acción recomendada

---

#### B3 — AVM Inteligente con IA (mejora del actual)
**Problema actual:** El AVM usa promedio simple de comparables sin features ponderadas.

**Mejora con IA:**
```python
tool: recalculate_avm_ai  # "Recalcula el valor de mercado de PROP-0023 con IA"
```

**Proceso:**
1. Recopilar comparables: mismo tipo, ciudad, ±30% área, últimos 12 meses
2. Construir prompt con tabla de comparables + características de la propiedad
3. LLM retorna: rango de valor, precio justo, confianza (%), factores clave
4. Actualizar `avm_estimated_price` y `avm_status` automáticamente

---

#### B4 — Generador de Descripción con Análisis de Imagen (mejorado)
**Mejora sobre el actual:** Actualmente genera 3 versiones de descripción pero no las guarda ni publica.

**Nuevo comportamiento:**
- Genera descripción + sugiere precio de lista ajustado al mercado actual
- Opción: "aplica esta descripción a la propiedad" → `update_property` automático
- Opción: "publica en WordPress" → llama `action_publish_wordpress`
- Tool `generate_and_apply_description`:
```
"Genera la descripción de PROP-0034, aplícala y publícala en WordPress"
```

---

#### B5 — Memoria a Largo Plazo (Persistent Memory)
**Problema actual:** El agente olvida todo al limpiar historial. No recuerda preferencias, clientes frecuentes ni acuerdos previos.

**Solución:** Nuevo modelo `estate.ai.memory`:
```python
class EstateAIMemory(models.Model):
    _name = 'estate.ai.memory'
    user_id    = fields.Many2one('res.users')
    memory_type = fields.Selection([
        ('preference', 'Preferencia del usuario'),
        ('fact',       'Hecho del negocio'),
        ('client',     'Datos de cliente recordados'),
        ('alert',      'Alerta activa'),
    ])
    content    = fields.Text()
    expires_at = fields.Date()  # None = permanente
```

**Tools a añadir:**
```python
save_memory   # "Recuerda que Carlos Torres es el asesor principal de Guayaquil"
recall_memory # "¿Qué recuerdas sobre el cliente Juan Pérez?"
```

**Integración:** las memorias relevantes se inyectan automáticamente en el system prompt al inicio de cada conversación.

---

#### B6 — Agente de Seguimiento Autónomo (Proactive Agent)
**Qué hace:** Un cron job diario activa el agente para que revise el estado del negocio y tome acciones sin que el usuario lo solicite:

**Acciones autónomas configurables:**
```python
# En estate.ai.config: checkbox 'proactive_agent_enabled'
# Cron: _cron_proactive_agent() diario a las 8am
```

| Trigger | Acción autónoma |
|---------|----------------|
| Lead caliente sin contacto en 48h | Crear actividad + WhatsApp al asesor |
| Pago vencido +7 días sin actividad | Enviar email al cliente automáticamente |
| Contrato vence en 30 días | Crear tarea de renovación al asesor |
| Propiedad disponible > 90 días | Sugerir rebaja de precio via notificación |
| Lead con match ≥ 95% nueva propiedad | Notificar asesor automáticamente |

---

### PRIORIDAD C — Experiencia y Calidad de Uso

---

#### C1 — OCR de Documentos (Escrituras, Facturas, Planos)
**Qué hace:** El usuario sube una imagen/PDF al chat y el agente extrae los datos relevantes para pre-rellenar campos.

**Casos de uso:**
```
Usuario: [adjunta foto de escritura]
Agente: "Detecté: Propietario: Juan Pérez, RUC: 1234567890, 
         Dirección: Av. 12 de Octubre 234, Quito, Área: 186m², 
         Precio escritura: $78,500. ¿Creo la propiedad con estos datos?"
```

**Implementación:**
- Endpoint `/estate_ai/upload` que acepta imagen/PDF
- Gemini Vision o GPT-4V para extraer datos en JSON
- Tool `extract_document_data` que parsea y propone creación de registro

**Formatos soportados:** JPG, PNG, PDF (primera página), WebP

---

#### C2 — Interfaz de Chat Mejorada (UI/UX)
**Mejoras al widget `ai_chat_float.js`:**

1. **Tarjetas de acción confirmable:** en vez de texto plano, mostrar card con resumen de lo que se va a hacer + botones [Confirmar] [Cancelar] [Ver más]
2. **Chips de sugerencias contextuales:** según la página donde está el usuario (en propiedad → "Analizar imagen", "Ver similares"; en lead → "Calcular score", "Agendar visita")
3. **Indicador de estado del agente:** "Consultando base de datos...", "Generando descripción...", "Analizando imagen..."
4. **Historial con búsqueda:** filtrar conversaciones pasadas por fecha o palabra clave
5. **Modo voz (Web Speech API):** botón de micrófono para dictar comandos
6. **Copiar resultado:** botón para copiar respuestas al portapapeles

---

#### C3 — Multi-Agente: Asistentes Especializados
**Qué hace:** En vez de un solo agente generalista, el usuario puede activar un agente especializado según el contexto.

| Agente | Especialidad | Activación |
|--------|-------------|-----------|
| 🏠 **PropAgent** | Propiedades: valoración, descripción, AVM | Menú propiedades |
| 👥 **CRMAgent** | Leads: scoring, seguimiento, matchmaking | Menú CRM |
| 💰 **FinAgent** | Contratos, pagos, comisiones, flujo de caja | Menú operaciones |
| 📊 **ReportAgent** | Reportes, KPIs, exportaciones, dashboards | Menú inteligencia |

**Implementación:** campo `agent_mode` en request + system prompts distintos por modo.

---

#### C4 — Integración con Email Entrante (AI Email Triage)
**Qué hace:** El agente lee emails entrantes de clientes (bandeja de `mail.message`) y los clasifica/responde automáticamente.

```python
# Cron: _cron_email_triage()
# Por cada email sin respuesta en las últimas 2h:
#   - Clasificar: consulta propiedad / solicitud visita / queja / otro
#   - Si es consulta propiedad → generar respuesta + sugerir propiedades
#   - Si es solicitud visita → crear evento en calendar + responder
#   - Si es queja → crear actividad urgente para asesor
```

---

#### C5 — Dashboard del Agente (Métricas de Uso)
**Qué hace:** Nueva vista en Odoo que muestra el rendimiento del agente IA.

**Métricas:**
- Conversaciones por día/semana/mes
- Herramientas más usadas
- Tiempo promedio de respuesta
- Acciones ejecutadas (leads creados, propiedades actualizadas, visitas agendadas)
- Tasa de confirmación vs cancelación en acciones
- Usuarios más activos

**Implementación:** vista `list + graph` del modelo `estate.ai.chat.history` + nuevas métricas en `estate.ai.memory`.

---

#### C6 — Soporte Multi-Idioma
**Qué hace:** El agente detecta automáticamente el idioma del usuario y responde en el mismo idioma. Útil para clientes extranjeros (inglés, portugués).

**Implementación:**
```python
# En system prompt: "Detect the user's language and always respond in the same language."
# En _get_system_context: añadir campo 'partner_lang' del usuario actual
```

---

## Tabla de Prioridades y Esfuerzo

| ID | Mejora | Impacto | Esfuerzo | Archivos |
|----|--------|---------|----------|---------|
| **A1** | CRUD: Contratos/Pagos/Comisiones/Ofertas | ★★★★★ | Medio | controller.py |
| **A2** | Generar PDF desde chat | ★★★★☆ | Bajo | controller.py |
| **A3** | Confirmación acciones destructivas | ★★★★☆ | Medio | controller.py + JS |
| **A4** | Eliminar/Archivar registros | ★★★☆☆ | Bajo | controller.py |
| **A5** | Operaciones en lote | ★★★★☆ | Medio | controller.py |
| **A6** | Enviar email desde chat | ★★★★☆ | Bajo | controller.py |
| **B1** | Lead Scoring con IA | ★★★★★ | Medio | controller.py |
| **B2** | Predicción Churn inquilinos | ★★★★☆ | Medio | controller.py |
| **B3** | AVM inteligente con IA | ★★★☆☆ | Medio | controller.py |
| **B4** | Descripción + publicar WP | ★★★☆☆ | Bajo | controller.py |
| **B5** | Memoria a largo plazo | ★★★★☆ | Alto | nuevo modelo + controller |
| **B6** | Agente proactivo autónomo | ★★★★★ | Alto | nuevo cron + controller |
| **C1** | OCR de documentos | ★★★★☆ | Alto | nuevo endpoint + controller |
| **C2** | UI/UX del chat mejorado | ★★★☆☆ | Medio | JS widgets |
| **C3** | Multi-agente especializado | ★★★☆☆ | Alto | controller + config |
| **C4** | Triage de email con IA | ★★★★☆ | Alto | nuevo cron |
| **C5** | Dashboard métricas del agente | ★★☆☆☆ | Bajo | nueva vista |
| **C6** | Multi-idioma automático | ★★☆☆☆ | Muy bajo | system prompt |

---

## Top 5 Recomendados para Implementar Primero

```
1. A1 — CRUD Contratos/Pagos   → más valor: el agente ya tiene 15 tools, añadir 7 más lo hace "completo"
2. A3 — Confirmación seguridad  → crítico antes de expandir escrituras, previene errores graves  
3. B1 — Lead Scoring con IA     → diferenciador clave, convierte el agente en asesor estratégico
4. A2 — Generar PDF desde chat  → muy solicitado, implementación rápida, alto impacto visual
5. B6 — Agente proactivo        → de reactivo a autónomo — el salto cualitativo más grande
```

---

## Referencia: Tabla de Funcionalidades Avanzadas

| Componente | Funcionalidad | Implementación en este sistema |
|------------|--------------|-------------------------------|
| **Lead Scoring IA** | Probabilidad de cierre con LLM | Tool `analyze_lead_probability` — B1 |
| **OCR Inteligente** | Leer escrituras y facturas escaneadas | Endpoint upload + Gemini Vision — C1 |
| **Generador de Contenido** | Descripciones persuasivas de inmuebles | Ya existe; mejorar con auto-publicar — B4 |
| **Predicción de Churn** | Inquilinos en riesgo de abandono | Tool `analyze_churn_risk` + cron — B2 |
| **Agente Autónomo** | Seguimiento sin intervención humana | Cron proactivo + tools de escritura — B6 |
| **Memoria Persistente** | Recordar hechos entre sesiones | Modelo `estate.ai.memory` — B5 |
