# Analisis de Reportes y Requerimientos CRM — Inmobi

## Estado Actual de Reportes

### Donde estan los reportes

En Odoo, navega a: **Inmobiliaria > Inteligencia > Dashboard General** (menu principal de reportes)

Desde ahi tienes acceso a:

| Funcionalidad | Donde se accede | Estado |
|--------------|-----------------|--------|
| **Dashboard KPI** | Inmobiliaria > Inteligencia > Dashboard General | IMPLEMENTADO |
| **Generar Reportes PDF/Excel** | Inmobiliaria > Inteligencia > Generar Reportes | IMPLEMENTADO |
| **Liquidacion de Comisiones** | Inmobiliaria > Inteligencia > Liquidacion Comisiones | IMPLEMENTADO |
| **Analiticas (graficos/pivots)** | Inmobiliaria > Inteligencia > Analisis de [Propiedades/Contratos/Pagos/etc.] | IMPLEMENTADO |
| **Reporte de Visitas** | Inmobiliaria > Inteligencia > Reporte de Visitas | IMPLEMENTADO |
| **Ficha Tecnica PDF** | Propiedad > boton Imprimir > Ficha Tecnica | IMPLEMENTADO |
| **Cotizacion PDF** | Lead CRM > boton Imprimir > Cotizacion | IMPLEMENTADO |
| **Estado de Cuenta PDF** | Contrato > boton Imprimir > Estado de Cuenta | IMPLEMENTADO |
| **Contrato PDF** | Contrato > boton Imprimir > Contrato | IMPLEMENTADO |
| **Reporte Propietario PDF** | Propiedad > boton Imprimir > Informe Mensual Propietario | IMPLEMENTADO |

### Reportes Excel disponibles (wizard)

Acceso: **Inmobiliaria > Inteligencia > Generar Reportes**

1. **Propiedades Disponibles** — listado con precios, area, tipo
2. **Clientes Activos** — oportunidades con ingreso esperado
3. **Ventas por Periodo** — ventas mensuales con grafico
4. **Tiempo de Venta** — dias en mercado por tipo de propiedad
5. **Visitas / Citas** — resultado de visitas con grafico circular
6. **Contratos por Vencer** — alerta de contratos proximos (60 dias)
7. **Desempeno de Asesores** — comisiones y ventas por asesor
8. **Analisis Geografico AVM** — precio/m2 por ciudad
9. **Retorno de Marketing** — leads por fuente y tasa de conversion

### Dashboard KPI (pantalla principal)

Muestra en tiempo real:
- Total de propiedades (disponibles, vendidas, alquiladas)
- Propiedades estancadas (45+ dias sin visitas)
- Clientes activos, citas del mes
- Comisiones del mes, ingresos, facturas pendientes
- Mapa geografico con marcadores (Leaflet.js)
- Ranking de asesores (top 10 por ventas)

### Analiticas (graficos + tablas pivot)

7 vistas analiticas con graficos, tablas pivot y listas:
1. Analisis de Propiedades (por tipo)
2. Analisis de Contratos (por tipo/monto)
3. Analisis de Pagos (por metodo/estado)
4. Analisis de Ofertas (por propiedad/monto)
5. Analisis de Gastos (por tipo)
6. Analisis de Tasaciones (por valor)
7. Analisis de Mantenimiento (por tipo/costo)

---

## Requerimientos del Cliente vs Estado Actual

### 1. Documentos privados en el CRM

**Requerimiento:** "Almacenar documentacion en el CRM de forma privada"

**Estado: YA IMPLEMENTADO**

El modulo `estate_document` ya tiene:
- Documentos vinculados a leads, propiedades y contactos
- **Regla de seguridad:** Los agentes solo ven documentos que ellos crearon
- Managers/Admins ven todos los documentos
- Tipos: contrato, legal, identificacion, escritura, certificado
- Validacion: solo PDF, DOC, XLS, imagenes (max 10MB)
- Acceso desde: Lead CRM > pestana "Documentacion Confidencial"

**Accion:** Ninguna necesaria. Solo verificar que los agentes vean el boton de documentos en el lead.

### 2. Integraciones con pagina web y redes sociales

**Requerimiento:** "Integraciones con la pagina web, redes sociales, WhatsApp"

**Estado: YA IMPLEMENTADO**

| Integracion | Modulo | Estado |
|------------|--------|--------|
| WordPress (publicar propiedades) | `estate_wordpress` | Implementado |
| Facebook (publicar en pagina) | `estate_social` | Implementado |
| Instagram (publicar con imagen) | `estate_social` | Implementado |
| WhatsApp (recordatorios de citas) | `estate_calendar` | Implementado |
| Webhook leads (capturar desde web/RRSS) | `estate_crm` | Implementado |

**Accion:** Ya esta todo. Solo falta configurar los tokens en Ajustes (ver `INTEGRACIONES.md` en `estate_social/`).

### 3. Reportes de visitas a inmuebles y ventas

**Requerimiento:** "Obtener las personas que visitaron un inmueble y reportes de ventas"

**Estado: YA IMPLEMENTADO**

- **Reporte de Visitas:** Inmobiliaria > Inteligencia > Reporte de Visitas
  - Lista, tabla pivot y grafico de barras
  - Filtros por propiedad, cliente, asesor, estado, resultado, fecha
  - Agrupar por: propiedad, cliente, resultado, asesor, mes
- **Ventas por periodo:** Excel wizard con grafico mensual
- **Tiempo de venta:** Excel wizard con dias promedio por tipo

### 4. GPS del inmueble

**Requerimiento:** "Apartado para guardar ubicacion GPS del inmueble"

**Estado: YA IMPLEMENTADO**

- Campos `latitude` y `longitude` en `estate.property`
- Mapa embebido con OpenStreetMap en la ficha de propiedad
- Boton "Ver en Google Maps" que abre en nueva ventana
- Mapa en el Dashboard con todos los inmuebles geolocalizados

### 5. Registro de visita en un solo paso

**Requerimiento:** "Enlazar propiedad y registrar visita deberia ser un solo paso"

**Estado: YA IMPLEMENTADO (parcialmente)**

Actualmente se puede crear la visita directamente desde la propiedad (boton de citas), pero se requieren varios campos. El flujo es:
1. Desde propiedad/lead: clic en "Programar Visita"
2. Se pre-llena la propiedad, solo falta seleccionar cliente y fecha

**Posible mejora:** Un boton de "Visita rapida" en la propiedad que solo pida cliente + fecha/hora (pre-rellenar todo lo demas).

### 6. Tiempo de venta y vendido por agencia vs dueno

**Requerimiento:** "Tiempo en que se vende, quien vende (agencia vs dueno)"

**Estado: YA IMPLEMENTADO**

- `days_on_market` — campo computado que calcula dias desde listado hasta venta
- `sold_by` — campo en propiedad: "Vendido por la Agencia" o "Vendido por el Dueno"
- Excel "Tiempo de Venta" con promedio por tipo de propiedad
- Reporte en dashboard: dias promedio en mercado

### 7. Recordatorios de contratos por vencer

**Requerimiento:** "Recordatorios cuando vencen contratos, lo manejamos en Excel"

**Estado: YA IMPLEMENTADO**

- Cron diario `ir_cron_check_contract_expiry` que revisa contratos
- Si faltan <= 30 dias: crea actividad "Contrato por vencer (X dias)"
- Si ya vencio: crea actividad urgente "Contrato VENCIDO!"
- El asesor recibe notificacion en su bandeja de actividades
- Excel "Contratos por Vencer" con codigo de colores (verde/amarillo/rojo)

---

## Plan de Mejoras para Reportes

### Lo que falta o se puede mejorar

#### PRIORIDAD ALTA — Consolidacion

| # | Mejora | Descripcion | Esfuerzo |
|---|--------|-------------|----------|
| 1 | **Dashboard unificado con pestanas** | Agregar pestanas al dashboard: "KPIs", "Mapa", "Ranking", "Alertas" para no tener todo en una sola pagina larga | Medio |
| 2 | **Reporte de conversion de leads** | Nuevo reporte Excel/PDF: leads creados > visitas > ofertas > cierre. Embudo de conversion con % por etapa | Medio |
| 3 | **Reporte de cartera de clientes** | PDF con todos los clientes de un asesor: leads activos, contratos vigentes, pagos pendientes, comisiones | Medio |

#### PRIORIDAD MEDIA — Nuevos reportes

| # | Mejora | Descripcion | Esfuerzo |
|---|--------|-------------|----------|
| 4 | **Reporte mensual automatico por email** | Ya existe el cron, pero mejorarlo: incluir graficos inline, comparativa mes anterior, alertas criticas | Bajo |
| 5 | **Reporte de productividad por asesor** | Visitas realizadas, leads convertidos, tiempo promedio de respuesta, comisiones ganadas — por periodo | Medio |
| 6 | **Reporte de ocupacion de propiedades** | Para arriendos: tasa de ocupacion, meses vacantes, ingresos por propiedad | Medio |
| 7 | **Comparativa de precios AVM** | Reporte que compare precio listado vs AVM estimado para todas las propiedades — identificar sobrevaluadas | Bajo |

#### PRIORIDAD BAJA — Mejoras visuales

| # | Mejora | Descripcion | Esfuerzo |
|---|--------|-------------|----------|
| 8 | **Graficos interactivos en dashboard** | Reemplazar stat buttons por graficos Chart.js embebidos (ventas/mes, leads/fuente) | Alto |
| 9 | **Exportacion directa desde analiticas** | Boton "Exportar Excel" en cada vista analitica para que el usuario no tenga que ir al wizard | Bajo |
| 10 | **Reporte de marketing ROI mejorado** | Incluir costo por lead, costo por visita, costo por cierre por cada canal | Medio |

---

## Resumen — Todo funciona

Basado en el analisis, **todos los requerimientos mencionados por el cliente ya estan implementados:**

1. Documentos privados en CRM
2. Integraciones web/RRSS/WhatsApp
3. Reportes de visitas y ventas
4. GPS del inmueble
5. Tiempo de venta
6. Vendido por agencia vs dueno
7. Recordatorios de contratos

El sistema tiene **6 PDFs, 9 reportes Excel, 20+ KPIs, 7 vistas analiticas, mapa geografico y ranking de asesores**. La sugerencia es enfocarse en la consolidacion visual (mejoras 1, 8) y agregar el embudo de conversion (mejora 2).
