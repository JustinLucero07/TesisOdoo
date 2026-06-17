# Guía de Funcionalidades — Sistema Inmobiliario Odoo 19

> **Proyecto:** Tesis de Grado — Sistema ERP Inmobiliario  
> **URL:** http://localhost:8070 | **DB:** tesis_odoo19

---

## MÓDULOS Y UBICACIÓN EN PANTALLA

### Menú principal: **Inmobiliaria**

| Qué buscas | Dónde está | Módulo |
|---|---|---|
| Ver/crear propiedades | Inmobiliaria → Propiedades | `estate_management` |
| Ver ofertas y negociaciones | Inmobiliaria → Ofertas | `estate_management` |
| Ver contratos | Inmobiliaria → Contratos | `estate_management` |
| Ver pagos | Inmobiliaria → Pagos | `estate_management` |
| Ver comisiones de asesores | Inmobiliaria → Comisiones | `estate_management` |
| Ver gastos de propiedades | Inmobiliaria → Gastos | `estate_management` |
| Solicitudes de inquilinos | Inmobiliaria → Inquilinos | `estate_management` |
| Tasaciones / Avalúos | Inmobiliaria → Tasaciones | `estate_management` |
| Citas y visitas | Inmobiliaria → Planificación → Citas | `estate_calendar` |
| Dashboard KPI | Inmobiliaria → Inteligencia → Dashboard | `estate_reports` |
| Reportes analíticos | Inmobiliaria → Inteligencia → Analytics | `estate_reports` |
| Chat con IA | Inmobiliaria → IA → Chat | `estate_ai_agent` |
| Documentos | Inmobiliaria → Documentos | `estate_document` |
| Portal propietarios | http://localhost:8070/my/properties | `estate_portal` |

---

## LO QUE PEDISTE — DÓNDE ESTÁ

### ✅ Promedio de ventas / Reporte de ventas
**Ruta:** CRM → Reportes → **Negocios realizados**  
**Archivo:** `estate_crm/views/estate_crm_actions.xml` (action `action_crm_reports_deals`)  
Muestra pivot con asesor, tipo de pago, revenue promedio y comisiones. Filtrado a leads ganados (`is_won=True`).

---

### ✅ Hoja de Captación (NUEVO)
**Ruta:** Inmobiliaria → Propiedades → abrir propiedad → menú **Imprimir → Hoja de Captación**  
**Archivo:** `estate_management/report/estate_capture_sheet_report.xml`  
PDF con: datos de la propiedad, propietario, condiciones comerciales, exclusividad, checklist de documentación y firmas.

---

### ✅ Contratos con/sin exclusividad
**Ruta:** Inmobiliaria → Contratos → campo **Tipo de Contrato** (sale / alquiler / **exclusividad**)  
**Archivo:** `estate_management/models/estate_contract.py` — campo `contract_type`  
En la propiedad: campo `is_exclusive` (booleano) + `exclusive_user_id` (asesor que captó en exclusiva).

---

### ✅ Quién hizo el negocio / qué asesor
**Ruta 1:** Inmobiliaria → Dashboard → pestaña **Asesores** → ranking mensual con ventas, ingresos y comisiones.  
**Ruta 2:** CRM → Reportes → **Negocios realizados** → pivotear por `user_id`.  
**Archivo:** `estate_reports/models/estate_dashboard.py` (línea ~261)

---

### ✅ Fases del CRM (papeles, avalúo, minuta)
**Ruta:** CRM → Pipeline (kanban) — columnas:
1. Nuevo / Contacto Inicial
2. **Captación y Calificación**
3. Visita Realizada
4. Seguimiento
5. **Entrega de Papeles**
6. **Avalúo Realizado**
7. **Minuta Firmada**
8. Cierre Ganado

**Archivo:** `estate_crm/data/estate_crm_stage_data.xml`

---

### ✅ Asesor responsable de la propiedad
**Ruta:** Inmobiliaria → Propiedades → campo **Asesor Responsable** (`user_id`)  
Para exclusividad: campo **Asesor Exclusivo** (`exclusive_user_id`).  
**Archivo:** `estate_management/models/estate_property.py` líneas 541-551

---

### ✅ Necesidades / Demanda del cliente
**Ruta:** CRM → abrir oportunidad → sección **"Propiedad Buscada"** → campo **Necesidades del Cliente**  
**Archivo:** `estate_crm/models/crm_lead.py` — campo `client_needs`

---

### ✅ Se cerró de contado o crédito
**Ruta:** CRM → abrir oportunidad → sección **"Detalles de Cierre"** → campo **Tipo de Pago**  
**Archivo:** `estate_crm/models/crm_lead.py` — campo `closing_payment_type` (cash / credit)

---

### ✅ Tiempo promesa de compraventa / crédito
**Ruta:** CRM → abrir oportunidad → sección **"Detalles de Cierre"**  
- Campo **Tiempo estimado crédito** (`mortgage_time_estimated`)  
- Campo **Tiempo promesa compraventa** (`promissory_note_time`)  
**Archivo:** `estate_crm/models/crm_lead.py` líneas 55-57

---

### ✅ Subir contrato de arras / contrato firmado
**Ruta:** Inmobiliaria → Contratos → abrir contrato → campos binarios en el formulario  
- **Contrato de Arras** (`earnest_money_contract`) → adjunta PDF/scan  
- **Contrato Firmado** (`signed_contract`) → adjunta el contrato final  
**Archivo:** `estate_management/models/estate_contract.py` líneas 62-65

---

### ✅ Ventas por fuente de captación
**Ruta:** CRM → Reportes → **Ventas por Fuente**  
Muestra gráfico de torta y pivot con leads ganados por fuente (website, WP, WhatsApp, Instagram, Facebook, Google, Referido, Teléfono, Walk-in, Portal, IA, Otro).  
**Archivo:** `estate_crm/views/estate_crm_actions.xml` (action `action_crm_reports_sources`)

---

### ✅ Simulación de ofertas (contraoferta)
**Ruta:** Inmobiliaria → Ofertas → abrir oferta → campos:
- **Monto Ofrecido** (`offer_amount`)
- **Contraoferta** (`counteroffer_amount`)
- **Monto Final Acordado** (`final_agreed_amount`)
- **% Descuento** (`discount_pct`) — calculado automático

**Archivo:** `estate_management/models/estate_offer.py`

---

### ✅ Comisiones a asesores
**Ruta:** Inmobiliaria → Comisiones → crear → llenar monto de venta y % de comisión → **Aprobar** → **Generar Factura** (crea vendor bill al asesor)  
**Archivo:** `estate_management/models/estate_commission.py` — método `action_generate_invoice()`

---

### ✅ Estadísticas Instagram (ya existía)
**Ruta:** Inmobiliaria → Propiedad → botón **"Stats IG"** (solo aparece si está publicado en IG)  
**Archivo:** `estate_social/models/estate_instagram_stats.py`  
Métricas: Impresiones, Alcance, Likes, Comentarios, Compartidos, Guardados, Engagement Rate.

---

### ✅ Estadísticas Facebook / Meta (NUEVO)
**Ruta:** Inmobiliaria → Propiedad → botón **"Stats FB"** (aparece si `fb_published = True`)  
**Archivo:** `estate_social/models/estate_facebook_stats.py`  
Métricas: Impresiones, Alcance único, Clics, Reacciones (Like/Love/Haha/Wow), Compartidos, Engagement Rate, CTR.  
También en: **Inmobiliaria → Redes Sociales → Estadísticas Facebook** (listado general)

---

### ❌ Cotización — ELIMINADA del menú de impresión
La cotización ya no aparece en el menú **Imprimir** del lead de CRM.  
El código se conserva pero está desactivado.  
**Archivo:** `estate_crm/reports/estate_crm_quotation_report.xml` (binding removido)

---

## ARCHIVOS CLAVE POR FUNCIONALIDAD

```
estate_management/
├── models/
│   ├── estate_property.py          ← Modelo central (propiedades)
│   ├── estate_contract.py          ← Contratos (exclusividad, arras, firmado)
│   ├── estate_offer.py             ← Ofertas y simulación de negociación
│   ├── estate_commission.py        ← Comisiones a asesores
│   ├── estate_payment.py           ← Pagos
│   └── estate_appraisal.py         ← Avalúos
├── report/
│   ├── estate_contract_report.xml  ← PDF contrato de venta/alquiler
│   └── estate_capture_sheet_report.xml  ← PDF hoja de captación (NUEVO)
└── views/
    └── estate_property_views.xml   ← Formulario de propiedad

estate_crm/
├── models/crm_lead.py              ← Lead extendido (score, temp, necesidades, cierre)
├── data/estate_crm_stage_data.xml  ← 8 etapas del pipeline
└── views/
    ├── estate_crm_lead_views.xml   ← Formulario del lead con todas las secciones
    └── estate_crm_actions.xml      ← Acciones de reportes (ventas, fuentes, asesores)

estate_reports/
└── models/estate_dashboard.py     ← KPIs, ranking asesores, gráficos, alertas

estate_social/
├── models/
│   ├── estate_social_publish.py   ← Publicar en FB/IG + botón Stats FB (NUEVO)
│   ├── estate_instagram_stats.py  ← Estadísticas Instagram
│   └── estate_facebook_stats.py   ← Estadísticas Facebook (NUEVO)
└── views/
    ├── estate_instagram_stats_views.xml
    └── estate_facebook_stats_views.xml  ← (NUEVO)

estate_wordpress/
├── models/
│   ├── estate_wordpress_sync.py   ← Publicar propiedades en WordPress
│   └── estate_wordpress_import.py ← Importar propiedades desde WordPress (NUEVO)
```

---

## ACTUALIZAR MÓDULOS (después de cambios)

```bash
source /home/justin/Documentos/Tesis/venv19/bin/activate

# Para todos los cambios de esta sesión:
python /home/justin/Documentos/odoo19/odoo-bin \
  -c /home/justin/Documentos/Tesis/odoo19.conf \
  -d tesis_odoo19 \
  -u estate_management,estate_crm,estate_social,estate_wordpress \
  --stop-after-init
```

---

## FLUJO COMPLETO DE VENTA

```
1. Lead entra (fuente: website/WP/WhatsApp/etc.)
   └── CRM → Stage: Captación y Calificación
       ├── Asignar asesor responsable
       ├── Registrar necesidades y presupuesto
       └── AI Matchmaker busca propiedades compatibles

2. Visita agendada
   └── CRM → Stage: Visita Realizada
       ├── Recordatorio WhatsApp automático (1h antes)
       └── Post-visita: rating + resultado

3. Negociación
   └── Oferta → Contraoferta → Monto acordado
       └── CRM → Stage: Entrega de Papeles
           ├── Avalúo (CRM → Stage: Avalúo Realizado)
           └── Minuta (CRM → Stage: Minuta Firmada)

4. Cierre
   └── Contrato firmado + contrato de arras subido
       ├── Tipo: contado / crédito hipotecario
       └── Tiempo de promesa / tiempo de crédito

5. Post-venta
   └── Factura generada → Pago registrado
       └── Comisión calculada → Vendor bill al asesor
```
