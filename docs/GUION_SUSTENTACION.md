# Guion de Sustentación — Diapositiva por Diapositiva

Complementa a `PRESENTACION_DIAPOSITIVAS.md`. Este documento es lo que **dices en voz**, no lo que va escrito en la diapositiva. Está pensado para hablar con naturalidad, no para leer palabra por palabra — apréndetelo por idea, no de memoria.

> Nota sobre tiempos: 28 diapositivas × ~30-40 segundos cada una ≈ 15-18 minutos, típico para una sustentación. Ajusta según el tiempo que te asignen.

---

## 1. Portada
"Buenos días/tardes. Mi nombre es Justin Mateo Lucero Reyes y voy a presentar mi trabajo de titulación: *Diseño e Implementación de un Sistema de Gestión Inmobiliaria basado en ERP Odoo con Integración de un Agente Inteligente para Consulta y Generación de Reportes*, dirigido por el Ing. Cristian Timbi. Antes de empezar, agradezco al tribunal por su tiempo."

## 2. Agenda
"La presentación va a seguir este orden: primero el problema que encontramos, los objetivos que planteamos para resolverlo, un marco teórico breve, la metodología de trabajo, la arquitectura de la solución, y luego los resultados — organizados exactamente en el mismo orden que los cinco objetivos específicos. Cierro con pruebas, conclusiones y recomendaciones."

## 3. El problema
"Inmobi es una inmobiliaria real de Cuenca que hasta antes de este proyecto gestionaba todo su negocio con hojas de cálculo, cuadernos y aplicaciones sueltas que no se comunicaban entre sí. Esto generaba tres problemas concretos: información duplicada porque cada asesor tenía su propio archivo, pérdida de datos, y ningún seguimiento formal de las negociaciones con los clientes. El resultado de negocio era medible: retrasos en la atención y oportunidades de venta que se perdían simplemente por desorganización."

## 4. Trabajos relacionados
"Revisamos investigaciones previas para ubicar este trabajo. Encontramos estudios que implementan Odoo básico en inmobiliarias, otros que muestran cómo el ERP mejora la gestión en PYMES, y trabajos que analizan agentes inteligentes dentro de ERPs o IA en sistemas CRM. Lo que noto es que ninguno de esos trabajos junta las tres cosas a la vez —un ERP inmobiliario completo, un CRM con algoritmo de coincidencia, y un agente de IA operativo— sobre un caso real de una empresa. Ese es el aporte diferenciador de este proyecto."

## 5. Importancia, alcance y delimitación
"Este proyecto beneficia a tres grupos: la gerencia, que obtiene control centralizado y reportes confiables; los asesores comerciales, que ganan seguimiento estructurado y más productividad; y los clientes finales, que reciben atención más ágil. En cuanto a delimitación: se desarrolló en Cuenca, provincia del Azuay, entre mayo y julio de 2026, para el sector inmobiliario, específicamente para la empresa Inmobi."

## 6. Objetivo general
"El objetivo general fue diseñar e implementar un sistema de gestión inmobiliaria basado en ERP Odoo, con integración de un agente inteligente para consulta y generación de reportes."

## 7. Objetivos específicos
"Ese objetivo general se desglosó en cinco objetivos específicos: primero, identificar las falencias del modelo actual para definir requisitos; segundo, desarrollar los módulos que cubran esos requisitos; tercero, integrar el agente inteligente; cuarto, integrar todo técnicamente y desplegarlo en producción; y quinto, evaluar las mejoras obtenidas. Voy a presentar los resultados exactamente en este orden, así que quédense con esta diapositiva en mente."

## 8. Marco teórico
"Brevemente, cuatro pilares teóricos sustentan las decisiones de diseño: los sistemas ERP centralizan información y reducen duplicación; Odoo específicamente tiene una arquitectura modular y de código abierto que permite extenderlo sin tocar el núcleo; los agentes inteligentes permiten consultar sistemas complejos en lenguaje natural, sin curva de aprendizaje técnica; y la integración vía APIs entre el ERP, la web y la mensajería mantiene consistente la información en todos los canales donde el cliente puede encontrar la inmobiliaria."

## 9. Metodología: Scrum en 6 sprints
"El desarrollo siguió la metodología ágil Scrum, en seis sprints de dos semanas cada uno, con Inmobi como cliente validador en cada ciclo. Cada sprint entregó un bloque funcional completo: primero gestión inmobiliaria, luego CRM, calendario y documental, reportes, el ecosistema web con WordPress, y por último la inteligencia artificial. Al cerrar cada sprint se hacía una revisión con el cliente para validar que lo construido resolviera un problema real, no solo que funcionara técnicamente."

## 10. Arquitectura de la solución
"La solución se diseñó con una arquitectura de tres capas, que es un patrón estándar para desacoplar responsabilidades. La capa de presentación incluye el cliente web de Odoo, el sitio público en WordPress, y el chat flotante del agente de IA. La capa de lógica de negocio es el servidor Odoo, que procesa las reglas del CRM y las tareas automatizadas. Y la capa de datos es PostgreSQL más el sistema de archivos para adjuntos y códigos QR. Toda la comunicación pasa por Nginx como proxy inverso con cifrado SSL."

## 11. Entorno de desarrollo y despliegue
"El desarrollo se hizo en un entorno local sobre Odoo 19 Community con Python y PostgreSQL. Para producción se contrató un servidor virtual privado en Hostinger, y el despliegue se hizo con contenedores Docker, lo que garantiza que la instalación sea reproducible y esté aislada. El código se versionó con Git en un repositorio de GitHub para conservar el historial completo de cambios."

## 12. OE1 — Requisitos
"Para el primer objetivo, el levantamiento se hizo con entrevistas al gerente y a los asesores de Inmobi, más observación directa de las herramientas que usaban a diario. De ahí se identificaron las falencias reales: información dispersa y duplicada entre archivos de cada asesor, cero seguimiento formal de las negociaciones, y reportes que tomaban horas armar a mano y aun así tenían errores. Ese análisis se tradujo en 33 requisitos funcionales y 8 no funcionales, cada uno trazado a un módulo específico del sistema mediante una matriz de trazabilidad."

## 13. OE2 — Los 12 módulos
"Para el segundo objetivo se construyeron doce módulos personalizados sobre Odoo, cada uno independiente pero conectado al núcleo de gestión inmobiliaria. [Aquí señala el diagrama y ve mencionando 3-4 módulos clave en voz alta: gestión de propiedades, CRM, calendario, reportes] — todos dependen del núcleo `estate_management`, que centraliza propiedades, contratos, pagos y comisiones."

## 14. Gestión de propiedades
"El módulo núcleo le da a cada inmueble una ficha única: ubicación con mapa, características físicas, fotos, y su relación con propietario, comprador y asesor. Los estados de la propiedad —disponible, reservada, vendida, arrendada— tienen transiciones validadas, así que ya es imposible, por ejemplo, vender dos veces el mismo inmueble, algo que sí pasaba antes con las hojas de cálculo. Un resultado que destaco es la valoración automática, el AVM: el sistema compara la propiedad con ventas similares de la misma ciudad y tipo, y le dice al asesor si el precio publicado está justo, alto o bajo — eso le da a la empresa un criterio objetivo para negociar, que antes no existía."

## 15. CRM inmobiliario
"En el CRM, cada cliente potencial registra su presupuesto y preferencias, y el sistema calcula automáticamente qué tan bien encaja con cada propiedad disponible. Con ese cruce, cada lead recibe una puntuación A, B o C y una 'temperatura' comercial —frío, tibio, caliente, hirviendo— para que el asesor sepa a quién atender primero. Y los formularios del sitio web y redes sociales entran directo como leads, sin que nadie tenga que digitarlos a mano."

## 16. Contratos, pagos y visitas
"Los contratos de venta y arriendo tienen su propio ciclo de vida completo, con encadenamiento de renovaciones. Cada pago que se registra actualiza el saldo del contrato automáticamente y puede generar su factura, conservando la trazabilidad de la comisión del asesor. Y las visitas quedaron integradas al calendario: cada cita envía sola un recordatorio por WhatsApp una hora antes, y después de la visita se dispara una encuesta de satisfacción."

## 17. Reportes y sitio web
"La gerencia ahora tiene un tablero de indicadores con sus metas de cierres, ingresos y comisiones, y el porcentaje de cumplimiento de cada una — exportable a PDF o Excel con un clic. Y la sincronización con WordPress quedó automática: cuando se publica o modifica una propiedad en el sistema, la entrada del sitio web se actualiza sola, y cuando se vende, se retira sola de la publicación."

## 18. Modelo de datos
"Este es el modelo entidad-relación del sistema. Las entidades núcleo son la propiedad, el lead del CRM, el contrato, el pago y la comisión, todas relacionadas entre sí. Y para no repetir código, varios comportamientos comunes —como el registro de auditoría o el manejo de teléfonos— se implementaron como mixins reutilizables entre modelos."

## 19. OE3 — El agente inteligente
"El tercer objetivo, y el componente diferenciador de este trabajo, es el agente inteligente. Es un asistente conversacional integrado directamente en el ERP, disponible como chat flotante en toda la aplicación. Funciona con Google Gemini o con OpenAI, configurable, y si el proveedor activo falla, reintenta automáticamente con el proveedor de respaldo. Lo importante es que no es un chatbot de respuestas fijas: dispone de más de cincuenta herramientas reales que le permiten consultar la base de datos, crear y actualizar registros, agendar visitas, generar reportes en PDF o Excel, y hasta analizar imágenes de propiedades."

## 20. Cómo razona el agente
"Internamente el agente combina varias técnicas. Usa RAG, generación aumentada por recuperación: los manuales del sistema se dividieron en fragmentos indexados, así que cuando alguien pregunta 'cómo se hace tal cosa', el agente responde citando la documentación real, no inventando procedimientos. Tiene memoria persistente, así que recuerda preferencias de un cliente entre conversaciones distintas. Y tiene alertas proactivas: revisa el negocio todos los días y avisa por iniciativa propia, por ejemplo cuando un cliente muy interesado lleva varios días sin respuesta. [Si el tiempo lo permite, aquí es el mejor momento para una demo en vivo de 30-40 segundos]"

## 21. OE4 — Integración y despliegue en producción
"Para el cuarto objetivo se integraron técnicamente todos los componentes y se validó la interoperabilidad completa antes de pasar a producción real. El despliegue final usa Docker sobre un servidor Ubuntu: PostgreSQL, el servidor Odoo, y Nginx como proxy con SSL y renovación automática de certificados. Ya en operación se hicieron ajustes de rendimiento —índices en la base de datos, respaldos automáticos diarios— y se reforzó la tolerancia a fallos: si el proveedor de IA activo no responde, el sistema reintenta con el de respaldo sin que el usuario note nada."

## 22. OE5 — Comparativa antes/después
"El quinto objetivo fue evaluar las mejoras. Esta tabla resume el contraste: antes, el registro de propiedades eran hojas de cálculo con duplicados; ahora es una ficha única sin duplicados posibles. Antes, los recordatorios de citas dependían de la memoria del asesor; ahora son automáticos por WhatsApp. Antes, los reportes se armaban a mano con errores; ahora hay un tablero en tiempo real. Y en conjunto, el sistema quedó operando con dieciocho tareas programadas que reemplazan trabajo que antes era manual o simplemente no se hacía — voy a detallar algunas de las más importantes si el tribunal quiere profundizar."

*(Ver más abajo la sección "Anexo: las tareas automáticas del sistema" con el detalle completo para responder preguntas.)*

## 23. Validación y pruebas
"Para respaldar que todo esto realmente funciona como digo, se construyó una batería de 167 pruebas automatizadas con el framework de pruebas de Odoo, todas superadas. Estas pruebas verifican las reglas críticas del negocio: que los estados de propiedades y contratos no se salten pasos inválidos, que las comisiones se calculen correctamente, que la puntuación de leads sea la que corresponde, y que la seguridad por roles funcione. Esto no es 'funciona en mi máquina' — es evidencia objetiva y repetible."

## 24. Cumplimiento de objetivos
"Con todo lo mostrado, los cinco objetivos específicos quedan cumplidos: requisitos documentados con trazabilidad, doce módulos operativos, el agente de IA funcionando con lenguaje natural, el sistema desplegado en producción con HTTPS, y las mejoras verificadas con los propios usuarios de Inmobi."

## 25. Cronograma y presupuesto
"El proyecto se ejecutó del 4 de mayo al 20 de julio de 2026, con 240 horas planificadas distribuidas en los cinco objetivos. El presupuesto total fue de 4830 dólares, entre equipo, servidor y consumo de las APIs de inteligencia artificial."

## 26. Conclusiones
"En conclusión: el levantamiento de requisitos tradujo las falencias reales de Inmobi en requisitos verificables; la arquitectura modular de Odoo permitió construir una solución a medida sin depender de software comercial costoso; el agente inteligente convierte al ERP en un asistente operativo real, no solo un buscador; y las dieciocho automatizaciones más las 167 pruebas superadas son evidencia objetiva de que el sistema resuelve las causas reales del problema, no solo los síntomas."

## 27. Recomendaciones
"Como recomendaciones dejo: monitorear el despliegue con respaldos y certificados actualizados; ejecutar una evaluación formal de KPIs antes/después con más tiempo de uso real; capacitar al personal apoyándose en el manual de usuario; gobernar el costo de las APIs de IA; y, a futuro, incorporar firma electrónica avanzada en los contratos y ampliar el catálogo de acciones proactivas del agente."

## 28. Cierre
"Con esto termino la presentación. Muchas gracias por su atención, quedo atento a sus preguntas."

---

# Anexo: las tareas automáticas del sistema (para preguntas del tribunal)

**Aviso importante antes de la defensa:** el informe escrito dice "dieciocho tareas programadas". Al revisar el código actual, hay **22 tareas (crons) activas** — 4 más de las que menciona el informe, porque se siguieron agregando mejoras después de escribir esa sección. Tienes dos opciones honestas si te preguntan por el número exacto:
1. Decir: *"El informe documenta 18; en el desarrollo posterior se agregaron 4 más (estadísticas de Instagram, importación de clientes por Excel, sincronización de WordPress y de Google Calendar), llegando a 22 activas hoy."* — Es la respuesta más transparente y demuestra que el sistema sigue evolucionando.
2. Si prefieres no abrir ese tema, simplemente habla de "varias" o "más de 15" en la diapositiva, sin comprometerte a un número exacto.

**No hace falta que memorices las 22** — con explicar 4-5 ejemplos claros en la diapositiva 22 es suficiente. Esta lista completa es para que la tengas a mano SOLO si el tribunal pregunta "¿cuáles son?" o "¿cómo funciona tal automatización?".

### Gestión de propiedades y contratos (estate_management)
1. **Aviso de vencimiento de documentos** (1×día) — revisa documentos con fecha de vencimiento a menos de 30 días (configurable), crea una actividad al responsable y marca el documento como notificado para no repetir el aviso.
2. **Alertas inteligentes de precio** (1×semana) — busca propiedades disponibles que el AVM marcó como sobrevaloradas y que llevan 45+ días en el mercado; crea una actividad sugiriendo revisar el precio, comparando el actual contra el estimado por el modelo.
3. **Alertas de pagos vencidos** (1×día) — detecta pagos pendientes con fecha ya pasada; crea actividad al responsable, y si el atraso es de 3 días o más, además envía un WhatsApp.
4. **Verificación de vencimiento de contratos** (1×día) — avisa por actividad y WhatsApp cuando a un contrato le quedan pocos días (configurable por propiedad) o ya venció, evitando duplicar el aviso.
5. **Alerta de propiedades estancadas** (cada 3 días) — detecta propiedades disponibles hace 45+ días sin ninguna visita realizada en ese lapso, y sugiere al asesor revisar precio, fotos o hacer campaña.
6. **Generación de facturas mensuales de arriendo** (1×mes) — para cada contrato de arriendo activo, genera automáticamente la factura del mes si todavía no existe una para ese periodo.
7. **Sincronización de estado desde facturas pagadas** (1×día) — si una factura de venta vinculada a una propiedad reservada se marca como pagada, la propiedad pasa sola a "vendida".

### CRM y leads (estate_crm)
8. **Matchmaking automático de leads y propiedades** (1×día) — cruza leads sin ganar que tienen presupuesto contra propiedades disponibles cuyo precio esté entre 70% y 105% de ese presupuesto (y opcionalmente misma ciudad); crea una actividad de oportunidad para el asesor.
9. **Enfriar leads sin actividad** (1×día) — si un lead caliente o hirviendo lleva 14+ días sin ninguna actividad, baja un escalón su temperatura automáticamente (hirviendo→caliente, caliente→tibio) y lo anota en el historial.
10. **Seguimiento drip automático** (1×día) — a los 2, 7 y 14 días exactos de creado un lead, crea una actividad de llamada con un guion distinto para cada hito (confirmar interés, explorar objeciones, último intento de recuperación).
11. **Alerta de lead hirviendo sin respuesta** (cada 6 horas) — si un lead en temperatura "hirviendo" lleva más de 48 horas sin ninguna interacción registrada, crea una actividad urgente para el asesor.
12. **Notificación a referidores** (1×día) — cuando un lead con un referidor asignado se gana, publica un aviso y crea una actividad para reconocer/entregar el beneficio del programa de referidos.
13. **Búsqueda de propiedades para necesidad pendiente** (cada 6 horas) — para clientes marcados con "necesidad pendiente", calcula un puntaje de compatibilidad (presupuesto, tipo, ciudad, habitaciones) contra las propiedades disponibles; si supera 60/100, le asigna la propiedad de interés, avisa por WhatsApp al cliente y crea actividad al asesor.
14. **Procesamiento de importaciones de clientes desde Excel** (cada 30 min, red de seguridad) — procesa en segundo plano hasta 5 archivos Excel pendientes de importar (formato Wasi), creando los contactos y leads correspondientes; normalmente se dispara al instante al presionar "Importar", el cron solo cubre los que quedaran en cola.

### Calendario y comunicación (estate_calendar / estate_gcal)
15. **Recordatorios de citas por WhatsApp** (cada 30 min, ajustado a 5 min en producción) — calcula la anticipación efectiva de cada cita (la de la cita, la del asesor, o la general) y envía WhatsApp al asesor y opcionalmente al cliente cuando toca avisar.
16. **Sincronización con Google Calendar** (cada 5 min) — revisa cambios hechos directamente en Google Calendar (cancelaciones o reprogramaciones) y los refleja en el sistema: si se cancela allá, marca la visita como cancelada aquí (sin borrarla); si cambia el horario, actualiza la fecha localmente.

### Reportes, redes sociales y sitio web
17. **Reporte mensual por email** (1×mes) — calcula KPIs del mes anterior (ventas, leads, visitas), los compara contra el mes previo, arma un ranking de asesores y alertas críticas, y envía el reporte por correo a gerencia/administración.
18. **Importación de publicaciones de Facebook** (1×hora) — trae las publicaciones recientes de la página de Facebook vía su API y las guarda/actualiza en el sistema.
19. **Actualización de estadísticas de Facebook** (1×día) — para cada publicación ya importada, refresca reacciones, comentarios y compartidos desde la API.
20. **Actualización de estadísticas de Instagram** (1×día) — igual que el anterior pero para publicaciones de Instagram vinculadas a propiedades publicadas.
21. **Re-sincronización con WordPress** (cada 2 horas, si está activado en Ajustes) — republica en el sitio web las propiedades que tuvieron cambios pendientes de sincronizar, hasta 20 por corrida.

### Agente de IA
22. **Alertas proactivas diarias del agente** (1×día) — revisa pagos vencidos, propiedades estancadas (90+ días), contratos por vencer (30 días), leads calientes sin respuesta (7+ días), leads nuevos de las últimas 24h y visitas del día; envía un resumen como notificación a gerentes/administradores.

---

# Anexo: respuesta de respaldo — "Portal del Propietario" (`estate_portal`)

Este módulo **no se menciona** en el guion, las diapositivas ni el manual de usuario — no formó parte del alcance original de la tesis (no estaba planteado desde el inicio) y solo aparece de forma incidental como una cajita en la Figura 1 del informe (diagrama de organización modular), sin tabla, sección ni desarrollo propio en el texto. Se deja fuera deliberadamente.

**Si el tribunal pregunta por esa cajita del diagrama**, la respuesta preparada es:

> "Ese módulo aprovecha el sistema de acceso a portal que ya trae Odoo de fábrica, y sobre esa base construimos una extranet sencilla para que el propietario vea sus propiedades y contratos. No fue parte de los cinco objetivos específicos del proyecto, así que quedó como un extra que no se profundizó ni se incluyó en el alcance formal."

Es una respuesta corta, no inventa nada y explica por qué no está en el informe sin que suene a que se olvidó algo importante.

---

# Herramientas de IA para armar las diapositivas

Con el contenido de `PRESENTACION_DIAPOSITIVAS.md` ya armado, estas son buenas opciones para convertirlo en un diseño visual real:

1. **Gamma (gamma.app) — la más recomendada para este caso.** Le pegas el contenido en markdown (o incluso el outline tal como está) y genera automáticamente un diseño de diapositivas completo, con imágenes, iconos y layout — después puedes editar cada diapositiva individualmente. Es la herramienta más orientada específicamente a "texto/outline → presentación lista", que es exactamente tu caso.
2. **Canva (con Magic Design / IA)** — si prefieres más control visual manual con plantillas universitarias/formales, y luego usar su asistente de IA para ajustar textos o generar variantes de diseño.
3. **Tome (tome.app)** — alternativa similar a Gamma, buena para presentaciones más narrativas.
4. **Google Slides + extensión "SlidesAI"** — si ya usas Google Workspace y quieres quedarte en ese ecosistema, esta extensión convierte texto/outline en slides directamente en Google Slides.

Mi recomendación concreta: pega el contenido de `PRESENTACION_DIAPOSITIVAS.md` en **Gamma**, genera el borrador, y luego ajusta manualmente los slides 19-20 (agente de IA) y 22 (comparativa) ya que son los que más impacto visual necesitan (capturas reales del chat y de la tabla comparativa).
