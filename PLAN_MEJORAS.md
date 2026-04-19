# Plan de Mejoras del Sistema — Inmobiliaria Odoo 19

> Documento generado el 2026-04-09. Estado actual del sistema + roadmap de mejoras priorizadas.

---

## Cambios aplicados hoy

### Pagos — diferenciación visual
- Banner explicativo en el formulario de `estate.payment` que aclara la diferencia con los pagos de Facturación
- Lista de pagos renombrada a "Pagos Inmobiliarios" con colores diferenciados (verde=pagado, amarillo=pendiente)
- Columnas mejoradas: estado de la factura Odoo visible directamente en la lista
- Botón "Marcar Pagado" inline en la lista de pagos del contrato
- Módulo `account_debit_note` instalado: permite emitir **notas de débito y crédito** desde Facturación

### CRM Lead — mejoras
- Nuevos smart buttons: **Contratos** y **Órdenes de Venta** vinculados al lead
- Botón **"Crear Orden de Venta"** en el header del lead (sin necesidad de ir a la propiedad)
- Métodos `action_view_lead_contracts`, `action_view_lead_sale_orders`, `action_create_sale_order_from_lead`

---

## Situación actual de Contabilidad

### ¿Qué tienes instalado?

| Módulo | Estado | Qué da |
|---|---|---|
| `account` | ✅ Instalado | Facturación + diario contable básico |
| `account_payment` | ✅ Instalado | Registro de pagos |
| `account_debit_note` | ✅ Instalado HOY | Notas de débito/crédito |
| `account_edi_ubl_cii` | ✅ Instalado | Factura electrónica UBL/CII |
| `accountant` | ❌ Enterprise | Contabilidad completa (de pago) |

### Lo que NO tienes (Enterprise) vs alternativas gratis

| Función Enterprise | Alternativa gratis (OCA) |
|---|---|
| Conciliación bancaria automática | `account_bank_statement_import` (OCA) |
| Reportes financieros avanzados (P&G, Balance) | `mis_builder` (OCA) |
| Activos fijos | `account_asset` (OCA) |
| Presupuestos | `account_budget_community` (OCA) |

> **Para tu tesis:** El módulo `account` de Community es suficiente. Cubre facturas, pagos, diarios, y reportes básicos.

### Cómo instalar módulos OCA (si los necesitas)

```bash
# 1. Clonar el repositorio OCA de accounting (versión 17 migrable)
git clone --branch 17.0 https://github.com/OCA/account-financial-reporting.git /home/justin/Documentos/oca_account

# 2. Agregar la ruta al odoo19.conf
# addons_path = ...,/home/justin/Documentos/oca_account

# 3. Instalar el módulo deseado
python odoo-bin -d tesis_odoo19 -i mis_builder --stop-after-init
```

> **NOTA:** Los módulos OCA de versión 17 son en su mayoría compatibles con Odoo 19 con ajustes mínimos en el `__manifest__.py` (cambiar versión). No se recomienda para tesis a menos que sea necesario.

---

## Roadmap de mejoras — priorizadas

### 🔴 Alta prioridad

#### A1 — Módulo de Presupuesto / Cotización formal
**Qué falta:** Actualmente no hay un paso formal de "Cotización" antes de la orden de venta. El cliente no recibe un PDF con las condiciones antes de firmar.

**Mejora:**
- Aprovechar el flujo nativo `Quotation → Sale Order` de Odoo
- Personalizar el PDF de cotización con datos de la propiedad, QR, y condiciones
- Botón "Enviar Cotización por Email" desde el lead CRM

**Impacto:** Flujo más profesional. El cliente recibe un documento formal antes de comprometerse.

---

#### A2 — Reporte de comisiones por asesor (PDF/Excel)
**Qué falta:** Las comisiones se calculan pero no hay un reporte formal exportable por asesor/período.

**Mejora:**
- Wizard de reporte: filtrar por asesor + período → exportar PDF con tabla de comisiones
- Incluir: propiedades vendidas, montos, % comisión, total a pagar

**Impacto:** El asesor puede ver exactamente lo que va a cobrar. El admin puede aprobar y pagar.

---

#### A3 — Estado de cuenta del cliente (portal)
**Qué falta:** El propietario/comprador no puede ver su historial de pagos desde el portal.

**Mejora:**
- En el portal del propietario, añadir sección "Mis Pagos" con lista de `estate.payment` y facturas
- Botón para descargar el comprobante de cada pago

---

### 🟡 Media prioridad

#### B1 — Recordatorio automático de pagos pendientes por WhatsApp
**Qué falta:** El cron detecta pagos vencidos y crea actividades, pero no notifica al cliente directamente.

**Mejora:**
- Cuando un `estate.payment` lleva +3 días vencido, enviar WhatsApp automático al cliente vía CallMeBot con el monto y número de contrato

---

#### B2 — Firma digital en la Orden de Venta
**Qué falta:** Los contratos tienen firma digital (`customer_signature`) pero las órdenes de venta no.

**Mejora:**
- Añadir campo `customer_signature` en `sale.order` (heredando el modelo)
- Widget de firma en la vista del portal y del backend

---

#### B3 — Historial de interacciones en el lead
**Qué falta:** Las interacciones (llamadas, reuniones, WhatsApp) están registradas pero no hay una línea de tiempo visual.

**Mejora:**
- Vista cronológica en el lead CRM con todas las interacciones: visitas, ofertas, mensajes, cambios de etapa
- Usar el chatter ya existente pero agregar filtros por tipo

---

#### B4 — Tasaciones vinculadas a la oferta
**Qué falta:** Las tasaciones (`estate.appraisal`) existen pero no están vinculadas a la oferta ni al lead.

**Mejora:**
- Añadir `appraisal_id` en la oferta
- Botón "Ver Tasación" en el formulario de oferta
- Al aceptar una oferta, registrar el precio acordado vs el precio tasado

---

#### B5 — Plantilla de email al generar contrato
**Qué falta:** Al crear un contrato, el cliente no recibe ninguna notificación automática.

**Mejora:**
- Template de email: "Su contrato {ref} ha sido generado. Revise los términos y firme digitalmente."
- Se envía al activar el contrato

---

### 🟢 Baja prioridad (mejoras de experiencia)

#### C1 — Vista Kanban de Propiedades con filtro rápido por tipo
Añadir botones de filtro rápido en la vista kanban: Venta / Arriendo / Disponibles / Reservadas

#### C2 — Comparador de propiedades
Vista de comparación lado a lado de 2-4 propiedades seleccionadas (área, precio, habitaciones, etc.)

#### C3 — Exportación de ficha de propiedad a PDF
Botón "Descargar Ficha" en la propiedad que genera un PDF con foto, datos y QR para compartir con clientes

#### C4 — Calculadora de hipoteca mejorada
La calculadora actual es estática. Mejora: hacer que sea interactiva con sliders (OWL widget)

#### C5 — Integración Google Calendar para visitas
Sincronizar visitas del calendario de Odoo con Google Calendar del asesor

#### C6 — Notificación push en Odoo cuando llega un lead nuevo
Usar el sistema de bus de Odoo para notificar al asesor en tiempo real cuando hay un lead nuevo con buen score

---

## Contabilidad: Plan para tesis

Para una tesis, el módulo `account` Community cubre todo lo necesario:

```
Lo que SÍ tienes (gratis):
✅ Facturas de venta (out_invoice)
✅ Facturas de compra (in_invoice)  
✅ Notas de débito/crédito (account_debit_note)
✅ Registro de pagos
✅ Diario de asientos
✅ Plan de cuentas
✅ Impuestos (IVA, retenciones básicas)
✅ Reporte de libro diario
✅ Estados de cuenta básicos
✅ Factura electrónica UBL/CII (account_edi_ubl_cii)

Lo que NO tienes sin Enterprise:
❌ Conciliación bancaria automática
❌ Reportes P&G / Balance visual
❌ Activos fijos deprecación automática
❌ Presupuestos contables

Recomendación para tesis:
→ Usa account Community + estate.payment para el flujo completo
→ Eso es más que suficiente para demostrar integración contable en una tesis
```

### Si necesitas más: OCA step-by-step

```bash
# Solo si necesitas reportes financieros avanzados:
git clone https://github.com/OCA/mis-builder.git --branch 17.0 /home/justin/Documentos/oca_mis_builder
# Agregar path en odoo19.conf y cambiar versión en __manifest__.py de 17.0 a 19.0
```

---

## Resumen ejecutivo — qué implementar primero

| Prioridad | Mejora | Esfuerzo | Impacto |
|---|---|---|---|
| 1 | A2 — Reporte PDF de comisiones por asesor | Bajo | Alto |
| 2 | A1 — PDF de cotización personalizado | Medio | Alto |
| 3 | B1 — WhatsApp para pagos vencidos | Bajo | Medio |
| 4 | B5 — Email al activar contrato | Bajo | Medio |
| 5 | A3 — Estado de cuenta en portal | Medio | Alto |
| 6 | C3 — Ficha de propiedad en PDF | Bajo | Alto |
| 7 | B2 — Firma digital en orden de venta | Medio | Medio |
