# Documento de Análisis y Especificación de Requisitos

**Proyecto:** Diseño e implementación de un sistema de gestión inmobiliaria basado en ERP Odoo con integración de un agente inteligente para consulta y generación de reportes.
**Empresa cliente:** Inmobi (Cuenca, Ecuador)
**Autor:** Justin Mateo Lucero Reyes
**Objetivo específico cubierto:** OE1 — Identificar las falencias en la gestión de propiedades y reportes del modelo actual para definir los requisitos funcionales y técnicos.

---

## 1. Introducción

Este documento corresponde a la fase de **levantamiento y análisis de requisitos** (OE1). Recoge la información obtenida del cliente (Inmobi) mediante entrevistas y observación directa de sus procesos, analiza la situación actual y, a partir de ello, define los **requisitos funcionales (RF)** y **no funcionales (RNF)** que la solución personalizada en Odoo debe cubrir.

La especificación sigue una adaptación del estándar **IEEE 830** (Especificación de Requisitos de Software) ajustada al alcance de un proyecto técnico de titulación.

---

## 2. Metodología de levantamiento de información

| Técnica | Descripción | Fuente |
|---------|-------------|--------|
| Entrevista semiestructurada | Reuniones con el personal de Inmobi (gerencia y asesores) para entender el flujo de trabajo. | Personal de Inmobi |
| Observación directa | Revisión de las herramientas actuales (hojas de cálculo, registros manuales, sitio web). | Procesos en sitio |
| Análisis documental | Inspección de las plantillas, contratos y reportes que la empresa usa hoy. | Documentación interna |

El levantamiento se ejecutó conforme a las actividades **1.1 (entrevistas), 1.2 (análisis de procesos) y 1.3 (documentación de requisitos)** del cronograma.

---

## 3. Entrevistas a Inmobi (síntesis)

### 3.1. Entrevista a Gerencia

> **¿Cómo gestionan hoy las propiedades y los clientes?**
> "Tenemos las propiedades en hojas de Excel y algunas en una aplicación que no es nuestra. Cada asesor lleva su propio archivo, así que muchas veces la misma propiedad está repetida o con precios distintos."

> **¿Qué problemas les genera esto?**
> "Se nos pierde información, no sabemos en qué estado va cada negociación y cuando quiero un reporte de ventas tengo que pedir que junten los archivos a mano. Eso toma días y casi siempre hay errores."

> **¿Qué esperan del nuevo sistema?**
> "Que todo esté en un solo lugar, que se pueda ver el estado de cada propiedad y contrato, y ojalá que avise automáticamente las visitas y vencimientos. Y si se puede preguntar cosas al sistema en lenguaje normal, mejor."

### 3.2. Entrevista a Asesores comerciales

> **¿Cómo hacen seguimiento a un cliente interesado?**
> "Anotamos en el cuaderno o en el celular. A veces se nos pasa llamar o agendar la visita."

> **¿Cómo publican en la web?**
> "Subimos la propiedad manualmente al WordPress. Si cambia el precio en el Excel, hay que volver a editarla en la web; muchas veces queda desactualizada."

> **¿Qué reportes necesitan?**
> "Saber cuántas propiedades hay disponibles, cuáles llevan mucho tiempo sin venderse, comisiones por asesor y las visitas de la semana."

---

## 4. Análisis de la situación actual

### 4.1. Herramientas usadas hoy

| Proceso | Herramienta actual | Problema detectado |
|---------|-------------------|--------------------|
| Registro de propiedades | Hojas de cálculo (Excel) | Duplicación, datos inconsistentes |
| Gestión de clientes/leads | Cuaderno, celular, Excel | Sin seguimiento, oportunidades perdidas |
| Contratos y pagos | Plantillas Word + registros manuales | Sin control de vencimientos ni saldos |
| Publicación web | Carga manual en WordPress | Información desactualizada |
| Agendamiento de visitas | Memoria / mensajes sueltos | Olvidos, sin recordatorios |
| Reportes | Consolidación manual de archivos | Lento, propenso a errores |

### 4.2. Falencias identificadas (resumen)

- **F1.** Información dispersa y duplicada (sin fuente única de verdad).
- **F2.** Falta de seguimiento del ciclo de vida de propiedades y negociaciones.
- **F3.** Ausencia de reportes confiables para la toma de decisiones.
- **F4.** Procesos manuales sin automatización (visitas, contratos, publicación web).
- **F5.** Comunicación con el cliente poco oportuna (sin recordatorios automáticos).
- **F6.** Desconexión entre el sitio web y los datos internos.

---

## 5. Requisitos Funcionales (RF)

> Nomenclatura: **RF-XX**. Prioridad: Alta / Media / Baja.

### 5.1. Gestión de propiedades (Núcleo)

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-01 | Registrar propiedades con datos de ubicación, atributos físicos (área, habitaciones, baños, parqueos), precio y fotografías. | Alta |
| RF-02 | Controlar el ciclo de vida de la propiedad mediante estados (disponible → reservada → vendida/arrendada). | Alta |
| RF-03 | Generar automáticamente un código QR por propiedad. | Media |
| RF-04 | Calcular una valoración automática (AVM) y clasificarla (justa/alta/baja). | Media |
| RF-05 | Registrar gastos, ofertas e historial de precios por propiedad. | Media |
| RF-06 | Generar descripción y análisis visual de la propiedad mediante IA a partir de imágenes. | Media |

### 5.2. CRM y clientes

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-07 | Registrar leads/oportunidades con presupuesto y preferencias del cliente. | Alta |
| RF-08 | Calcular el porcentaje de coincidencia (match) entre el presupuesto del cliente y las propiedades. | Alta |
| RF-09 | Clasificar leads por puntaje (A/B/C) y temperatura (frío/tibio/caliente/hirviendo). | Media |
| RF-10 | Registrar interacciones con el cliente y avanzar la oportunidad por etapas. | Media |

### 5.3. Contratos y pagos

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-11 | Gestionar contratos de venta y arriendo con estados y fechas de inicio/fin. | Alta |
| RF-12 | Registrar pagos asociados a contratos y calcular saldos pendientes. | Alta |
| RF-13 | Calcular y registrar comisiones por asesor. | Media |
| RF-14 | Almacenar firma del cliente y documentos firmados del contrato. | Media |
| RF-15 | Alertar sobre vencimientos de contratos (tarea programada). | Media |

### 5.4. Calendario y visitas

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-16 | Agendar visitas asociadas a una propiedad y un cliente. | Alta |
| RF-17 | Enviar recordatorios automáticos de visita por WhatsApp. | Alta |
| RF-18 | Registrar el resultado y la calificación de la visita. | Media |
| RF-19 | Sincronizar las visitas con un Google Calendar compartido del equipo. | Baja |

### 5.5. Documentos

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-20 | Almacenar documentos vinculados a propiedades, clientes y contratos. | Media |
| RF-21 | Extraer texto de documentos mediante OCR con IA (Gemini Vision). | Media |

### 5.6. Reportes y analítica

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-22 | Mostrar un dashboard con KPIs (ventas, propiedades, visitas, comisiones). | Alta |
| RF-23 | Exportar reportes en PDF y Excel. | Alta |
| RF-24 | Generar reportes de ventas con métricas (precio promedio, % vs listado, días en mercado). | Media |

### 5.7. Integraciones

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-25 | Publicar y sincronizar propiedades automáticamente con el sitio WordPress. | Alta |
| RF-26 | Compartir propiedades en redes sociales (Facebook/WhatsApp). | Baja |
| RF-27 | Recibir leads desde formularios web/Meta mediante webhooks. | Media |

### 5.8. Agente inteligente

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-28 | Consultar el sistema mediante lenguaje natural (chat). | Alta |
| RF-29 | Generar reportes y análisis bajo demanda desde el chat. | Alta |
| RF-30 | Emitir alertas proactivas diarias (oportunidades, vencimientos). | Media |
| RF-31 | Soportar más de un proveedor de IA (Google Gemini y OpenAI). | Media |

### 5.9. Seguridad y auditoría

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-32 | Controlar el acceso por roles y permisos. | Alta |
| RF-33 | Registrar una bitácora de auditoría de cambios (crear/editar/eliminar). | Media |

---

## 6. Requisitos No Funcionales (RNF)

| ID | Requisito | Descripción |
|----|-----------|-------------|
| RNF-01 | **Usabilidad** | Interfaz web amigable (OWL), en español, con estados vacíos guiados. |
| RNF-02 | **Rendimiento** | Respuesta de consultas habituales en pocos segundos. |
| RNF-03 | **Disponibilidad** | Despliegue en VPS con proxy inverso Nginx y respaldo automático diario. |
| RNF-04 | **Seguridad** | Cifrado SSL/TLS, credenciales fuera del código, control de acceso por grupos. |
| RNF-05 | **Mantenibilidad** | Arquitectura modular; cada funcionalidad en su módulo independiente. |
| RNF-06 | **Escalabilidad** | Posibilidad de añadir módulos sin afectar el núcleo. |
| RNF-07 | **Portabilidad** | Despliegue contenerizado (Docker) reproducible. |
| RNF-08 | **Robustez** | Si una integración externa (IA, WhatsApp, Google) falla, el trabajo diario no se interrumpe. |

---

## 7. Matriz de trazabilidad (Requisito → Módulo implementado)

| Requisito | Módulo Odoo que lo implementa |
|-----------|------------------------------|
| RF-01 a RF-06 | `estate_management` |
| RF-07 a RF-10 | `estate_crm` |
| RF-11 a RF-15 | `estate_management` (contratos, pagos, comisiones) |
| RF-16 a RF-19 | `estate_calendar`, `estate_gcal` |
| RF-20, RF-21 | `estate_document` |
| RF-22 a RF-24 | `estate_reports` |
| RF-25 | `estate_wordpress` |
| RF-26, RF-27 | `estate_social`, `estate_crm` (webhooks) |
| RF-28 a RF-31 | `estate_ai_agent` |
| RF-32 | Seguridad de Odoo (`ir.model.access`, grupos) |
| RF-33 | `estate_audit` |

> **Conclusión de OE1:** los requisitos levantados a partir de las falencias de Inmobi quedan cubiertos por los módulos personalizados desarrollados. Esta matriz sirve como base de verificación para la fase de evaluación (OE5).

---

*Documento de requisitos — Proyecto de Titulación, Universidad Politécnica Salesiana, Sede Cuenca.*
