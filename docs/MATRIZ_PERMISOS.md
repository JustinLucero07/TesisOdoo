# Matriz de Roles y Permisos (por módulo)

Documento de verificación de la seguridad del sistema. Organiza, módulo por módulo, los permisos de acceso (CRUD) por grupo y las reglas de registro (visibilidad por fila).

## Notación

Cada celda indica los permisos concedidos en el orden **R W C U**:

- **R** = Leer (read) · **W** = Escribir (write) · **C** = Crear (create) · **U** = Eliminar (unlink)
- Una letra presente = permiso concedido; un punto `·` = denegado.
- Ejemplo: `RWC·` = leer + escribir + crear, sin eliminar. `R···` = solo lectura. `····` = sin acceso.

## Grupos y jerarquía (actualizado)

| Grupo | XML ID | Hereda de (implied_ids) | Rol |
|---|---|---|---|
| **Asesor** | `estate_group_agent` | `+ Ver todas las propiedades` | Agente comercial; operativo |
| **Marketing** | `estate_group_marketing` | **Administrador** (co-admin) | Encargada general: control amplio |
| **Gerente** | `estate_group_manager` | Asesor | Ve y gestiona todo lo operativo |
| **Administrador** | `estate_group_admin` | Gerente + `base.group_erp_manager` | Control total (incl. usuarios) |
| **Ver todas las propiedades** | `estate_group_property_viewer_all` | — (auxiliar) | Regla `1=1` para ver todas las propiedades |

> Cambios respecto al diseño base: **Asesor** ahora incluye "ver todas las propiedades"; **Marketing hereda Administrador** (es co-administradora); **Administrador** incluye la gestión de usuarios de Odoo (`base.group_erp_manager`).

---

## Resumen ejecutivo: división de roles (estado actual efectivo)

Esta es la división **real y verificada** tras la última configuración:

| Área | Asesor | Marketing / Gerente / Administrador |
|------|--------|-------------------------------------|
| **Propiedades** | Ver/crear/editar **todas**; eliminar **solo en Borrador** | Ver/crear/editar/**eliminar todas** (cualquier estado) |
| **Leads** | Ver/crear/editar **solo los suyos** | **Todos** |
| **Contratos** | Ver/crear/editar **solo los suyos** | **Todos** |
| **Pagos** | Ver **solo los suyos** | **Todos** |
| **Comisiones** | Ver **solo las suyas** | Ver/gestionar **todas** + registrar pagos |
| **Finanzas, Dashboard, Reportes** | No | **Sí** |
| **Configuración, Usuarios y Roles, Auditoría** | No | **Marketing y Admin: sí** · Gerente: solo operativo |

Notas clave:
- **Marketing = co-administradora** (hereda el rol Administrador): finanzas, comisiones, configuración, eliminar, usuarios/roles, dashboard, reportes y auditoría.
- **Eliminar propiedades:** el modelo bloquea borrar propiedades publicadas/vendidas; solo Gerencia/Marketing/Admin lo evitan. El asesor solo borra Borradores (regla de registro + control en `unlink()`).
- **Verificado en vivo** rol por rol (visibilidad, creación, edición y eliminación).

> **Totales del proyecto:** ~249 permisos de acceso definidos por los módulos `estate_*`. El resto (account, hr, etc.) pertenecen a Odoo estándar.

> Las tablas por módulo de abajo reflejan el **diseño base de cada CSV**; la verdad efectiva por rol es la del resumen de arriba (por las herencias de grupos y reglas de registro).

---

## 1. `estate_management` (Núcleo)

### 1.A — Modelos inmobiliarios propios

| Modelo | Asesor | Marketing | Gerente | Admin |
|---|:--:|:--:|:--:|:--:|
| estate.property.type | `R···` | `R···` | `RWC·` | `RWCU` |
| estate.property | `RWCU`¹ | `RWC·`² | `RWCU` | `RWCU` |
| estate.property.tag | `R···` | `R···` | `RWC·` | `RWCU` |
| estate.property.image | `RWC·` | `RWC·` | `RWC·` | `RWCU` |
| estate.commission | `RWC·` | `R···` | `RWCU` | `RWCU` |
| estate.contract | `RWC·` | `R···` | `RWC·` | `RWCU` |
| estate.payment | `RWC·` | `R···` | `RWC·` | `RWCU` |
| estate.property.price.history | `R···` | `R···` | `RWC·` | `RWCU` |
| estate.property.expense | `RWC·` | `R···` | `RWC·` | `RWCU` |
| estate.property.offer | `RWC·` | `R···` | `RWC·` | `RWCU` |
| estate.tenant.request | `RWC·` | `R···` | `RWC·` | `RWCU` |
| estate.contract.deposit | `RWC·` | `R···` | `RWC·` | `RWCU` |
| estate.appraisal | `RWC·` | `R···` | `RWC·` | `RWCU` |
| estate.property.comparator.wizard | `RWC·` | `RWC·` | `RWCU` | `RWCU` |
| estate.sale.wizard | `RWC·` | `····` | `RWC·` | `RWCU` |
| estate.advisor.fb.post | `RWC·` | `R···` | `RWCU` | `RWCU` |

> ¹ El Asesor puede **eliminar propiedades solo en estado Borrador** (regla `estate_group_agent` con dominio `state = draft` + control en `unlink()`). Para publicadas/vendidas: solo Gerencia/Marketing/Admin.
> ² Marketing tiene `RWC·` en el CSV, pero al **heredar Administrador** su acceso efectivo es total (`RWCU`).

**Reglas de registro (Propiedad):**
- Asesor: ve/crea/edita **todas** (grupo "ver todas las propiedades"); elimina **solo Borradores**.
- Marketing / Gerente / Administrador: ven, editan y **eliminan todas**.

**Reglas de registro (Contrato / Pago):**
- Asesor: ve/crea/edita **solo los suyos** (`user_id = user`).
- Marketing / Gerente / Administrador: ven **todos**.

### 1.B — Modelos estándar de Odoo (acceso otorgado por `estate_management`)

> Este módulo concede a los grupos inmobiliarios acceso a modelos nativos de Odoo (son los registros `std.*` que aparecen en la lista de permisos). Esto permite que el sistema inmobiliario funcione integrado con CRM, Ventas, Contabilidad y RR.HH. sin instalar perfiles completos de Odoo.

| Modelo estándar (técnico) | Asesor | Marketing | Gerente | Admin |
|---|:--:|:--:|:--:|:--:|
| Contacto (res.partner) | `RWC·` | `RWC·` | `RWCU` | `RWCU` |
| Lead / Oportunidad (crm.lead) | `RWC·` | `RWC·` | `RWCU` | `RWCU` |
| Etapas CRM (crm.stage) | `R···` | `R···` | `RWCU` | `RWCU` |
| Etiqueta CRM (crm.tag) | `R···` | `RWC·` | `RWCU` | `RWCU` |
| Equipo de ventas (crm.team) | `R···` | `R···` | `RWCU` | `RWCU` |
| Cita / Evento (calendar.event) | `RWC·` | `RWC·` | `RWCU` | `RWCU` |
| Actividad (mail.activity) | `RWCU` | `RWCU` | `RWCU` | `RWCU` |
| Pedido de venta (sale.order) | `RWC·` | `R···` | `RWCU` | `RWCU` |
| Línea de pedido (sale.order.line) | `RWC·` | `R···` | `RWCU` | `RWCU` |
| Producto (product.template) | `R···` | `RW··` | `RW··` | `RWCU` |
| Variante de producto (product.product) | `R···` | `RW··` | `RW··` | `RWCU` |
| Categoría de producto | `R···` | `R···` | `RW··` | `RWCU` |
| Factura/Asiento (account.move) | `R···` | `R···` | `RWCU` | `RWCU` |
| Apunte contable (account.move.line) | `R···` | `R···` | `RWCU` | `RWCU` |
| Pagos (account.payment) | `R···` | `R···` | `RWCU` | `RWCU` |
| Cuenta contable (account.account) | `····` | `····` | `R···` | `RWCU` |
| Cuenta analítica | `····` | `····` | `RWC·` | `RWCU` |
| Diario (account.journal) | `R···` | `R···` | `RW··` | `RWCU` |
| Impuesto (account.tax) | `R···` | `R···` | `R···` | `RWCU` |
| Empleado (hr.employee) | `····` | `····` | `RW··` | `RWCU` |
| Departamento (hr.department) | `····` | `····` | `R···` | `RWCU` |
| Asistencia (hr.attendance) | `RWC·` | `····` | `RWCU` | `RWCU` |
| Usuario (res.users) | `R···` | `R···` | `R···` | `RWCU` |

---

## 2. `estate_crm`

| Modelo | Asesor | Marketing | Gerente | Admin |
|---|:--:|:--:|:--:|:--:|
| estate.client.interaction | `RWC·` | `R···` | `RWCU` | `RWCU` |
| estate.meta.webhook.event | `····` | `R···` | `RWCU` | `RWCU` |

**Reglas de registro:**
- *Lead (crm.lead):* Asesor ve **solo los asignados a él**; Gerente/Admin ven **todos**.
- *Interacción:* Asesor ve **solo las suyas**; Gerente/Admin ven **todas**.

---

## 3. `estate_calendar`

| Modelo | Asesor | Marketing | Gerente | Admin |
|---|:--:|:--:|:--:|:--:|
| calendar.print.wizard | `RWCU` | `RWC·` | `RWCU` | `RWCU` |
| estate.advisor.unavailability | `RWCU` | `····` | `RWCU` | `RWCU` |

**Reglas de registro:**
- *Indisponibilidad:* Asesor gestiona **solo la suya** (`user_id = user`); Gerente/Admin ven **todas**.

> *Visitas:* `calendar.event` usa la seguridad nativa de Odoo (cada usuario ve las citas en las que participa). La indisponibilidad ("día ocupado") bloquea el agendamiento de visitas para el asesor en las fechas marcadas.

---

## 4. `estate_document`

| Modelo | Asesor | Marketing | Gerente | Admin |
|---|:--:|:--:|:--:|:--:|
| estate.document | `RWC·` | `R···` | `RWCU` | `RWCU` |
| estate.document.type | `R···` | `R···` | `RWC·` | `RWCU` |
| estate.document.reject.wizard | `RWCU` | `····` | `RWCU` | `RWCU` |

**Reglas de registro:**
- *Documento:* Asesor ve según **confidencialidad** (público/interno + sus restringidos); Gerente/Admin ven **todos**.

---

## 5. `estate_reports`

| Modelo | Asesor | Marketing | Gerente | Admin |
|---|:--:|:--:|:--:|:--:|
| estate.dashboard | `R·C·` | `R·C·` | `RWCU` | `RWCU` |
| estate.report.wizard | `RWC·` | `RWC·` | `RWCU` | `RWCU` |
| estate.commission.wizard | `RWC·` | `RWC·` | `RWCU` | `RWCU` |
| estate.sales.report.wizard | `RWC·` | `RWC·` | `RWCU` | `RWCU` |
| estate.sales.target | `R···` | `····` | `RWCU` | `RWCU` |

---

## 6. `estate_ai_agent`

| Modelo | Asesor | Marketing | Gerente | Admin |
|---|:--:|:--:|:--:|:--:|
| estate.ai.chat.history | `R·C·` | `····` | `RWCU` | `RWCU` |
| estate.ai.memory | `RWC·` | `····` | `RWCU` | `RWCU` |
| estate.ai.feedback | `R·C·` | `R·C·` | `RWCU` | `RWCU` |

**Reglas de registro:**
- *Chat IA:* Asesor ve **solo su historial**; Gerente/Admin ven **todo**.
- *Memoria IA:* Asesor ve **solo las suyas**; Gerente/Admin ven **todas**.

---

## 7. `estate_audit`

| Modelo | Gerente | Admin | Sistema |
|---|:--:|:--:|:--:|
| estate.audit.log | `R···` | `RWCU` | `RWCU` |

> La bitácora **no concede acceso a Asesor ni Marketing**. El Gerente solo puede **leer** (la bitácora es inmutable por diseño; el modelo bloquea además escritura/eliminación salvo contexto interno).

---

## 8. `estate_social`

| Modelo | Asesor | Marketing | Gerente | Admin |
|---|:--:|:--:|:--:|:--:|
| estate.instagram.stats | `RWC·` | `RWC·` | `RWCU` | `RWCU` |
| estate.facebook.stats | `RWC·` | `RWC·` | `RWCU` | `RWCU` |
| estate.facebook.stats.history | `R···` | `RW··` | `RWCU` | `RWCU` |

---

## 9. `estate_wordpress`

| Modelo | Asesor | Marketing | Gerente | Admin |
|---|:--:|:--:|:--:|:--:|
| estate.wp.agent | `RWC·` | `RWC·` | `RWCU` | `RWCU` |
| estate.wordpress.import.wizard | `····` | `RWC·` | `RWCU` | `RWCU` |
| estate.wordpress.import.line | `····` | `RWC·` | `RWCU` | `RWCU` |
| estate.wordpress.link.wizard | `····` | `RWC·` | `RWCU` | `RWCU` |

---

## 10. `estate_payroll`

| Modelo | Asesor | Marketing | Gerente | Admin |
|---|:--:|:--:|:--:|:--:|
| estate.payroll.line | `R···` | `····` | `RWCU` | `RWCU` |

**Reglas de registro:**
- *Nómina:* Asesor ve **solo la suya**; Gerente/Admin ven **todas**.

---

## Historial de decisiones de diseño

> Auditoría inicial y decisiones tomadas por el cliente. El modelo final es intencional.

| # | Tema | Decisión final |
|---|---|---|
| **O2** | "Día ocupado" de otros asesores | ✅ Resuelto: cada asesor gestiona **solo el suyo** (regla `user_id = user`). |
| **Propiedades** | ¿Quién ve/crea/edita/elimina? | Todos los roles ven/crean/editan **todas**. Eliminar: Asesor **solo Borradores**; Marketing/Gerente/Admin **cualquiera**. |
| **Marketing** | Alcance del rol | Por decisión del cliente, **Marketing es co-administradora** (hereda Administrador): finanzas, comisiones, configuración, eliminar, usuarios/roles, dashboard, reportes, auditoría. |
| **Leads / Contratos / Pagos** | Visibilidad del Asesor | El asesor ve/gestiona **solo los suyos**; Marketing/Gerente/Admin ven **todos**. |
| **Usuarios y Roles** | Quién los gestiona | Administrador y Marketing (vía `base.group_erp_manager`). |
| **Eliminación** | Protección de registros | Solo Gerencia/Marketing/Admin eliminan registros operativos; el asesor no (salvo propiedades en Borrador). |

> *Toda esta configuración fue verificada en vivo (impersonando cada rol): visibilidad, creación, edición y eliminación.*

---

*Matriz de roles y permisos — Proyecto de Titulación, UPS Sede Cuenca.*
