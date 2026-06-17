# Fases del Proyecto — Sistema de Gestión Inmobiliaria ERP Odoo 19

> **Título:** Diseño e Implementación de un Sistema de Gestión Inmobiliaria basado en ERP Odoo con Integración de un Agente Inteligente para Consulta y Generación de Reportes
> **Empresa cliente:** Inmobi — Cuenca, Ecuador
> **Autor:** Justin Mateo Lucero Reyes — Universidad Politécnica Salesiana

---

## FASE 1 — Levantamiento de Información y Diagnóstico

### 1.1 Contexto de la empresa

La empresa **Inmobi** es una inmobiliaria ubicada en la ciudad de Cuenca, Ecuador. Al momento del levantamiento de información, sus procesos operativos presentaban las siguientes características:

| Proceso | Herramienta usada |
|---|---|
| Registro de propiedades | Hojas de cálculo Excel |
| Seguimiento de clientes | Registros manuales y aplicaciones no propias |
| Control de contratos | Documentos Word + carpetas físicas |
| Seguimiento de pagos | Excel sin automatización |
| Publicación en sitio web | Ingreso manual propiedad por propiedad |
| Reportes de ventas | No existían — datos dispersos sin consolidar |
| Agendamiento de visitas | WhatsApp / Agenda personal del asesor |
| Notificaciones a clientes | Manual (llamadas o mensajes individuales) |

### 1.2 Problemas identificados

A partir de entrevistas con el personal de Inmobi y análisis de sus procesos, se identificaron los siguientes problemas estructurales:

#### Problema 1 — Desorganización de la información
- Los datos de propiedades, clientes y contratos vivían en sistemas separados sin integración.
- Duplicación de registros: un mismo cliente podía estar en dos hojas diferentes con datos distintos.
- Pérdida de información al rotar personal o al cambiar de asesor responsable.

#### Problema 2 — Falta de seguimiento de clientes (CRM)
- No existía un sistema para registrar el avance de un prospecto: desde el primer contacto hasta el cierre.
- Los asesores dependían de su memoria o notas personales para hacer seguimiento.
- Sin visibilidad del "estado" de cada oportunidad de negocio (fría, caliente, cerrada).

#### Problema 3 — Control de contratos y documentos desconectado
- Los contratos se guardaban como archivos Word sueltos, sin vínculo al cliente ni a la propiedad en el sistema.
- Los documentos legales (cédulas, escrituras, avalúos) no tenían ciclo de vida: no había control de si estaban pendientes, recibidos o verificados.
- Al abrir la ficha de un cliente era imposible ver todos sus documentos en un solo lugar.

#### Problema 4 — Publicación web manual y lenta
- Cada vez que se agregaba o modificaba una propiedad, el asesor debía entrar manualmente al sitio WordPress y actualizar los datos.
- Esto generaba inconsistencias: el sitio mostraba propiedades ya vendidas o precios desactualizados.

#### Problema 5 — Sin reportes para tomar decisiones
- No existía ningún reporte que respondiera preguntas como:
  - ¿Cuál es el precio promedio de venta este trimestre?
  - ¿Cuántos días tarda en venderse una casa en Cuenca?
  - ¿Qué asesor está vendiendo más?
  - ¿Cuántas propiedades llevan más de 90 días disponibles sin venderse?

#### Problema 6 — Sin automatización de comunicaciones
- Los recordatorios de visitas se enviaban a mano por WhatsApp.
- No había notificaciones automáticas al cliente cuando su contrato estaba por vencer.
- El seguimiento post-visita dependía de cada asesor.

### 1.3 Conclusión del diagnóstico

La empresa Inmobi necesitaba una solución que:
1. **Centralizara** la información en un solo sistema integrado
2. **Automatizara** las tareas repetitivas (notificaciones, publicaciones, reportes)
3. **Conectara** los procesos de propiedad → cliente → contrato → pago en un flujo único
4. **Proveyera visibilidad** en tiempo real del estado del negocio
5. **Integrara inteligencia artificial** para consultas, generación de descripciones y reportes

---

## FASE 2 — Definición de Requerimientos

### 2.1 Requerimientos Funcionales

A partir del diagnóstico se definieron los siguientes requerimientos funcionales agrupados por módulo:

#### RF-01 — Gestión de Propiedades
| ID | Requerimiento |
|---|---|
| RF-01.1 | Registrar propiedades con datos completos: ubicación, área, habitaciones, precio, tipo |
| RF-01.2 | Control de estado: Disponible → Reservado → Vendido / Arrendado |
| RF-01.3 | Generación automática de código QR por propiedad |
| RF-01.4 | Estimación automática del valor de mercado (AVM) |
| RF-01.5 | Historial de cambios de precio |
| RF-01.6 | Registro de imágenes de la propiedad |
| RF-01.7 | Días en mercado calculados automáticamente |

#### RF-02 — CRM y Gestión de Clientes
| ID | Requerimiento |
|---|---|
| RF-02.1 | Registrar leads/prospectos con datos de contacto y presupuesto |
| RF-02.2 | Algoritmo de match entre presupuesto del cliente y propiedades disponibles |
| RF-02.3 | Clasificación automática del lead: score A/B/C y temperatura cold/warm/hot/boiling |
| RF-02.4 | Recibir leads automáticamente desde el sitio web (webhook WordPress) |
| RF-02.5 | Recibir leads desde redes sociales (webhook Meta/Facebook) |
| RF-02.6 | Tips de negociación generados por IA según el perfil del lead |
| RF-02.7 | Seguimiento del pipeline de ventas con etapas configurables |

#### RF-03 — Contratos
| ID | Requerimiento |
|---|---|
| RF-03.1 | Registrar contratos de venta, arrendamiento y exclusividad |
| RF-03.2 | Flujo de estados: Borrador → Activo → Suspendido / Renovando → Renovado / Vencido |
| RF-03.3 | Firma digital del cliente directamente en el sistema |
| RF-03.4 | Control de pagos vinculados al contrato |
| RF-03.5 | Generación de facturas desde los pagos |
| RF-03.6 | Contratos de renovación vinculados al contrato padre |
| RF-03.7 | Generación de borrador de contrato por IA (Gemini) |
| RF-03.8 | Al crear un contrato desde una oferta, notificar al asesor con link directo |

#### RF-04 — Gestión Documental
| ID | Requerimiento |
|---|---|
| RF-04.1 | Registrar documentos vinculados a propiedades, clientes, leads y contratos |
| RF-04.2 | Más de 25 tipos de documento configurables por categoría |
| RF-04.3 | Ciclo de vida: Pendiente → Recibido → Verificado → Archivado / Rechazado |
| RF-04.4 | Niveles de confidencialidad: Público / Interno / Restringido / Confidencial |
| RF-04.5 | Vista unificada "Carpeta del cliente" con todos sus documentos |
| RF-04.6 | Extracción automática de datos de documentos mediante OCR con IA (Gemini Vision) |
| RF-04.7 | Fecha de vencimiento para certificados con alerta de expiración próxima |

#### RF-05 — Calendario y Visitas
| ID | Requerimiento |
|---|---|
| RF-05.1 | Agendar visitas a propiedades desde el CRM |
| RF-05.2 | Tipos de cita: visita, llamada, reunión, seguimiento |
| RF-05.3 | Recordatorio automático por WhatsApp 1 hora antes de cada visita |
| RF-05.4 | Registro del resultado de la visita: rating y notas del asesor |

#### RF-06 — Reportes y Analítica
| ID | Requerimiento |
|---|---|
| RF-06.1 | Dashboard general con KPIs en tiempo real |
| RF-06.2 | Reporte de promedio de ventas con filtros y comparativa de períodos |
| RF-06.3 | 12 tipos de reportes exportables en PDF y Excel |
| RF-06.4 | Liquidación de comisiones por asesor |
| RF-06.5 | Mapa interactivo de propiedades |
| RF-06.6 | Embudo de conversión Lead → Oferta → Contrato → Venta |
| RF-06.7 | Ranking de asesores por desempeño mensual |
| RF-06.8 | Reporte mensual automático enviado por email a administradores |

#### RF-07 — Integración WordPress
| ID | Requerimiento |
|---|---|
| RF-07.1 | Publicar propiedades automáticamente en el sitio WordPress al guardar |
| RF-07.2 | Sincronizar cambios de precio, estado y descripción en tiempo real |
| RF-07.3 | Recibir leads del formulario de contacto del sitio web como oportunidades CRM |
| RF-07.4 | Importar propiedades existentes de WordPress al sistema Odoo |

#### RF-08 — Agente Inteligente
| ID | Requerimiento |
|---|---|
| RF-08.1 | Chat en lenguaje natural integrado en el ERP (widget flotante) |
| RF-08.2 | Consultar datos del sistema: propiedades, clientes, contratos, pagos |
| RF-08.3 | Integración con Google Gemini API y OpenAI como proveedor alternativo |
| RF-08.4 | Alertas proactivas diarias: pagos vencidos, contratos por vencer, leads calientes sin actividad |
| RF-08.5 | Historial de conversaciones por usuario |

### 2.2 Requerimientos No Funcionales

| ID | Requerimiento |
|---|---|
| RNF-01 | El sistema debe ejecutarse sobre Odoo 19 Community Edition |
| RNF-02 | Base de datos PostgreSQL |
| RNF-03 | Autenticación y permisos por grupos: Asesor, Manager, Administrador |
| RNF-04 | Reglas de registro (ir.rule) para control de confidencialidad de documentos |
| RNF-05 | Notificaciones WhatsApp vía Meta WhatsApp Cloud API |
| RNF-06 | Frontend reactivo con OWL (Odoo Web Library) para el widget del agente IA |
| RNF-07 | Exportación de reportes en PDF (QWeb) y Excel (xlsxwriter) |
| RNF-08 | Archivos de documento máximo 10 MB, formatos: PDF, DOC, XLS, JPG, PNG, WEBP |

### 2.3 Arquitectura definida

```
┌─────────────────────────────────────────────────────────────────┐
│                    CAPA DE PRESENTACIÓN                          │
│  Odoo Web Client (OWL/JS)  │  WordPress (portal público)        │
│  Widget IA flotante         │  Floating Chat Widget              │
└─────────────────┬──────────────────────────────────────────────┘
                  │ HTTPS/TLS
┌─────────────────▼──────────────────────────────────────────────┐
│                  CAPA DE LÓGICA DE NEGOCIO                      │
│  Servidor Odoo 19 (Python 3.11)                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐   │
│  │ Módulos ERP  │  │  Agente IA   │  │     Cron Jobs      │   │
│  │ Inmobiliario │  │ (NLP, CRUD)  │  │ (WhatsApp/Alertas) │   │
│  └──────────────┘  └──────┬───────┘  └────────────────────┘   │
└─────────────────────────────│───────────────────────────────────┘
                              │ API
        ┌─────────────────────┼────────────────────┐
        ▼                     ▼                     ▼
  Google Gemini API    Meta WhatsApp API    WordPress REST API
┌───────────────────────────────────────────────────────────────┐
│                     CAPA DE DATOS                             │
│         PostgreSQL 15 — Base de datos tesis_odoo19            │
│    Propiedades · Contratos · Leads · Calendario · Docs · IA   │
└───────────────────────────────────────────────────────────────┘
```

---

## FASE 3 — Implementación de Módulos

El sistema se implementó como **9 módulos Odoo custom** instalados sobre Odoo 19 Community Edition. Cada módulo vive en su propia carpeta dentro del directorio del proyecto.

**Servidor:** `http://localhost:8070` · **DB:** `tesis_odoo19` · **Config:** [odoo19.conf](odoo19.conf)

---

### MÓDULO 1 — `estate_management` (Núcleo)

**Ubicación:** [estate_management/](estate_management/)
**Propósito:** Es el módulo central. Define todas las entidades base del negocio inmobiliario.

#### Modelos implementados

| Modelo | Descripción | Archivo |
|---|---|---|
| `estate.property` | Propiedad inmobiliaria — entidad central del sistema | [models/estate_property.py](estate_management/models/estate_property.py) |
| `estate.contract` | Contrato de venta, arriendo o exclusividad | [models/estate_contract.py](estate_management/models/estate_contract.py) |
| `estate.payment` | Pago vinculado a un contrato | [models/estate_payment.py](estate_management/models/estate_payment.py) |
| `estate.offer` | Oferta de compra/arriendo de un cliente sobre una propiedad | [models/estate_offer.py](estate_management/models/estate_offer.py) |
| `estate.commission` | Comisión generada al cerrar una venta | [models/estate_commission.py](estate_management/models/estate_commission.py) |
| `estate.appraisal` | Avalúo / tasación formal de una propiedad | [models/estate_appraisal.py](estate_management/models/estate_appraisal.py) |
| `estate.property.type` | Catálogo de tipos de propiedad (Casa, Dpto, Terreno…) | [models/estate_property_type.py](estate_management/models/estate_property_type.py) |
| `estate.property.tag` | Etiquetas de propiedad (Vista al mar, Esquinero…) | [models/estate_property_tag.py](estate_management/models/estate_property_tag.py) |
| `estate.property.image` | Imágenes adicionales por propiedad | [models/estate_property_image.py](estate_management/models/estate_property_image.py) |
| `estate.price.history` | Historial de cambios de precio | [models/estate_price_history.py](estate_management/models/estate_price_history.py) |
| `estate.expense` | Gastos asociados a una propiedad | [models/estate_expense.py](estate_management/models/estate_expense.py) |
| `estate.tenant` | Inquilino de un arrendamiento | [models/estate_tenant.py](estate_management/models/estate_tenant.py) |

#### Funcionalidades clave de `estate.property`
- **Estado:** `available → reserved → sold / rented` con trazabilidad en chatter
- **AVM:** `avm_estimated_price` calculado con media de precios del mercado local + `avm_status` (fair/high/low)
- **QR Code:** campo `qr_image` generado automáticamente (librería `qrcode`)
- **Días en mercado:** `days_on_market` calculado desde `date_listed` hasta hoy
- **Relaciones:** `owner_id` (propietario), `buyer_id` (comprador), `user_id` (asesor responsable)
- **WordPress:** `wp_published`, `wp_post_id` para sincronización

#### Funcionalidades clave de `estate.contract`
- **7 estados:** `draft → active → suspended ↔ renewing → renewed / expired / cancelled`
- **Transiciones validadas:** diccionario `_VALID_STATE_TRANSITIONS` — el sistema rechaza saltos inválidos
- **Firma digital:** campo `customer_signature` (widget `signature`) + `signature_date`
- **Smart-buttons:** conteos en vivo de Pagos, Facturas, Documentos, Oferta origen
- **Renovaciones:** `parent_contract_id` y `child_contract_ids` para cadena de renovaciones
- **Cron:** `_cron_generate_rent_invoices` — genera facturas mensuales de arriendo automáticamente

---

### MÓDULO 2 — `estate_crm` (CRM Inmobiliario)

**Ubicación:** [estate_crm/](estate_crm/)
**Propósito:** Extiende el CRM nativo de Odoo para el negocio inmobiliario.

#### Modelos implementados

| Modelo | Descripción | Archivo |
|---|---|---|
| `crm.lead` (extendido) | Lead/oportunidad con datos inmobiliarios | [models/crm_lead.py](estate_crm/models/crm_lead.py) |
| `estate.property.match` | Resultado del algoritmo de match propiedad-cliente | [models/estate_property_match.py](estate_crm/models/estate_property_match.py) |
| `estate.interaction` | Registro de interacciones con el cliente | [models/estate_interaction.py](estate_crm/models/estate_interaction.py) |
| `meta.webhook.event` | Eventos recibidos desde Facebook/Instagram | [models/meta_webhook_event.py](estate_crm/models/meta_webhook_event.py) |

#### Campos añadidos a `crm.lead`
- `target_property_id` — Propiedad de interés del cliente
- `client_budget` — Presupuesto disponible
- `match_percentage` — % de compatibilidad entre presupuesto y propiedad (calculado)
- `lead_score` — Puntuación A/B/C
- `lead_temperature` — cold / warm / hot / boiling
- `smart_negotiation_tips` — Tips generados por Gemini IA

#### Algoritmo de match presupuestal
Cuando un cliente tiene propiedad de interés asignada, `_compute_match_percentage` calcula:
- Precio vs presupuesto (50% del score)
- Ciudad coincidente (20%)
- Tipo de propiedad coincidente (15%)
- Habitaciones (10%)
- Área (5%)

Si el match es ≥ 95%, **se crea automáticamente un lead en CRM** vinculando al cliente con la propiedad.

#### Controladores (webhooks)
- [controllers/webhook_controller.py](estate_crm/controllers/webhook_controller.py) — Recibe leads de WordPress y Meta
- [controllers/whatsapp_controller.py](estate_crm/controllers/whatsapp_controller.py) — Recibe mensajes de WhatsApp Business

---

### MÓDULO 3 — `estate_calendar` (Calendario y Visitas)

**Ubicación:** [estate_calendar/](estate_calendar/)
**Propósito:** Extiende el calendario de Odoo para gestionar visitas inmobiliarias con recordatorios por WhatsApp.

#### Modelos implementados

| Modelo | Descripción | Archivo |
|---|---|---|
| `calendar.event` (extendido) | Visita/cita con campos inmobiliarios | [models/calendar_event.py](estate_calendar/models/calendar_event.py) |
| `estate.whatsapp` | Envío de mensajes vía Meta WhatsApp Cloud API | [models/estate_whatsapp.py](estate_calendar/models/estate_whatsapp.py) |

#### Campos añadidos a `calendar.event`
- `property_id` — Propiedad a visitar
- `appointment_type` — visita / llamada / reunión / seguimiento
- `visit_state` — programada / realizada / cancelada / no_asistió
- `visit_rating` — Evaluación de 1 a 5 después de la visita
- `whatsapp_sent` — Flag de si ya se envió el recordatorio

#### Recordatorio automático por WhatsApp
Un cron job verifica cada hora las citas que empiezan en los próximos 60 minutos y envía automáticamente un mensaje de WhatsApp al cliente usando la **Meta WhatsApp Cloud API**.

---

### MÓDULO 4 — `estate_document` (Gestión Documental)

**Ubicación:** [estate_document/](estate_document/)
**Propósito:** Sistema completo de gestión documental vinculado a todas las entidades del negocio.

#### Modelos implementados

| Modelo | Descripción | Archivo |
|---|---|---|
| `estate.document` | Documento inmobiliario con ciclo de vida | [models/estate_document.py](estate_document/models/estate_document.py) |
| `estate.document.type` | Catálogo configurable de tipos de documento | [models/estate_document_type.py](estate_document/models/estate_document_type.py) |
| `estate.document.reject.wizard` | Wizard de rechazo con razón obligatoria | [models/estate_document.py](estate_document/models/estate_document.py) |
| `estate.contract` (extendido) | Añade `document_ids` y auto-crea placeholders al activar | [models/estate_contract.py](estate_document/models/estate_contract.py) |
| `res.partner` (extendido) | Añade carpeta unificada del cliente | [models/res_partner.py](estate_document/models/res_partner.py) |
| `crm.lead` (extendido) | Añade pestaña de documentos al lead | [models/crm_lead.py](estate_document/models/crm_lead.py) |

#### Ciclo de vida de un documento
```
[Pendiente] → subir archivo → [Recibido] → manager verifica → [Verificado] → [Archivado]
                                    ↓                 ↓
                                [Rechazado]  ← wizard con razón obligatoria
                                    ↓
                           reset → [Pendiente]
```

#### 25+ tipos de documento en 6 categorías
| Categoría | Ejemplos |
|---|---|
| Contrato | Contrato Firmado, Acuerdo de Arras, Adenda, Acuerdo de Confidencialidad |
| Identidad | Cédula de Identidad, Pasaporte, RUC |
| Propiedad | Escritura, Catastro, Habitabilidad, Licencia de Construcción, Planos |
| Financiero | Comprobante de Pago, Avalúo, Tasación Bancaria, Carta de Crédito |
| Legal | Poder Notarial, Certificado Matrimonial, Sucesión, No Adeudo |
| Otros | Fotografías, Otro |

Datos iniciales en: [data/document_types_data.xml](estate_document/data/document_types_data.xml)

#### OCR con Gemini Vision
Método `action_ocr_extract()` en `estate.document`:
1. Toma el archivo del campo `file` (ya subido)
2. Detecta el MIME type del archivo
3. Selecciona el prompt según la categoría del documento (contrato, identidad, propiedad, etc.)
4. Envía el archivo a **Gemini 2.5 Flash** con el archivo en base64
5. Parsea el JSON de la respuesta y lo guarda en `ocr_result`
6. Publica el resultado en el chatter del documento

Botón **"Extraer con IA"** visible en la ficha del documento cuando hay archivo cargado.

#### Confidencialidad con reglas de registro
- `public` → todos los usuarios
- `internal` → cualquier asesor
- `restricted` → solo asesor responsable + managers
- `confidential` → solo managers y admins

Implementado con `ir.rule` de Odoo en [security/document_record_rules.xml](estate_document/security/document_record_rules.xml) — el filtrado es a nivel de base de datos, no solo visual.

---

### MÓDULO 5 — `estate_reports` (Reportes y Dashboard)

**Ubicación:** [estate_reports/](estate_reports/)
**Propósito:** Dashboard en tiempo real, 12 tipos de reportes PDF/Excel y reporte de promedio de ventas.

#### Modelos / Wizards implementados

| Modelo | Descripción | Archivo |
|---|---|---|
| `estate.dashboard` | Dashboard con 40+ KPIs en tiempo real | [models/estate_dashboard.py](estate_reports/models/estate_dashboard.py) |
| `estate.sales.report.wizard` | Wizard de promedio de ventas con 9 KPIs | [wizards/estate_sales_report_wizard.py](estate_reports/wizards/estate_sales_report_wizard.py) |
| `estate.report.wizard` | Wizard para 12 tipos de reporte PDF/Excel | [wizards/estate_report_wizard.py](estate_reports/wizards/estate_report_wizard.py) |
| `estate.commission.wizard` | Wizard de liquidación de comisiones | [wizards/estate_commission_wizard.py](estate_reports/wizards/estate_commission_wizard.py) |

#### KPIs del Dashboard (`estate.dashboard`)
- Propiedades: total, disponibles, vendidas, arrendadas, estancadas (+45 días sin visita)
- Contratos: activos, por vencer en 30 días
- Financiero: comisiones del mes, ingresos, pagos pendientes, facturas vencidas
- Pipeline: ofertas activas, órdenes de venta
- Operacional: días promedio en mercado, citas del mes

Visualizaciones HTML generadas en el servidor:
- Mapa Leaflet con todas las propiedades (`_compute_map_html`)
- Ranking top-10 asesores (`_compute_advisor_ranking`)
- Tabla de ocupación de arriendos (`_compute_occupancy`)
- Comparativa precio AVM vs precio real (`_compute_avm_comparison`)
- Gráfico de ventas últimos 6 meses (`_compute_charts`)
- Embudo de conversión (`_compute_funnel`)

#### Reporte de Promedio de Ventas (`estate.sales.report.wizard`)
**Filtros:** Período (5 opciones), tipo de operación, tipo de propiedad, ciudad, asesores.

**9 KPIs calculados:**

| KPI | Fórmula |
|---|---|
| Precio promedio de venta | AVG(price) de propiedades cerradas en el período |
| Precio promedio listado | AVG(price) inicial antes de ajustes |
| % logrado vs listado | Σ(precio_cierre) / Σ(precio_listado) × 100 |
| Días promedio en mercado | AVG(days_on_market) |
| Precio mediano | MEDIAN(price) usando `statistics.median()` |
| Precio mínimo / máximo | MIN y MAX del período |
| Tasa de cierre | vendidas / (disponibles + vendidas) × 100 |
| Comparativa período anterior | % de cambio vs período equivalente anterior |

**Exportación:**
- PDF: template QWeb con KPI cards + estadísticos + top ciudades/asesores
- Excel: 2 hojas (KPIs + Detalle de propiedades)
- Controlador de descarga: [controllers/sales_report_controller.py](estate_reports/controllers/sales_report_controller.py)

#### 12 Tipos de Reporte (`estate.report.wizard`)
1. Propiedades Disponibles
2. Clientes Activos (Oportunidades)
3. Ventas por Período
4. Tiempo de Venta (días en mercado)
5. Visitas / Citas Realizadas
6. Contratos por Vencer (60 días)
7. Desempeño y Comisiones de Asesores
8. Análisis Geográfico y AVM
9. Retorno de Marketing (origen de leads)
10. Embudo de Conversión
11. Cartera por Asesor
12. Ocupación de Arriendos

---

### MÓDULO 6 — `estate_social` (Redes Sociales)

**Ubicación:** [estate_social/](estate_social/)
**Propósito:** Publicación automática de propiedades en Facebook e Instagram, y análisis de estadísticas.

#### Modelos implementados

| Modelo | Descripción | Archivo |
|---|---|---|
| `estate.social.publish` | Publicación de una propiedad en redes sociales | [models/estate_social_publish.py](estate_social/models/estate_social_publish.py) |
| `estate.social` | Configuración e integración con Meta Graph API | [models/estate_social.py](estate_social/models/estate_social.py) |
| `estate.facebook.stats` | Estadísticas de páginas e insights de Facebook | [models/estate_facebook_stats.py](estate_social/models/estate_facebook_stats.py) |
| `estate.instagram.stats` | Estadísticas de cuenta de Instagram | [models/estate_instagram_stats.py](estate_social/models/estate_instagram_stats.py) |
| `estate.social.followup` | Seguimiento de leads captados por redes sociales | [models/estate_social_followup.py](estate_social/models/estate_social_followup.py) |

---

### MÓDULO 7 — `estate_wordpress` (Sincronización WordPress)

**Ubicación:** [estate_wordpress/](estate_wordpress/)
**Propósito:** Sincronización bidireccional entre Odoo y el sitio WordPress con plugin Houzez.

#### Modelos implementados

| Modelo | Descripción | Archivo |
|---|---|---|
| `estate.wordpress.sync` | Lógica de publicación y actualización en WordPress REST API | [models/estate_wordpress_sync.py](estate_wordpress/models/estate_wordpress_sync.py) |
| `estate.wordpress.import` | Importación masiva de propiedades desde WordPress | [models/estate_wordpress_import.py](estate_wordpress/models/estate_wordpress_import.py) |
| `estate.wordpress.config` | Credenciales y configuración de la conexión | [models/estate_wordpress_config.py](estate_wordpress/models/estate_wordpress_config.py) |
| `estate.wordpress.link` | Vínculo entre propiedad Odoo y post WordPress | [models/estate_wordpress_link.py](estate_wordpress/models/estate_wordpress_link.py) |
| `estate.wp.agent` | Agente de sincronización automática | [models/estate_wp_agent.py](estate_wordpress/models/estate_wp_agent.py) |

#### Flujo de sincronización
1. Asesor guarda/modifica una propiedad en Odoo
2. El sistema detecta el cambio y llama a WordPress REST API
3. Si `wp_post_id` no existe → crea nuevo post en WordPress
4. Si existe → actualiza el post con los nuevos datos
5. WordPress actualiza el portal público automáticamente

**Webhook inverso:** cuando alguien llena el formulario de contacto en WordPress, Houzez envía un webhook a Odoo → se crea automáticamente un lead en el CRM.

**Controlador:** [controllers/main.py](estate_wordpress/controllers/main.py)

---

### MÓDULO 8 — `estate_portal` (Portal del Propietario)

**Ubicación:** [estate_portal/](estate_portal/)
**Propósito:** Extranet para que los propietarios consulten el estado de sus propiedades, contratos y pagos desde un navegador sin acceso al backend de Odoo.

**Controlador:** [controllers/portal.py](estate_portal/controllers/portal.py)

---

### MÓDULO 9 — `estate_ai_agent` (Agente Inteligente)

**Ubicación:** [estate_ai_agent/](estate_ai_agent/)
**Propósito:** Agente conversacional integrado en el ERP con soporte para Google Gemini y OpenAI.

#### Modelos implementados

| Modelo | Descripción | Archivo |
|---|---|---|
| `res.config.settings` (extendido) | Configuración del agente: proveedor, API key, modelo, temperatura | [models/estate_ai_config.py](estate_ai_agent/models/estate_ai_config.py) |
| `estate.ai.chat.history` | Historial de conversaciones por usuario | [models/estate_ai_chat.py](estate_ai_agent/models/estate_ai_chat.py) |
| `estate.contract` (extendido) | Método `action_generate_contract_ai` — redacta borrador de contrato con Gemini | [models/estate_ai_contract.py](estate_ai_agent/models/estate_ai_contract.py) |
| `estate.ai.memory` | Memoria persistente del agente por sesión | [models/estate_ai_memory.py](estate_ai_agent/models/estate_ai_memory.py) |

#### Endpoint REST principal
**Ruta:** `POST /estate/ai/chat`
**Autenticación:** usuario Odoo logueado
**Descripción:** Recibe un mensaje en lenguaje natural, ejecuta tool calls (buscar propiedades, crear leads, obtener estadísticas, etc.) y devuelve la respuesta del agente.

**Tools disponibles para el agente:**
- `search_properties` — busca propiedades con filtros
- `get_leads` — consulta leads del CRM
- `get_market_stats` — estadísticas del mercado
- `create_crm_activity` — crea actividad de seguimiento
- `create_lead` — registra nuevo lead
- `create_property` — registra nueva propiedad
- Y más...

#### Endpoint OCR
**Ruta:** `POST /estate_ai/ocr`
**Descripción:** Recibe un archivo (imagen o PDF), lo analiza con Gemini Vision y devuelve los datos estructurados en JSON.

#### Componentes OWL (Frontend)
- `ai_chat` — Widget de chat embebido en vistas Odoo
- `ai_chat_float` — Widget flotante disponible en toda la aplicación

**Ubicación:** [estate_ai_agent/static/](estate_ai_agent/static/)

#### Cron proactivo diario
Método `_cron_proactive_agent` en `estate.ai.chat.history`:
- Verifica pagos vencidos, propiedades estancadas, contratos por vencer, leads calientes sin actividad
- Envía notificación push a todos los managers con el resumen
- Se registra en el historial de conversaciones

---

## Resumen General

| Módulo | Requerimientos cubiertos | Archivos Python |
|---|---|---|
| `estate_management` | RF-01, RF-03 | ~13 modelos |
| `estate_crm` | RF-02 | ~5 modelos + 2 controllers |
| `estate_calendar` | RF-05 | ~3 modelos + 1 wizard |
| `estate_document` | RF-04 | ~6 modelos |
| `estate_reports` | RF-06 | 1 modelo + 3 wizards + 1 controller |
| `estate_social` | (adicional) | ~5 modelos |
| `estate_wordpress` | RF-07 | ~5 modelos + 1 controller |
| `estate_portal` | (adicional) | 1 controller |
| `estate_ai_agent` | RF-08 | ~5 modelos + 1 controller |

**Total módulos custom:** 9
**Stack tecnológico:** Odoo 19 · Python 3.11 · PostgreSQL 15 · OWL/JavaScript · Google Gemini API · OpenAI API · Meta WhatsApp Cloud API · WordPress REST API
