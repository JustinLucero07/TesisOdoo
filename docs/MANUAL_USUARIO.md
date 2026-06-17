# Manual de Usuario — Inmobi
### Sistema Integral de Gestión Inmobiliaria
**Inmobi Community** · Construido sobre Odoo 19

---

## Índice

1. [Introducción](#1-introducción)
2. [Conceptos básicos de la interfaz](#2-conceptos-básicos-de-la-interfaz)
3. [Acceso, usuarios y roles](#3-acceso-usuarios-y-roles)
4. [Gestión de Propiedades](#4-gestión-de-propiedades)
5. [Clientes y Leads (CRM)](#5-clientes-y-leads-crm)
6. [Flujo de Venta](#6-flujo-de-venta)
7. [Operaciones](#7-operaciones)
8. [Documentos](#8-documentos)
9. [Finanzas](#9-finanzas)
10. [Agenda y Visitas](#10-agenda-y-visitas)
11. [Reportes e Inteligencia de Negocio](#11-reportes-e-inteligencia-de-negocio)
12. [Asistente con Inteligencia Artificial](#12-asistente-con-inteligencia-artificial)
13. [Integraciones](#13-integraciones)
14. [Configuración](#14-configuración)
15. [Preguntas frecuentes y solución de problemas](#15-preguntas-frecuentes-y-solución-de-problemas)
16. [Glosario](#16-glosario)

---

## 1. Introducción

**Inmobi** es una plataforma integral para inmobiliarias que cubre todo el ciclo del negocio:

- **Inventario** de propiedades (casas, departamentos, terrenos, oficinas, locales).
- **CRM** de clientes y leads con puntuación inteligente y cruce automático.
- **Operaciones**: contratos, ofertas, tasaciones, mantenimiento, documentos.
- **Finanzas**: pagos, comisiones, nómina, facturación nativa.
- **Reportes** ejecutivos con metas, gráficos y exportación.
- **Asistente con IA** que entiende lenguaje natural y automatiza tareas.
- **Integraciones**: WordPress, redes sociales, WhatsApp y automatización con n8n.

### Módulos del sistema
| App | Función |
|-----|---------|
| **Inmobiliaria** | Núcleo: propiedades, operaciones, finanzas, agenda |
| **CRM** | Clientes, leads, pipeline, aliados |
| **Reportes** | Dashboard ejecutivo, análisis, exportaciones |
| (flotante) **Asistente IA** | Chat inteligente disponible en todo el sistema |

---

## 2. Conceptos básicos de la interfaz

| Elemento | Descripción |
|----------|-------------|
| **Menú de aplicaciones** | Cuadrícula (☰) arriba a la izquierda. Cambia entre apps. |
| **Barra de menú** | Secciones de la app activa (ej. Propiedades, Operaciones…). |
| **Vista lista** | Tabla de registros. Usa **filtros** y **agrupar por** para encontrar rápido. |
| **Vista kanban** | Tarjetas (útil en propiedades y pipeline). |
| **Ficha (formulario)** | Detalle de un registro, con pestañas y barra de estado. |
| **Barra de estado** | Arriba de la ficha: muestra y permite cambiar el ciclo de vida. |
| **Botones de acción** | A la izquierda del estado (Publicar, Vender, etc.). |
| **Chatter** | Panel derecho: historial de cambios, mensajes y actividades. |
| **Botones inteligentes** | Contadores arriba a la derecha (Citas, Leads, Documentos…). |

### Buscar y filtrar
- Escribe en la **barra de búsqueda** para filtrar por texto.
- Pulsa el desplegable para ver **filtros predefinidos** (ej. *Disponibles*, *Mis propiedades*, *Vencidos*).
- **Agrupar por** organiza la lista (por estado, ciudad, asesor…).
- Guarda tus búsquedas como **favoritas** (estrella).

---

## 3. Acceso, usuarios y roles

### Ingresar
1. Abre el navegador en la dirección del servidor (ej. `http://localhost:8070`).
2. Ingresa **usuario** y **contraseña**.

### Roles de seguridad
| Rol | Permisos |
|-----|----------|
| **Agente** | Gestiona sus propiedades, leads, visitas, ofertas y documentos. |
| **Manager** | Todo lo del agente + reportes, comisiones, metas y configuración. |
| **Administrador** | Acceso total, incluida la configuración técnica. |
| **Marketing** | Acceso a publicación y redes sociales. |

> Los roles se asignan en **Inmobiliaria → Configuración → Roles Inmobiliarios** y **Usuarios del Sistema** (solo Administrador).

---

## 4. Gestión de Propiedades

**Ruta:** Inmobiliaria → Propiedades → Catálogo

### 4.1 Crear una propiedad
1. Pulsa **Nuevo**.
2. **Información general**: tipo de operación (Venta/Arriendo), tipo de propiedad, precio,
   precio tope (mínimo negociable), comisión (%), área.
3. **Ubicación**: dirección, ciudad, sector. Usa **"Ubicar en Mapa automáticamente"** para geocodificar.
4. **Personas**: propietario, apoderado (opcional), asesor responsable, co-asesor (opcional con % split).
5. **Características físicas**: habitaciones, baños, parqueaderos, piso, año de construcción.
6. Guarda. La propiedad nace en estado **Borrador**.

### 4.2 Pestañas de la ficha
| Pestaña | Contenido |
|---------|-----------|
| **Descripción** | Descripción comercial + herramientas de IA (ver 4.4). |
| **Multimedia** | Portada, galería (carga múltiple), Tour 360°, Código QR. |
| **Comercial** | Ofertas, historial de precios, ventas, AVM, datos del Negocio Cerrado. |
| **Financiero** | Simulador de crédito hipotecario. |
| **Publicación** | Estado de WordPress / web. |

### 4.3 Imágenes (pestaña Multimedia)
- **Imagen Principal (portada)**: la foto destacada que se publica.
- **Subir varias a la vez**: arrastra o selecciona **múltiples imágenes** desde tu computadora;
  al **guardar** se agregan a la galería.
- **Galería**: reordena arrastrando.

### 4.4 Descripción comercial con IA
- **Generar con IA (imagen + descripción)**: analiza la foto principal y redacta una descripción
  comercial profesional (formato HTML listo para portales).
- **Solo texto**: genera solo el texto, sin analizar imagen.
- **Detalles adicionales**: escribe lo que quieres resaltar (vista, acabados, cercanías…).
- **Refinar**: una vez generada, escribe instrucciones (*"hazla más corta"*, *"enfócate en la inversión"*)
  y pulsa **Aplicar cambios con IA**.
- El estilo/tono se configura en **Configuración → Agente IA → Estilo de Descripciones**.

### 4.5 Valoración automática (AVM)
- Botón **Calcular AVM**: estima el precio de mercado comparando propiedades similares
  (mismo tipo, sector, ±rango de precio) de los últimos meses.
- Resultado: **precio estimado**, estado (**justo / alto / bajo**), confianza y nº de comparables.
- El panel **Análisis IA** (barra derecha) interpreta el resultado y da recomendaciones.

### 4.6 Ciclo de vida
```
Borrador → [Publicar] → Disponible → [Reservar] → Reservado
                              │                        │
                              └──────[Vender / Arrendar]┘
                                          ↓
                                   Vendido / Arrendado → [Re-listar]
```
| Estado | Significado |
|--------|-------------|
| **Borrador** | En preparación, no visible al público. |
| **Disponible** | Publicada y ofertable. |
| **Reservado** | Apartada para un comprador. |
| **Vendido / Arrendado** | Operación cerrada. |

- **Publicar en Mercado**: pasa a Disponible (y sincroniza con WordPress si está configurado).
- **Reservar**: bloquea la propiedad.
- **Vender Propiedad**: abre el asistente de venta (ver §6).
- **Re-listar en Mercado**: reactiva una propiedad vendida/arrendada.

### 4.7 Panel "Análisis IA" (barra lateral derecha)
Resumen ejecutivo en vivo que se actualiza con la propiedad:
- **Ficha** (código, tipo, ubicación, m², habitaciones).
- **Precio**: precio/m², comparación con AVM.
- **Interesados**: leads directos + compatibles por presupuesto.
- **Visitas** registradas.
- **Alertas** (propietario sin asignar, AVM sin calcular, etc.).
- **Acción inmediata** sugerida.

### 4.8 Botones inteligentes (contadores)
Citas, Leads Interesados, Posts Personales, Documentos, Ofertas, Comisiones, Historial de Precios.
Haz clic en cada uno para ver el detalle.

---

## 5. Clientes y Leads (CRM)

**App:** CRM

### 5.1 Pipeline de Leads
- **CRM → Mi Pipeline**: embudo visual por etapas. **Arrastra** las tarjetas entre etapas
  (Nuevo → Calificado → Visita → Oferta → Ganado/Perdido).

### 5.2 Datos de un lead
| Campo | Descripción |
|-------|-------------|
| **Propiedad de interés** | Inmueble que busca el cliente. |
| **Presupuesto** | Cuánto puede pagar. |
| **% de Match** | Coincidencia presupuesto ↔ precio de la propiedad. |
| **Puntuación (Score)** | A (Prioritario), B (Cualificado), C (Básico). |
| **Temperatura** | Frío, Tibio, Caliente, ¡Hirviendo! |
| **Tips de negociación IA** | Sugerencias automáticas para cerrar. |

### 5.3 Clientes
- **CRM → Clientes → Directorio**: todos los contactos.
- **Nuevo cliente**: alta rápida.
- **Gestiones realizadas**: registro de cada llamada/visita/mensaje (interacciones).
- **Clientes Pendientes**: leads sin propiedad compatible. El sistema busca cada pocas horas
  nuevas propiedades que encajen y **notifica por WhatsApp** al cliente.
- **Red de Aliados**: inmobiliarias/agentes con quienes compartes inventario.

### 5.4 Cruce inmuebles ↔ clientes
**Inmobiliaria → Propiedades → Cruce inmuebles - clientes**: coincidencias automáticas
entre el inventario y los leads según presupuesto y preferencias.

---

## 6. Flujo de Venta

El cierre de una venta sigue un proceso **unificado y automático**:

1. En la propiedad (Disponible o Reservada), pulsa **Vender Propiedad**.
2. Completa el **asistente de venta** (datos del *Negocio Cerrado*):
   - Comprador, precio de cierre, fecha de cierre, comisión (%).
   - **Seña / Arras**, forma de pago (Contado, Hipotecario, Financiamiento del vendedor, Mixto).
   - **Fecha máxima de cumplimiento**, apoderado del comprador.
   - Si es hipotecario: institución y asesor de crédito.
   - Detalles y observaciones del negocio.
3. Al **Confirmar Venta**, el sistema automáticamente:
   - ✅ Crea y **confirma la Orden de Venta** (módulo Ventas).
   - ✅ Genera y **contabiliza la Factura** (módulo Facturación).
   - ✅ Marca la propiedad como **Vendida**.
   - ✅ Registra la **comisión** del asesor (dividida con co-asesor si aplica).
4. Imprime el documento **"Negocio Cerrado"** (botón Imprimir en la propiedad): replica la hoja
   de cierre con todos los datos y espacio para firmas.

> **Importante:** este flujo garantiza que cada venta quede registrada en los módulos nativos de
> **Ventas** y **Facturación**, por lo que los reportes financieros siempre cuadran.

### Arriendo
- Botón **Arrendar Propiedad**: registra el canon mensual y la comisión del primer mes.

---

## 7. Operaciones

**Ruta:** Inmobiliaria → Operaciones

### 7.1 Contratos
- Tipos: **Compraventa**, **Arriendo**, **Exclusividad**.
- **Redactar Contrato con IA**: la IA redacta el borrador legal del contrato (según tipo,
  propiedad y cliente) en la pestaña **Notas / Cláusulas**.
- Ciclo: Borrador → Activo → (Suspendido / En Renovación / Renovado / Vencido / Cancelado).
- **Firma del Cliente**, gestión de **pagos** del contrato, **renovaciones** automáticas.
- Los **PDF del contrato** (firmado/arras o documentos vinculados) se **previsualizan** en la barra derecha.

### 7.2 Ofertas
- Registro de ofertas recibidas (monto, descuento, financiamiento, estado).
- Aceptar una oferta puede generar la orden de venta.

### 7.3 Tasaciones
- Solicitudes de avalúo con motivo (Venta, Arriendo, Seguro/Hipoteca, Legal, Otro), fecha y resultado.

### 7.4 Solicitudes de Mantenimiento
- Pedidos de arrendatarios sobre el inmueble.

### 7.5 Depósitos / Garantías
- Garantías y depósitos de contratos de arriendo.

---

## 8. Documentos

**Ruta:** Inmobiliaria → Operaciones → Documentos

### 8.1 Subir y clasificar
1. **Nuevo** → nombre, **tipo** de documento (cédula, escritura, contrato…), confidencialidad.
2. **Vinculación**: relaciona el documento con una propiedad, contrato, cliente o lead.
3. Sube el **archivo**. Si es **PDF**, se **previsualiza** automáticamente en la barra derecha.

### 8.2 Extracción con IA (OCR)
- Botón **Extraer con IA**: Gemini Vision lee el documento y extrae los datos relevantes
  (nombres, fechas, montos, números de referencia) según su categoría.

### 8.3 Ciclo de vida del documento
```
Pendiente → Recibido → Verificado → Archivado
```
- **Verificar** (Manager): valida el documento.
- **Rechazar**: con motivo.

---

## 9. Finanzas

**Ruta:** Inmobiliaria → Finanzas

| Sección | Descripción |
|---------|-------------|
| **Pagos de Venta** | Cuotas y abonos de ventas. |
| **Pagos de Arrendamiento** | Cánones mensuales de arriendo. |
| **Gastos de Propiedad** | Gastos asociados a inmuebles. |
| **Comisiones** | Comisiones por asesor, con estado (Borrador → Aprobada → Pagada). |
| **Nómina / Sueldos** | Rol de pagos del asesor: sueldo base, bono de comisiones, subsidios, deducciones IESS, neto. |

### Comisiones
- Se generan automáticamente al vender/arrendar.
- **Estado de Pago de Comisiones** (en Reportes → Ventas): agrupa por estado para ver lo
  **devengado** (borrador/aprobada) vs lo **pagado**.
- **Liquidación de Comisiones** (en Reportes → Informes): genera el documento de liquidación.

---

## 10. Agenda y Visitas

**Ruta:** Inmobiliaria → Agenda

- **Calendario de Citas**: agenda visitas a propiedades (fecha, cliente, asesor, tipo).
- Las visitas envían **recordatorio por WhatsApp** ~1 hora antes (vía Meta WhatsApp Cloud API).
- Estados de visita: programada → realizada (con calificación) / cancelada.
- **Días no disponibles**: bloquea fechas para que no se agenden visitas.
- **Calculadora Hipotecaria**: simula cuotas (entrada, tasa, plazo) por sistema francés.

---

## 11. Reportes e Inteligencia de Negocio

**App:** Reportes

### 11.1 Dashboard Ejecutivo
Panel principal de gerencia con filtros (asesor, período: mes/trimestre/año/personalizado) y pestañas:

| Pestaña | Contenido |
|---------|-----------|
| **Resumen** | KPIs, indicadores financieros, **cumplimiento de metas** (barras con semáforo), tendencia vs período anterior. |
| **Gráficos** | Ventas por mes y leads por fuente (Chart.js interactivo). |
| **CRM / Embudo** | Funnel de conversión visual con % entre etapas. |
| **Asesores** | Ranking de asesores. |
| **Mercado** | Comparativa precio vs AVM y mapa de propiedades. |

- **Botones inteligentes** (arriba): Disponibles, Ofertas, Contratos, Visitas, Estancadas, Por Vencer
  — haz clic para abrir la lista filtrada.
- **Exportar a PDF**: informe ejecutivo del dashboard.
- **Pregunta a la IA** desde el propio dashboard.

### 11.2 Metas de Ventas
**Reportes → Ventas → Metas de Ventas**: define objetivos de **cierres**, **ingresos** y **comisiones**
por asesor y mes. El cumplimiento se calcula solo y aparece en el dashboard con semáforo
(🟢 ≥100% · 🟡 ≥70% · 🔴 <70%).

### 11.3 Secciones de Reportes
- **Ventas**: Ventas por Mes, Ranking de Asesores, Metas, Comisiones, Estado de Pago, Análisis de Cierres.
- **Análisis**: pivots y gráficos nativos por modelo (Propiedades, Contratos, Pagos, Ofertas, Gastos,
  Tasaciones, Mantenimiento, Por Tipo, Días en Mercado, Precio Promedio).
- **Informes**: Exportar Datos, Liquidación de Comisiones, Reporte de Visitas, Comparar Propiedades.
- **Tablero Gráfico**: vista alternativa con gráficos nativos de Odoo.

---

## 12. Asistente con Inteligencia Artificial

El asistente vive en el **botón flotante 🤖** (esquina inferior derecha), disponible en todo el sistema.

### 12.1 Cómo usarlo
- Escribe en lenguaje natural. El asistente entiende contexto (recuerda la propiedad/lead que ves).
- Responde con texto, **gráficos profesionales** (con toggle Línea/Barras), tablas y enlaces de descarga.
- Valora cada respuesta con 👍 / 👎 (queda registrado para mejorar el sistema).

### 12.2 Qué puede hacer
**Consultar:**
- *"¿Cuál es mi propiedad con más prospectos?"*
- *"¿Qué puedo mejorar en la casa de Baños?"* → recomendaciones (precio vs AVM, fotos, días en mercado, interesados).
- *"¿Cómo está mi propiedad en el Centro? ¿Quiénes están interesados?"*
- *"Estadísticas del mercado"*, *"Pagos vencidos"*, *"Visitas de esta semana"*.

**Reportes con gráficos:**
- *"Reporte de ventas por mes"*, *"Propiedades por tipo"*, *"Leads por temperatura"*,
  *"Ranking de asesores"*, *"Informe ejecutivo completo del mes"*.
- *"Descargar PDF del reporte"* / *"Exportar a Excel"*.

**Crear y gestionar:**
- *"Crea un lead para Juan Pérez, presupuesto 150000"*.
- *"Agenda una visita a [propiedad] el 15 de julio a las 10"*.
- *"Reserva la propiedad PROP-0052"*, *"Cambia el precio de [propiedad] a 200000"*.

**Marketing y análisis:**
- *"Genera una descripción de marketing para [propiedad]"*.
- *"Plan de campaña de marketing para [propiedad]"*.
- *"Recalcula el AVM de [propiedad]"*, *"Compara estas dos propiedades"*.

> Si una herramienta específica no cubre la pregunta, el asistente puede consultar la base de datos
> directamente para responder cualquier cosa.

---

## 13. Integraciones

| Integración | Función |
|-------------|---------|
| **WordPress** | Publica y sincroniza propiedades al sitio web (tema Houzez). |
| **Redes Sociales** | Publica en Facebook/Instagram y registra posts personales de asesores; estadísticas. |
| **WhatsApp** | Recordatorios de visitas y notificaciones a clientes (Meta Cloud API). |
| **n8n** | Workflows de automatización (agentes virtuales, búsquedas, catálogos). Ver carpeta `n8n/`. |
| **IA (Gemini / OpenAI)** | Descripciones, OCR, contratos, chat, análisis. |

> La configuración de cada integración está en **Configuración** y en los Ajustes técnicos.

---

## 14. Configuración

**Ruta:** Inmobiliaria → Configuración (Manager / Administrador)

- **Roles Inmobiliarios** y **Usuarios del Sistema**.
- **Tipos de Inmueble** y **Tipos de Documento** (datos maestros).
- **Asistente IA** (en Ajustes → Agente IA):
  - Proveedor (Google Gemini / OpenAI), **API Key**, modelo.
  - **Estilo de Descripciones** de propiedad (tono editable).
  - Prompt del sistema del chat.
- Integraciones: WordPress, redes sociales, WhatsApp Business.

---

## 15. Preguntas frecuentes y solución de problemas

**No veo el botón "Vender Propiedad".**
La propiedad debe estar **Disponible** o **Reservada**, y de tipo Venta. En Borrador, primero publícala.

**El asistente IA no responde / da error.**
Verifica en **Configuración → Agente IA** que haya una **API Key** válida y que el agente esté activo.

**La descripción con IA sale incompleta.**
Revisa que la propiedad tenga datos suficientes (precio, área, tipo). El sistema ya está optimizado
para generar descripciones completas.

**No se publica en WordPress (error 401).**
El usuario de WordPress necesita rol **Editor** o superior, y una Application Password válida.

**Un contrato/tasación de arriendo no abría.**
Resuelto: el sistema ahora admite el tipo **Arriendo** en contratos y tasaciones.

**¿Dónde están mis backups?**
En `~/odoo_backups/` (diarios automáticos). Usa `scripts/restore_odoo.sh` para restaurar.

---

## 16. Glosario

| Término | Significado |
|---------|-------------|
| **AVM** | *Automated Valuation Model* — valoración automática de mercado. |
| **Lead** | Prospecto / oportunidad de venta en el CRM. |
| **Score (A/B/C)** | Calidad del lead: Prioritario / Cualificado / Básico. |
| **Temperatura** | Cercanía al cierre: Frío → Tibio → Caliente → Hirviendo. |
| **Negocio Cerrado** | Conjunto de datos del cierre de una venta (comprador, seña, pago, etc.). |
| **Comisión devengada vs pagada** | Generada pero pendiente de pago vs ya pagada. |
| **Chatter** | Panel de mensajes e historial a la derecha de cada ficha. |
| **Filestore** | Almacenamiento en disco de adjuntos, imágenes y PDFs. |
| **Pipeline** | Embudo de oportunidades del CRM. |

---

*Inmobi Community — Sistema de Gestión Inmobiliaria sobre Odoo 19.*
*Para soporte técnico, consulta la documentación en la carpeta `docs/`.*
