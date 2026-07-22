# Diapositivas — Sustentación de Trabajo de Titulación

**Diseño e Implementación de un Sistema de Gestión Inmobiliaria basado en ERP Odoo con Integración de un Agente Inteligente para Consulta y Generación de Reportes**

Autor: Justin Mateo Lucero Reyes · Tutor: Ing. Cristian Fernando Timbi Sisalima, Mgtr.
Universidad Politécnica Salesiana — Sede Cuenca — Carrera de Computación

> Guía de contenido por diapositiva. Cada bloque = 1 diapositiva. Los puntos son el texto sugerido (llévalo a viñetas cortas en el diseño real, no copies párrafos completos a la diapositiva). Las notas en *cursiva* son sugerencias de qué decir en voz / qué mostrar, no van en la diapositiva.

---

## 1. Portada

- Universidad Politécnica Salesiana — Sede Cuenca — Carrera de Computación
- **Diseño e Implementación de un Sistema de Gestión Inmobiliaria basado en ERP Odoo con Integración de un Agente Inteligente para Consulta y Generación de Reportes**
- Autor: Justin Mateo Lucero Reyes
- Tutor: Ing. Cristian Fernando Timbi Sisalima, Mgtr.
- Cuenca — Ecuador — 2026

*Diapositiva de apertura, 15-20 segundos: preséntate, el título y agradece al tutor/tribunal.*

---

## 2. Agenda

- Problema y contexto
- Objetivos
- Marco teórico (breve)
- Metodología
- Arquitectura de la solución
- Resultados por objetivo específico
- Pruebas y validación
- Conclusiones y recomendaciones

---

## 3. El problema

- Empresa **Inmobi** (Cuenca) gestiona propiedades, clientes y contratos con **hojas de cálculo, registros manuales y aplicaciones no integradas**.
- Consecuencias: duplicación de información, pérdida de datos, sin seguimiento de negociaciones, reportes poco confiables.
- Resultado de negocio: **retrasos en la atención y pérdida de oportunidades de venta**.

*Muestra aquí, si quieres, 1-2 capturas o mockups de las hojas de cálculo que usaban antes (si las tienes) — el contraste "antes vs. después" es lo que más convence al tribunal.*

---

## 4. Trabajos relacionados (antecedentes)

- Gonzales-Saji (2024) — falta de digitalización en inmobiliarias, implementa un Odoo básico.
- Daud et al. / Utami (2024) — ERP en PYMES mejora la gestión por su flexibilidad.
- Alshamsi & Mellor (2020) — agentes inteligentes en ERP automatizan tareas y apoyan decisiones.
- Sadeghian (2021) — IA en CRM mejora la relación con clientes en el sector inmobiliario.
- **Brecha que cubre esta tesis:** ninguno integra los tres a la vez (ERP inmobiliario completo + CRM con matching + agente de IA operativo) sobre un caso real.

---

## 5. Importancia, alcance y delimitación

- **Beneficiarios:** gerencia (control y reportes confiables), asesores (seguimiento estructurado, más productividad), clientes finales (atención más ágil).
- **Delimitación geográfica:** Cuenca, Azuay, Ecuador.
- **Delimitación temporal:** mayo–julio de 2026.
- **Delimitación sectorial/institucional:** sector inmobiliario — empresa Inmobi.

---

## 6. Objetivo general

> Diseñar e implementar un sistema de gestión inmobiliaria basado en ERP Odoo con integración de un agente inteligente para consulta y generación de reportes.

---

## 7. Objetivos específicos

- **OE1.** Identificar las falencias en la gestión de propiedades y reportes del modelo actual para definir los requisitos.
- **OE2.** Desarrollar módulos a medida en Odoo que respondan a esos requisitos.
- **OE3.** Diseñar e integrar un agente inteligente que consuma los datos del sistema en lenguaje natural.
- **OE4.** Integrar técnicamente los componentes y desplegar en producción.
- **OE5.** Evaluar las mejoras obtenidas en eficiencia, organización y acceso a la información.

*Este slide es el "mapa" de toda la sustentación: cada bloque de resultados que viene después se ordena exactamente por OE1→OE5. Dilo explícitamente: "voy a mostrar los resultados en el mismo orden de estos 5 objetivos".*

---

## 8. Marco teórico (síntesis)

- **Sistemas ERP:** centralizan información, reducen duplicación, automatizan tareas (Montero, 2021).
- **Odoo:** arquitectura modular y de código abierto — se instala solo lo que la empresa necesita y se puede extender sin tocar el núcleo (Cayo, 2022).
- **Agentes inteligentes / chatbots:** permiten consultar y operar el sistema en lenguaje natural, sin curva de aprendizaje técnica (Pérez, 2023).
- **Integración ERP–web–mensajería vía APIs:** mantiene consistente la información en todos los canales (Sánchez, 2020).

---

## 9. Metodología: Scrum en 6 sprints

| Sprint | Módulos | Entregable principal |
|---|---|---|
| 1 | Gestión Inmobiliaria | Inventario, estados y contratos |
| 2 | CRM Inmobiliario | Leads y algoritmo de match presupuestal |
| 3 | Calendario y Documental | Visitas, recordatorios WhatsApp, OCR |
| 4 | Reportes y Analítica | Dashboards KPI, exportación PDF/Excel |
| 5 | Ecosistema Web (WordPress) | Portal público sincronizado |
| 6 | Inteligencia Artificial | Agente conversacional, AVM, alertas |

- Cliente validador: Inmobi. Ciclo por sprint: construir → probar con datos reales → mostrar al cliente → corregir.

---

## 10. Arquitectura de la solución (3 capas)

*Mostrar aquí la Figura 4 del informe (Arquitectura del Sistema en Tres Capas).*

- **Presentación:** cliente web de Odoo (OWL/JS), sitio público (WordPress), chat flotante del agente.
- **Lógica de negocio:** servidor Odoo 19 (Python) — reglas, CRM, cron jobs, agente IA.
- **Datos:** PostgreSQL + sistema de archivos (adjuntos, QR, memoria del agente).
- Comunicación asegurada con **Nginx como proxy inverso + SSL**; integraciones externas vía API (Google Gemini/OpenAI, WhatsApp Cloud API, WordPress REST, Google Calendar).

---

## 11. Entorno de desarrollo y despliegue

- Odoo 19 Community + Python + PostgreSQL + OWL.
- Producción: **VPS Ubuntu Server (Hostinger)**, desplegado con **Docker** (reproducible y aislado).
- Código versionado con Git, repositorio en GitHub.
- Dominio propio con **HTTPS** (certificados renovados automáticamente).

---

## 12. OE1 — Requisitos

- Levantamiento con entrevistas al gerente y asesores + observación directa de sus herramientas.
- Falencias detectadas: información dispersa y duplicada por asesor, sin seguimiento formal de negociaciones, reportes lentos y armados a mano.
- Resultado: **33 requisitos funcionales + 8 no funcionales**, documentados con matriz de trazabilidad hacia cada módulo.

---

## 13. OE2 — Los 12 módulos del sistema

*Mostrar aquí la Figura 1 del informe (Organización modular del sistema y dependencias).*

| Módulo | Función |
|---|---|
| Gestión de propiedades | Núcleo: estados, contratos, pagos, comisiones, AVM, QR |
| CRM inmobiliario | Leads, puntuación A/B/C, match presupuestal |
| Calendario de visitas | Citas + recordatorios WhatsApp + Google Calendar |
| Gestión documental | Documentos con OCR |
| Reportes y analítica | KPIs, exportación PDF/Excel |
| Redes sociales | Publicación y estadísticas |
| Sincronización WordPress | Sitio público automático |
| Agente de IA | Asistente conversacional |
| Auditoría | Bitácora de cambios |
| Nómina de asesores | Cálculo y recibo de pago |
| *(+ Portal del propietario)* | |

---

## 14. Gestión de propiedades

- Ficha única por inmueble: ubicación con mapa, características físicas, fotos, propietario/comprador/asesor.
- Estados controlados (borrador → disponible → reservada → vendida/arrendada) — **ya no se puede vender dos veces el mismo inmueble**.
- Cálculo automático de días en mercado, comisión y **código QR** por propiedad.
- **AVM (valoración automática):** compara con ventas similares de la misma ciudad/tipo y clasifica el precio como justo, alto o bajo.

*Mostrar Figura 5/6 del informe: listado y ficha de propiedad.*

---

## 15. CRM inmobiliario

- Cada lead registra presupuesto y preferencias; el sistema calcula el **% de coincidencia** con las propiedades disponibles.
- Puntuación automática **A/B/C** + temperatura comercial (frío/tibio/caliente/hirviendo).
- Leads del sitio web y redes sociales entran directo al sistema, sin digitación manual.

*Mostrar Figura 7: kanban del CRM con leads clasificados.*

---

## 16. Contratos, pagos y visitas

- Ciclo de vida completo del contrato (borrador → activo → renovación → vencido/cancelado), con encadenamiento de renovaciones.
- Cada pago actualiza el saldo y puede generar factura, con trazabilidad de la comisión del asesor.
- Visitas integradas al calendario: recordatorio automático por WhatsApp 1 hora antes + encuesta de satisfacción después.

---

## 17. Reportes y sitio web

- Tablero de indicadores (KPI): metas de cierres, ingresos y comisiones, con % de cumplimiento — exportable a PDF/Excel con un clic.
- Sincronización con WordPress: publicar/editar una propiedad en Odoo actualiza el sitio automáticamente; al venderla, se retira sola.

*Mostrar Figura 8: tablero de KPIs.*

---

## 18. Modelo de datos

*Mostrar aquí la Figura 2 del informe (diagrama entidad-relación con herencia de modelos).*

- Entidades núcleo: `estate.property`, `crm.lead`, `estate.contract`, `estate.payment`, `estate.commission`.
- Mixins reutilizables: `mail.thread`, `mail.activity.mixin`, `estate.phone.mixin`, `estate.audit.mixin`, `estate.genai.mixin`.

---

## 19. OE3 — El agente inteligente

- Asistente conversacional integrado en el propio ERP: chat flotante + panel de análisis por propiedad.
- Funciona con **Google Gemini u OpenAI** (configurable, con respaldo automático entre proveedores).
- Dispone de **más de 50 herramientas** (function calling): consultar, crear/actualizar registros, agendar visitas, generar reportes PDF/Excel, analizar imágenes, redactar descripciones comerciales.

*Mostrar aquí la Figura 3 del informe (flujo del agente) y, si es posible, una demo en vivo o la Figura 9 (conversación real).*

---

## 20. Cómo "razona" el agente

- **RAG (Retrieval-Augmented Generation):** los manuales del sistema se indexaron por fragmentos; el agente responde dudas de uso citando la documentación real, no inventa procedimientos.
- **Memoria persistente:** recuerda preferencias y datos de clientes entre conversaciones.
- **Alertas proactivas:** revisa el negocio a diario y avisa solo, por ejemplo, cuando un cliente muy interesado lleva días sin respuesta.
- **Análisis de imágenes (multimodal):** lee documentos escaneados (OCR) y genera descripciones comerciales a partir de fotos de la propiedad.

---

## 21. OE4 — Integración y despliegue en producción

- Todos los componentes probados de forma integral antes de pasar a producción real.
- VPS Ubuntu + Docker: PostgreSQL, Odoo, Nginx (proxy + SSL) y renovación automática de certificados.
- Ajustes de operación: índices en BD para búsquedas rápidas, respaldo automático diario, y **tolerancia a fallos**: si el proveedor de IA activo falla, reintenta con el proveedor de respaldo automáticamente.

---

## 22. OE5 — Comparativa: antes vs. después

| Aspecto | Antes | Con el sistema |
|---|---|---|
| Registro de propiedades | Hojas de cálculo, duplicados | Ficha única, sin duplicados |
| Seguimiento de clientes | Anotaciones informales | Leads clasificados y priorizados |
| Recordatorios de citas | Dependían de la memoria del asesor | Automáticos por WhatsApp |
| Control de contratos | Vencimientos sin vigilancia | Alertas automáticas |
| Publicación web | Manual | Sincronización automática |
| Reportes | Consolidación manual, con errores | Tablero en tiempo real |
| Consulta de información | Buscar en varios archivos | Preguntar en lenguaje natural |

- **18 tareas programadas** (crons) reemplazan trabajo que antes era manual o simplemente no se hacía.

---

## 23. Validación y pruebas

- **167 pruebas automatizadas** (unitarias + integración) con el framework de Odoo — **todas superadas**.
- Verifican reglas críticas: estados de propiedades y contratos, cálculo de comisiones, puntuación de leads, seguridad por roles.
- Validación con usuarios finales de Inmobi en reuniones de revisión + Manual de Usuario para apoyar la adopción.

*Este es tu slide de "credibilidad técnica" — insiste en que las 167 pruebas dan evidencia objetiva, no solo "funciona en mi máquina".*

---

## 24. Cumplimiento de objetivos

| Objetivo | Estado | Evidencia |
|---|---|---|
| OE1 | Cumplido | Requisitos + matriz de trazabilidad |
| OE2 | Cumplido | 12 módulos operativos |
| OE3 | Cumplido | Agente con lenguaje natural, RAG, memoria, alertas |
| OE4 | Cumplido | Sistema desplegado en producción (VPS + HTTPS) |
| OE5 | Cumplido | Información centralizada, automatización verificada |

---

## 25. Cronograma y presupuesto (resumen)

- Ejecución: **04 de mayo al 20 de julio de 2026** — 240 horas planificadas, distribuidas en los 5 objetivos específicos.
- Presupuesto total: **USD 4,830** (equipo, servidor VPS, consumo de API de IA, desarrollo).

---

## 26. Conclusiones

- El levantamiento de requisitos tradujo las falencias reales de Inmobi en 33 requisitos funcionales + 8 no funcionales, verificables.
- La arquitectura modular de Odoo permitió construir, de forma incremental, una solución a medida sin depender de software comercial costoso.
- El agente inteligente (+50 herramientas, function calling) convierte al ERP en un asistente operativo real: consulta, ejecuta acciones, genera reportes y documentos, y alerta proactivamente.
- 18 tareas automáticas y 167 pruebas superadas son evidencia objetiva de que el sistema resuelve las causas reales del problema, no solo sus síntomas.

---

## 27. Recomendaciones

1. Monitorear el despliegue: respaldos automáticos, uso de recursos, certificados y dependencias actualizadas.
2. Ejecutar la evaluación formal de mejoras (OE5) con KPIs medidos antes/después.
3. Capacitar al personal apoyándose en el Manual de Usuario, especialmente en el uso del agente.
4. Gobernar el costo de las APIs de IA (límites y monitoreo de consumo).
5. Mantener activos los respaldos diarios y verificar el procedimiento de restauración.
6. Custodiar credenciales (API keys, cuenta de servicio) fuera del código fuente.
7. Evolución futura: firma electrónica avanzada en contratos, más acciones proactivas del agente, nuevas fuentes de datos para el AVM.

---

## 28. Cierre

- Gracias — Preguntas del tribunal.

*Ten a mano, por si preguntan: (1) el chat del agente funcionando en vivo, (2) el código en GitHub, (3) el manual de usuario en PDF.*
