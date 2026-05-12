# Dónde encontrar y cómo funcionan — Contratos / Documentos / Reportes

> Guía práctica: para cada punto de la propuesta, aquí está **dónde hacer clic en el sistema** y **qué archivo del código lo implementa**.

---

## CONTRATOS — `estate.contract`

### ¿Dónde lo encuentro en pantalla?

Menú principal → **Inmobiliaria → Contratos**

O desde una **Propiedad**: botón smart-button `[N Contratos]` en la parte superior de la ficha.

O desde una **Oferta aceptada**: cuando aceptas una oferta, aparece un **banner verde** en el contrato recién creado y un mensaje en el chatter del lead con link directo "Abrir contrato".

---

### Vista lista de contratos

**Qué ves:** tabla con columnas Referencia, Propiedad, Cliente, Tipo, Fecha Inicio, Fecha Fin, Monto, Total Pagado, Estado.

**Decoraciones de color:**
- Verde = Activo
- Amarillo/naranja = Suspendido o En Renovación
- Gris = Cancelado / Renovado

**Filtros disponibles** (botón 🔍):
- Por estado: Activo, Borrador, Por vencer (30 días), Este mes, Este año
- Agrupar por: Tipo, Estado, Propiedad, Mes

**Código:** [estate_management/views/estate_contract_views.xml](estate_management/views/estate_contract_views.xml) — vista `estate_contract_view_tree`

---

### Ficha del contrato (vista form)

Al abrir un contrato ves esto, de arriba abajo:

#### 1. Barra de estado (statusbar)
```
[Borrador] → [Activo] → [Suspendido] ↔ [En Renovación] → [Renovado]
                       ↘ [Vencido]
             [Cancelado] (en cualquier momento)
```
Haz clic en un estado para saltar directamente a él (si la transición es válida).

**Código:** [estate_management/models/estate_contract.py](estate_management/models/estate_contract.py) — diccionario `_VALID_STATE_TRANSITIONS` y métodos `action_activate`, `action_suspend`, `action_resume_active`, `action_start_renewal`, `action_create_renewal`, `action_set_expired`, `action_cancel`

#### 2. Botones de acción (header)
Cambian según el estado actual:

| Estado actual | Botones visibles |
|---|---|
| Borrador | **Activar** |
| Activo | **Suspender**, Iniciar Renovación, Cancelar |
| Suspendido | **Reanudar**, Cancelar |
| En Renovación | **Crear Renovación**, Volver a Activo, Cancelar |
| Vencido | Reset a Borrador, Iniciar Renovación |

#### 3. Smart-buttons (íconos arriba a la derecha)
- **[N Pagos]** — abre lista de pagos del contrato
- **[N Facturas]** — abre facturas de cuenta (account.move)
- **[Ver Oferta]** — abre la oferta de origen (solo si tiene `offer_id`)
- **[N Documentos]** — abre documentos vinculados a este contrato

**Código:** [estate_management/models/estate_contract.py](estate_management/models/estate_contract.py) — métodos `_compute_payment_count`, `_compute_invoice_count`, `action_view_payments`, `action_view_invoices`, `action_view_offer`

#### 4. Pestañas de la ficha

**Pestaña ✍️ Firma del Cliente** (siempre visible)
- Widget de firma digital dibujable
- Si está vacío, muestra instrucciones al asesor
- Al firmar guarda: imagen de la firma + fecha automática (`signature_date`)

**Pestaña 💰 Pagos**
- Lista editable de pagos del contrato
- Columnas: Referencia, Fecha, Monto, Estado, Notas
- Botones por fila: **Marcar Pagado**, **Facturar**
- Código: modelo `estate.payment` en [estate_management/models/estate_payment.py](estate_management/models/estate_payment.py)

**Pestaña 📂 Documentos del Contrato**
- Lista de `estate.document` donde `contract_id = este contrato`
- Puedes subir documentos directamente desde aquí
- Ver sección DOCUMENTOS más abajo para el ciclo de vida

**Pestaña 📝 Notas / Cláusulas**
- Editor HTML para notas y cláusulas adicionales

**Pestaña 🔄 Renovaciones** (visible solo si tiene contratos hijos)
- Lista de contratos de renovación enlazados por `child_contract_ids`

**Pestaña 📂 Anexos heredados** (visible solo si tiene archivos legacy)
- Muestra los campos Binary originales (`earnest_money_contract`, `signed_contract`)
- Son los documentos del sistema anterior, antes de la migración

#### 5. Banners contextuales
- **Banner verde**: "Contrato creado desde oferta" — aparece la primera vez que abres el contrato recién creado
- **Banner naranja**: cuando el contrato está suspendido
- **Banner azul info**: cuando el contrato es una renovación (muestra badge "Renovación de CT-XXXX")

---

### Numeración automática
Los contratos se numeran automáticamente: `CONT-2026-0001`, `CONT-2026-0002`, etc.
Los pagos: `PAG-2026-0001`, etc.

**Código:** [estate_management/data/sequences.xml](estate_management/data/sequences.xml) (o similar)

---

### Migrar archivos viejos (Binary → Documentos)
Si tienes contratos con archivos en los campos legacy, el método `_migrate_binary_to_documents()` convierte esos archivos en registros de `estate.document` correctamente vinculados. Es idempotente (puedes correrlo varias veces sin duplicar).

**Código:** [estate_management/models/estate_contract.py](estate_management/models/estate_contract.py) — método `_migrate_binary_to_documents`

---

## DOCUMENTOS — `estate.document`

### ¿Dónde lo encuentro en pantalla?

**Desde el menú:** Inmobiliaria → Documentos (si existe menú directo)

**Desde una Propiedad:** smart-button **[N Documentos]** arriba en la ficha

**Desde un Cliente (res.partner):**
- Smart-button **[N Documentos]** → documentos vinculados directamente al cliente
- Smart-button **📂 Carpeta completa** → TODOS los documentos del cliente (propiedades + leads + contratos + identidad)

**Desde un Contrato:** pestaña **📂 Documentos del Contrato** (ver arriba)

**Desde un Lead/Oportunidad:** pestaña **📂 Documentos** en el form del lead

---

### Vista Kanban (por defecto)
Los documentos se muestran en kanban **agrupado por categoría**:
- 📝 Contratos
- 🪪 Identidad
- 🏠 Propiedad
- 💰 Financiero
- ⚖️ Legal
- 📁 Otros

Cada tarjeta muestra: nombre, tipo, estado (badge coloreado), propiedad o cliente vinculado, fecha, tamaño del archivo, nivel de confidencialidad.

**Código:** [estate_document/views/estate_document_views.xml](estate_document/views/estate_document_views.xml) — vista `estate_document_view_kanban`

---

### Vista Lista
Columnas + decoraciones de color por estado:
- Verde = Verificado
- Azul = Recibido
- Gris = Pendiente / Archivado
- Rojo = Rechazado

**Código:** [estate_document/views/estate_document_views.xml](estate_document/views/estate_document_views.xml) — vista `estate_document_view_tree`

---

### Ciclo de vida de un documento

```
[Pendiente] → subir archivo → [Recibido] → manager verifica → [Verificado] → [Archivado]
                                               ↓                    ↓
                                           [Rechazado] ←←←←←←←←←←←←
                                               ↓
                                         reset → [Pendiente]
```

**En pantalla:**
- Cuando subes un archivo (`file`), el sistema cambia automáticamente de Pendiente a **Recibido**
- El botón **Verificar** solo aparece a usuarios con grupo `estate_group_manager`
- El botón **Rechazar** abre un wizard donde debes escribir la razón obligatoriamente
- El botón **Archivar** mueve a Archivado (reversible con "Volver a Pendiente")

**Código:**
- [estate_document/models/estate_document.py](estate_document/models/estate_document.py) — métodos `action_mark_received`, `action_verify`, `action_reject`, `action_archive_doc`, `action_reset_to_pending`
- [estate_document/models/estate_document.py](estate_document/models/estate_document.py) — wizard `estate.document.reject.wizard`

---

### Tipos de documento

**Dónde configurarlos:** Inmobiliaria → Configuración → Tipos de Documento

Son un **modelo configurable** (no una lista fija). Ya vienen 25+ tipos predefinidos:

| Categoría | Ejemplos |
|---|---|
| **Contrato** | Contrato Firmado, Acuerdo de Arras, Adenda, Acuerdo de Confidencialidad |
| **Identidad** | Cédula de Identidad, Pasaporte, RUC |
| **Propiedad** | Escritura, Catastro, Habitabilidad, Licencia de Construcción, Planos |
| **Financiero** | Comprobante de Pago, Avalúo, Tasación Bancaria, Carta de Crédito |
| **Legal** | Poder Notarial, Certificado Matrimonial, Sucesión, No Adeudo |
| **Otros** | Fotografías, Otro |

Puedes añadir más tipos desde esa vista de configuración (solo managers).

**Código:** [estate_document/models/estate_document_type.py](estate_document/models/estate_document_type.py) y [estate_document/data/document_types_data.xml](estate_document/data/document_types_data.xml)

---

### Confidencialidad

Cada documento tiene un campo **Nivel de Confidencialidad**:

| Nivel | Quién puede ver el archivo |
|---|---|
| `Público` | Todos los usuarios |
| `Interno` | Cualquier asesor del sistema |
| `Restringido` | Solo el asesor responsable + managers |
| `Confidencial` | Solo managers y administradores |

Está implementado con `ir.rule` (reglas de registro de Odoo), así que el filtrado es automático — un usuario sin permiso directamente no ve el registro.

**Código:** [estate_document/security/document_record_rules.xml](estate_document/security/document_record_rules.xml)

---

### Auto-creación al activar un contrato

Cuando haces clic en **Activar** en un contrato, el sistema crea automáticamente **2 documentos placeholder** en estado `pendiente`:
1. **Contrato Firmado** (tipo: `contract_signed`) — recordatorio para subir el PDF firmado
2. **Cédula del Cliente** (tipo: `client_id_card`) — recordatorio para subir la identificación

Estos aparecen inmediatamente en la pestaña "📂 Documentos del Contrato".

**Código:** [estate_document/models/estate_contract.py](estate_document/models/estate_contract.py) — override de `action_activate`

---

### Validaciones de archivos

- **Extensiones permitidas:** `.pdf`, `.doc`, `.docx`, `.xls`, `.xlsx`, `.jpg`, `.png`, `.gif`, `.webp`
- **Tamaño máximo:** 10 MB por archivo
- El sistema rechaza el guardado si se viola alguna de estas reglas

**Código:** [estate_document/models/estate_document.py](estate_document/models/estate_document.py) — método `_check_file_type_and_size`

---

### Filtros de búsqueda disponibles

En la barra de búsqueda de documentos:
- Por estado: Pendiente, Recibido, Verificado, Rechazado
- Por categoría de tipo
- Confidencial (muestra solo restringidos/confidenciales)
- **Expira en 30 días** — para certificados con `expiration_date` próximo

---

### Carpeta completa del cliente

En la ficha de un **Contacto/Cliente** (res.partner), smart-button **📂 Carpeta completa**:

Muestra en vista kanban **todos** los documentos relacionados con ese cliente:
- Documentos con `partner_id = cliente`
- Documentos de propiedades donde es propietario o comprador
- Documentos de leads donde es el cliente
- Documentos de contratos donde es el cliente

Todo agrupado por categoría en una sola vista.

**Código:** [estate_document/models/res_partner.py](estate_document/models/res_partner.py) — método `action_view_full_folder`

---

## REPORTES DE VENTAS — `estate_reports`

### ¿Dónde lo encuentro en pantalla?

**Dashboard general:** Menú → **Dashboard** (o Inmobiliaria → Dashboard)

**Reporte de Promedio de Ventas:** Menú → Reportes → **📊 Promedio de Ventas**

**Otros reportes:** Menú → Reportes → **Generar Reportes**

**Liquidación de Comisiones:** Menú → Reportes → **Liquidación de Comisiones**

---

### Dashboard general

Al abrir el Dashboard ves todos los KPIs en tiempo real:

**KPIs de propiedades:**
- Total propiedades / Disponibles / Vendidas / Arrendadas
- Propiedades estancadas (sin visita en 45+ días)
- Contratos por vencer (próximos 30 días)

**KPIs financieros:**
- Comisiones del mes
- Ingresos ganados (ventas del mes)
- Pagos pendientes / facturas vencidas

**KPIs de pipeline:**
- Ofertas activas
- Contratos activos
- Órdenes de venta

**Visualizaciones:**
- Mapa Leaflet con propiedades
- Ranking de asesores (top 10)
- Tabla de ocupación de arriendos
- Comparativa AVM (precio estimado vs precio real)
- Gráfico de ventas (últimos 6 meses)
- Gráfico de leads por fuente
- Embudo de conversión
- Tendencias período actual vs anterior

**Filtros del dashboard:**
- Por asesor (`filter_user_id`)
- Por período: Mes actual, Trimestre, Año, Mes anterior, Personalizado

Cada número del dashboard es **clicable** → te lleva a la lista filtrada correspondiente.

**Código:** [estate_reports/models/estate_dashboard.py](estate_reports/models/estate_dashboard.py)

---

### Reporte de Promedio de Ventas (wizard)

**Cómo abrirlo:** Reportes → 📊 Promedio de Ventas

Se abre un **wizard con filtros** en la parte superior:

| Filtro | Opciones |
|---|---|
| Período | Últimos 30 días / 90 días / Trimestre / Año / Personalizado |
| Tipo de operación | Solo ventas / Solo alquileres / Ambos |
| Tipo de propiedad | Selección múltiple |
| Ciudad | Texto libre |
| Asesores | Selección múltiple |

Después de configurar los filtros, el wizard calcula automáticamente:

#### Tab 📈 Resumen — 9 KPIs con comparativa

| KPI | Qué mide |
|---|---|
| N° de operaciones | Cuántas propiedades vendidas/alquiladas en el período |
| Precio promedio de venta | AVG del precio de cierre |
| Precio promedio listado | AVG del precio inicial |
| % logrado vs listado | Qué % del precio pedido se obtuvo |
| Días promedio en mercado | Cuánto tardaron en venderse |
| Precio mediano | Mediana (elimina sesgos de outliers) |
| Precio mínimo / máximo | Rango del período |
| Tasa de cierre | % de propiedades disponibles que se cerraron |

Cada KPI muestra una **flecha ↑ o ↓** con el % de cambio vs el período anterior equivalente.

#### Tab 📋 Detalle
Botón "Ver propiedades del período" → abre lista filtrada de propiedades vendidas/alquiladas.

#### Tab 📊 Datos crudos
JSON con datos para gráficos: top 5 ciudades, distribución por tipo, ranking de asesores. Solo visible en modo desarrollador.

#### Tab 📥 Exportar
- **Botón PDF** → genera reporte ejecutivo QWeb con KPI cards + estadísticos + top ciudades/asesores. Muestra qué filtros se aplicaron.
- **Botón Excel** → descarga archivo `.xlsx` con 2 hojas: KPIs (con comparativa) y Detalle (todas las propiedades)

**Si no hay datos:** aparece un banner amigable indicando que no hay ventas en ese período.

**Código:**
- [estate_reports/wizards/estate_sales_report_wizard.py](estate_reports/wizards/estate_sales_report_wizard.py) — modelo y lógica
- [estate_reports/wizards/estate_sales_report_wizard_views.xml](estate_reports/wizards/estate_sales_report_wizard_views.xml) — vista
- [estate_reports/controllers/sales_report_controller.py](estate_reports/controllers/sales_report_controller.py) — endpoint descarga Excel (`/estate_reports/sales_report_xlsx/{wizard_id}`)

---

### Generar Reportes (12 tipos)

**Cómo abrirlo:** Reportes → Generar Reportes

Wizard con selector de tipo de reporte y filtros de fecha. Genera PDF o Excel.

| # | Reporte | Qué muestra |
|---|---|---|
| 1 | Propiedades Disponibles | Inventario actual con características |
| 2 | Clientes Activos | Oportunidades/leads activos en CRM |
| 3 | Ventas por Período | Propiedades vendidas con precio y asesor |
| 4 | Tiempo de Venta | Días en mercado por tipo y ciudad |
| 5 | Visitas / Citas | Citas realizadas con rating y notas |
| 6 | Contratos por Vencer | Contratos que vencen en los próximos 60 días |
| 7 | Desempeño y Comisiones | Por asesor: volumen, comisión, tiempo promedio |
| 8 | Análisis Geográfico (AVM) | Precio estimado vs real por zona |
| 9 | Retorno de Marketing | Leads por fuente y su conversión |
| 10 | Embudo de Conversión | Lead → Oferta → Contrato → Venta |
| 11 | Cartera por Asesor | Propiedades asignadas a cada asesor |
| 12 | Ocupación de Arriendos | Tasa de ocupación de propiedades en arriendo |

El Excel incluye gráficos integrados (pie, barras, columnas según el tipo).

**Código:** [estate_reports/wizards/estate_report_wizard.py](estate_reports/wizards/estate_report_wizard.py)

---

### Liquidación de Comisiones

**Cómo abrirlo:** Reportes → Liquidación de Comisiones

Filtros: asesor (opcional, vacío = todos), fecha desde, fecha hasta, incluir borradores.

Genera un PDF de liquidación por asesor con detalle de comisiones.

**Código:** [estate_reports/wizards/estate_commission_wizard.py](estate_reports/wizards/estate_commission_wizard.py)

---

### Reporte mensual automático (cron)

El sistema envía automáticamente un email mensual a los administradores con:
- Alertas críticas (contratos por vencer, pagos vencidos)
- KPIs del mes
- Ranking de asesores
- Propiedades vendidas en el mes

**Código:** [estate_reports/models/estate_dashboard.py](estate_reports/models/estate_dashboard.py) — método `_cron_send_monthly_report`

---

## RESUMEN RÁPIDO — dónde hacer clic

| Quiero ver... | Ruta en pantalla |
|---|---|
| Lista de contratos | Inmobiliaria → Contratos |
| Ficha de un contrato | Contratos → clic en el nombre |
| Pagos de un contrato | Ficha contrato → pestaña 💰 Pagos |
| Documentos de un contrato | Ficha contrato → pestaña 📂 Documentos del Contrato |
| Firmar un contrato | Ficha contrato → pestaña ✍️ Firma del Cliente |
| Contratos de una propiedad | Ficha propiedad → smart-button [N Contratos] |
| Todos los documentos | Inmobiliaria → Documentos |
| Documentos de una propiedad | Ficha propiedad → smart-button [N Documentos] |
| Todos los documentos de un cliente | Ficha contacto → smart-button 📂 Carpeta completa |
| Configurar tipos de documento | Inmobiliaria → Configuración → Tipos de Documento |
| KPIs generales | Menú → Dashboard |
| Promedio de ventas | Reportes → 📊 Promedio de Ventas |
| Exportar reporte PDF/Excel | Reportes → Generar Reportes |
| Comisiones de asesores | Reportes → Liquidación de Comisiones |
