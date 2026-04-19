# Sistema de Gestión Inmobiliaria — Tesis de Grado

Suite ERP modular para gestión integral de bienes raíces, construida sobre **Odoo 19 Community Edition**.

> **URL:** http://localhost:8070 · **Base de datos:** `tesis_odoo19` · **Puerto:** 8070

---

## Índice

1. [Arranque rápido](#1-arranque-rápido)
2. [Arquitectura de módulos](#2-arquitectura-de-módulos)
3. [Modelo de datos central](#3-modelo-de-datos-central)
4. [Flujo de Venta](#4-flujo-de-venta)
5. [Flujo de Arriendo](#5-flujo-de-arriendo)
6. [Módulos y funcionalidades](#6-módulos-y-funcionalidades)
7. [Automatizaciones (Cron Jobs)](#7-automatizaciones-cron-jobs)
8. [Dashboard e Inteligencia](#8-dashboard-e-inteligencia)
9. [Agente IA](#9-agente-ia)
10. [Integraciones externas](#10-integraciones-externas)
11. [Seguridad y Roles](#11-seguridad-y-roles)
12. [Comandos de administración](#12-comandos-de-administración)

---

## 1. Arranque rápido

```bash
# Activar entorno virtual
source /home/justin/Documentos/Tesis/venv19/bin/activate

# Iniciar servidor
python /home/justin/Documentos/odoo19/odoo-bin -c /home/justin/Documentos/Tesis/odoo19.conf

# Acceder en: http://localhost:8070
```

### Instalar / actualizar módulos

```bash
# Actualizar módulos específicos
python /home/justin/Documentos/odoo19/odoo-bin \
  -c /home/justin/Documentos/Tesis/odoo19.conf \
  -d tesis_odoo19 \
  -u estate_management,estate_crm \
  --stop-after-init

# Instalar todos los módulos desde cero
python /home/justin/Documentos/odoo19/odoo-bin \
  -c /home/justin/Documentos/Tesis/odoo19.conf \
  -d tesis_odoo19 \
  -i estate_management,estate_crm,estate_reports,estate_ai_agent,estate_document,estate_calendar,estate_social,estate_portal,estate_wordpress \
  --stop-after-init
```

### Dependencias Python

```bash
source venv19/bin/activate
pip install qrcode[pil] google-genai openai openpyxl psycopg2-binary requests
```

---

## 2. Arquitectura de módulos

```
estate_management      ← MÓDULO BASE (propiedades, contratos, pagos, comisiones, AVM, QR)
├── estate_crm         ← CRM: lead scoring, budget matching, tips de negociación IA
├── estate_calendar    ← Visitas: calendar.event + recordatorios WhatsApp (CallMeBot)
├── estate_document    ← Documentos vinculados a propiedades/leads/contactos
├── estate_reports     ← Dashboard KPI, PDF contratos, exportación Excel
├── estate_social      ← Botones de compartir: Facebook / WhatsApp / Twitter
├── estate_wordpress   ← Publicación y sincronización automática con WordPress REST API
├── estate_portal      ← Portal/extranet para propietarios
└── estate_ai_agent    ← Chat IA (Gemini / OpenAI) + widget OWL + endpoint REST
```

### Árbol de dependencias Odoo

`estate_management` depende de: `base`, `mail`, `sale_management`, `account`, `portal`, `calendar`, `hr_attendance`

---

## 3. Modelo de datos central

### `estate.property` — entidad principal

| Campo | Descripción |
|---|---|
| `title` | Nombre comercial de la propiedad |
| `offer_type` | `sale` (Venta) / `rent` (Arriendo) |
| `state` | `available → reserved → sold / rented` |
| `price` | Precio de venta o renta mensual |
| `owner_id`, `buyer_id`, `user_id` | Propietario, comprador, asesor responsable |
| `avm_estimated_price` | Valoración automática de mercado (AVM) |
| `qr_image` | Código QR generado con datos + URL mapa |
| `sale_count`, `property_invoice_count` | Smart buttons hacia órdenes y facturas |
| `wp_published`, `wp_post_id` | Estado de publicación en WordPress |

### Trazabilidad completa por operación

```
res.partner (cliente)
    │
    ├── crm.lead (oportunidad)           ← lead_id
    │       └── estate.property.offer    ← offer_id
    │               ├── estate.contract  ← offer_id / sale_order_id
    │               │     └── estate.payment → account.move
    │               └── sale.order       ← property_id / lead_id
    │                     └── account.move (factura nativa)
    │
    └── estate.property
            ├── calendar.event (visitas)
            ├── estate.appraisal (tasaciones)
            ├── estate.property.expense (gastos)
            └── estate.commission (comisiones)
```

---

## 4. Flujo de Venta

```
1. CRM Lead  →  Oferta presentada  →  Contraoferta  →  Oferta ACEPTADA
                                                              │
                          ┌───────────────────────────────────┤
                          │                                   │
               [Contrato de Compraventa]          [Orden de Venta Odoo]
               (estate.contract)                  (sale.order)
                          │                                   │
                  Pagos del contrato               Factura desde la orden
                  (estate.payment)                 (account.move)
                          │                                   │
                          └───────────── FACTURA PAGADA ──────┘
                                               │
                                    Propiedad → VENDIDA ✓
                                    (automático vía cron o botón)
```

**Notas:**
- La **Oferta** al aceptarse reserva la propiedad y rechaza las demás ofertas activas
- El botón **"Crear Orden de Venta"** solo aparece en ofertas aceptadas de propiedades en Venta
- La orden de venta se **vincula automáticamente** al lead CRM de origen
- Al **confirmar la orden**: email al cliente + notificación en chatter del lead y la propiedad
- La factura pagada puede marcar la propiedad como Vendida: botón manual o cron diario

---

## 5. Flujo de Arriendo

```
1. CRM Lead  →  Oferta presentada  →  Oferta ACEPTADA
                                             │
                                  [Contrato de Arriendo]
                                  (estate.contract, tipo=rent)
                                  · fecha inicio / vencimiento
                                  · monto mensual
                                             │
                                  Factura mensual (manual o cron)
                                  (account.move out_invoice)
                                             │
                                  Pago registrado (estate.payment)
                                             │
                                    Propiedad → ARRENDADA ✓
                                             │
                                  Al vencer: propiedad → DISPONIBLE (manual)
```

**Notas:**
- Botón **"Generar Factura Mensual"** en contratos de arriendo activos
- Cron mensual automático el 1ro de cada mes (evita duplicados)
- El "Generar Contrato" detecta automáticamente el tipo según la propiedad (venta/arriendo)

---

## 6. Módulos y funcionalidades

### `estate_management` — Módulo base

**Menú:** `Inmobiliaria`

| Sección | Funcionalidad |
|---|---|
| **Propiedades** | CRUD completo, galería, estados, AVM, ROI, mapa OpenStreetMap, tour 360°, QR, score |
| **Ofertas** | Pipeline kanban por estado, contraoferta, botón "Crear Orden/Contrato" |
| **Contratos** | Compraventa / Arriendo / Exclusividad, firma digital, generación de facturas mensuales |
| **Pagos** | Cuotas por contrato, estado (pendiente/pagado/anulado), vinculación a factura |
| **Comisiones** | Por asesor, tipo (venta/arriendo/bono), estado (borrador/aprobada/pagada) |
| **Gastos** | Gastos de mantenimiento por propiedad |
| **Tasaciones** | Historial de avalúos, comparables de mercado |
| **Inquilinos** | Solicitudes de mantenimiento de arrendatarios |
| **Facturación** | Facturas vinculadas a propiedad + QR + botón "Marcar Vendida/Arrendada" |
| **Ventas** | Órdenes de venta con campo propiedad + lead CRM + email automático al confirmar |

### `estate_crm` — CRM Inmobiliario

**Menú:** `CRM` (integrado con CRM nativo de Odoo)

- Lead scoring A/B/C y temperatura (frío/tibio/caliente/hirviendo)
- Match automático propiedad-presupuesto (≥95% → crea lead automáticamente)
- Tips de negociación generados por IA
- Canal de captación: web, WhatsApp, Instagram, Google, referido, etc.
- Estadísticas: velocidad del lead, días sin actividad, visitas completadas

### `estate_calendar` — Visitas y Citas

**Menú:** `Inmobiliaria > Planificación`

- Visitas vinculadas a propiedad y lead CRM
- Estados: programada → confirmada → realizada → cancelada
- Calificación post-visita (1–5 estrellas)
- Recordatorios WhatsApp 1h antes vía CallMeBot API

### `estate_reports` — Reportes e Inteligencia

**Menú:** `Inmobiliaria > Inteligencia`

- **Dashboard KPI** con pipeline comercial completo:
  - Ofertas activas / Contratos activos / Órdenes confirmadas / Facturas pendientes ($)
  - Comisiones del mes / Ventas cerradas / Pipeline activo
  - Inventario: total / disponibles / vendidas / arrendadas
  - Mapa geográfico interactivo (Leaflet)
  - Ranking de asesores del mes (top 10)
  - Filtro por asesor
- **Análisis gráficos** (7 vistas): propiedades, contratos, pagos, ofertas, gastos, tasaciones, inquilinos
- **Exportación Excel** de datos
- **Reporte PDF** de contrato
- **Reporte de propietarios**

### `estate_ai_agent` — Agente de Inteligencia Artificial

**Menú:** `Inmobiliaria > IA` + widget flotante en toda la aplicación

- Chat con IA (Google Gemini o OpenAI)
- Genera reportes con gráficos (barras, circulares, líneas) directamente en el chat
- Tool calling: puede consultar datos reales del sistema (propiedades, ventas, comisiones, etc.)
- Análisis de imágenes de propiedades con Google Gemini Vision

### `estate_document` — Gestión Documental

**Menú:** `Inmobiliaria > Documentos`

- Documentos vinculados a propiedades, leads y contactos
- Tipos: contrato, escritura, plano, foto, otros

### `estate_social` — Redes Sociales

- Botones de compartir en la vista de propiedad: Facebook, WhatsApp, Twitter
- Comparte título, precio y URL de la propiedad

### `estate_wordpress` — Integración WordPress

**Menú:** `Inmobiliaria > Configuración > WordPress`

- Publicación automática de propiedades al WordPress via REST API
- Sincronización de estado: disponible/vendida/arrendada
- Compatible con tema Houzez

### `estate_portal` — Portal del Propietario

- Acceso externo para propietarios a ver sus propiedades y contratos
- Extranet con autenticación de portal Odoo

---

## 7. Automatizaciones (Cron Jobs)

`Ajustes > Técnico > Automatización > Acciones Planificadas`

| Nombre | Frecuencia | Función |
|---|---|---|
| Generar Facturas Mensuales de Arriendo | Mensual (día 1) | Crea facturas para contratos de arriendo activos |
| Sincronizar Estado Propiedad desde Facturas | Diario | Marca propiedades como Vendida/Arrendada al pagar factura |
| Verificar Vencimientos de Contratos | Diario | Alerta de contratos próximos a vencer (30 días) |
| Alertas de Pagos Vencidos | Diario | Crea actividades para pagos pendientes vencidos |
| Alertas Inteligentes de Precio | Semanal | Detecta propiedades con precio alto vs mercado (45+ días) |
| Alerta Propiedades Estancadas | Cada 3 días | Detecta propiedades 45+ días sin visitas |
| Reporte Mensual por Email | Mensual | Envía resumen de KPIs a administradores |
| Recordatorios WhatsApp de Visitas | Cada hora | Envía recordatorio 1h antes de la cita vía CallMeBot |

---

## 8. Dashboard e Inteligencia

**Ruta:** `Inmobiliaria > Dashboard`

El dashboard centraliza toda la información operativa y financiera:

```
┌─────────────────────────────────────────────────────────┐
│           PIPELINE COMERCIAL                            │
│  Ofertas activas | Contratos | Órdenes | Fact. pendiente│
├─────────────────────────────────────────────────────────┤
│           KPIs FINANCIEROS                              │
│  Comisiones mes | Ventas cerradas | Pipeline activo     │
├───────────────────────┬─────────────────────────────────┤
│  MAPA GEOGRÁFICO      │  OPERACIONES Y LEADS            │
│  (propiedades con     │  Citas realizadas               │
│   lat/lng en Leaflet) │  Contratos por vencer           │
│                       │  Días promedio en mercado       │
├───────────────────────┴─────────────────────────────────┤
│  INVENTARIO           │  RANKING ASESORES (top 10)      │
│  Total/Disp./Vend./   │  🥇🥈🥉 ventas + comisiones    │
│  Arrendadas           │  del mes actual                 │
└───────────────────────┴─────────────────────────────────┘
```

**Filtro por asesor:** Todas las métricas se pueden filtrar por un asesor específico.

---

## 9. Agente IA

**Configuración:** `Inmobiliaria > Configuración > Config IA`

| Campo | Descripción |
|---|---|
| Proveedor | Google Gemini o OpenAI |
| API Key | Clave del proveedor |
| Modelo | ej. `gemini-2.0-flash`, `gpt-4o` |

**Capacidades del chat:**

- Responde preguntas sobre propiedades, contratos, clientes
- Genera reportes con datos reales del sistema en tiempo real
- Visualiza datos con gráficos:
  - `[GRAFICO:barra,Label1:Val1,Label2:Val2]` → gráfico de barras horizontal
  - `[GRAFICO:circular,Label1:Val1,Label2:Val2]` → tarjetas porcentuales
  - `[GRAFICO:linea,Label1:Val1,Label2:Val2]` → gráfico de línea SVG
- Analiza imágenes de propiedades (solo Gemini con Vision)

**Widget flotante:** disponible en toda la aplicación (esquina inferior derecha)

---

## 10. Integraciones externas

### WhatsApp (CallMeBot)
- Configurar en: `Inmobiliaria > Configuración > Config WhatsApp`
- API gratuita de CallMeBot — requiere registro previo del número
- Envía recordatorios automáticos 1h antes de cada visita

### WordPress / Houzez
- Configurar en: `Inmobiliaria > Configuración > WordPress`
- Requiere: URL del sitio, usuario y contraseña de aplicación WordPress
- Publica automáticamente propiedades marcadas con "Publicar en WordPress"

### Google Gemini / OpenAI
- Configurar en: `Inmobiliaria > Configuración > Config IA`
- Se usa para: tips de negociación, descripción de imágenes, chat IA

---

## 11. Seguridad y Roles

| Rol | Acceso |
|---|---|
| **Agente Inmobiliario** | Sus propias propiedades, leads y citas. Registra asistencia propia. |
| **Manager Inmobiliario** | Todo el equipo. Gestiona asistencias del equipo. |
| **Administrador Inmobiliario** | Acceso total. Configuración. Administra asistencias. |

Los grupos de asistencia (`hr_attendance`) se propagan automáticamente desde los grupos inmobiliarios mediante `implied_ids`.

---

## 12. Comandos de administración

### Iniciar servidor

```bash
source /home/justin/Documentos/Tesis/venv19/bin/activate
python /home/justin/Documentos/odoo19/odoo-bin -c /home/justin/Documentos/Tesis/odoo19.conf
```

### Actualizar módulos

```bash
python /home/justin/Documentos/odoo19/odoo-bin \
  -c /home/justin/Documentos/Tesis/odoo19.conf \
  -d tesis_odoo19 \
  -u estate_management \
  --stop-after-init
```

### Ejecutar pruebas

```bash
python /home/justin/Documentos/odoo19/odoo-bin \
  -c /home/justin/Documentos/Tesis/odoo19.conf \
  -d tesis_odoo19 \
  --test-enable \
  --stop-after-init \
  -u estate_management
```

### Instalar dependencias Python

```bash
source /home/justin/Documentos/Tesis/venv19/bin/activate
pip install qrcode[pil] google-genai openai openpyxl psycopg2-binary requests
```

---

*Proyecto de Tesis de Grado — Sistema de Gestión Inmobiliaria sobre Odoo 19 Community Edition*
