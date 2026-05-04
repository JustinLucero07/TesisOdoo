# Guia Completa del Agente Inteligente (IA)

El agente IA es un asistente conversacional integrado directamente en Odoo que puede consultar, crear, modificar y analizar datos del sistema inmobiliario usando lenguaje natural.

---

## Como acceder al agente

- Desde cualquier pantalla de Odoo: clic en el icono de chat flotante (esquina inferior derecha)
- Escribe tu consulta en lenguaje natural y el agente ejecuta las acciones automáticamente

---

## Capacidades completas

### 1. Consultas y busquedas

| Que puedes preguntar | Ejemplo |
|---|---|
| Buscar propiedades por filtros | "Muestrame casas disponibles en Cuenca menores a $200,000" |
| Detalle completo de una propiedad | "Dame toda la info de la propiedad P00005" |
| Buscar contactos/clientes | "Busca al cliente Maria Lopez" |
| Ver leads del CRM | "Muestrame los leads calientes" |
| Estadisticas del mercado | "Cual es el precio promedio de departamentos en Cuenca?" |
| Comparar propiedades | "Compara las propiedades 3, 5 y 8" |
| Resumen 360 de un cliente | "Dame el perfil completo de Juan Perez" |
| Proximas visitas | "Que visitas tengo esta semana?" |
| Pagos y contratos pendientes | "Hay pagos vencidos?" |

**Ejemplos de preguntas:**
```
- "Cuantas propiedades disponibles tengo?"
- "Muestrame terrenos en Azogues"
- "Que propiedades llevan mas de 90 dias en el mercado?"
- "Cuales son los leads mas calientes?"
- "Muestrame los contratos que vencen este mes"
- "Que leads nuevos ingresaron hoy?"
```

---

### 2. Crear registros

| Accion | Ejemplo |
|---|---|
| Crear un lead | "Crea un lead: Maria Gomez busca casa en Cuenca, presupuesto $150,000, su telefono es 0991234567" |
| Crear una propiedad | "Registra una casa en El Vergel, Cuenca, 180m2, 3 habitaciones, 2 banos, precio $165,000" |
| Crear un contrato | "Crea un contrato de arriendo para la propiedad 5 con Pedro Arias por $800 mensuales" |
| Registrar un pago | "Registra un pago de $800 al contrato 3, metodo transferencia" |
| Crear una oferta | "Registra una oferta de $140,000 de Ana Torres por la propiedad 7" |
| Registrar comision | "Registra comision de $3,500 para el asesor Carlos Mendez por la propiedad 12" |
| Agendar visita | "Agenda visita a la propiedad 4 con Maria Lopez manana a las 10:00" |
| Crear actividad CRM | "Crea una actividad de seguimiento en el lead 15: llamar al cliente" |

**Ejemplos:**
```
- "Ingresa nuevo lead: Roberto Cardenas, email roberto@mail.com, busca departamento, presupuesto $80,000"
- "Registra propiedad: Departamento Centro Historico, Cuenca, 95m2, 2 hab, 1 bano, $95,000 venta"
- "Agenda visita para la propiedad 8 con el cliente del lead 12, el viernes a las 15:00"
```

---

### 3. Modificar registros

| Accion | Ejemplo |
|---|---|
| Actualizar propiedad | "Cambia el precio de la propiedad 5 a $175,000" |
| Actualizar lead | "Mueve el lead 8 a etapa Negociacion y temperatura caliente" |
| Reservar propiedad | "Reserva la propiedad 3 para Juan Perez" |
| Vender/alquilar | "Marca la propiedad 7 como vendida a $160,000" |
| Aprobar pago | "Aprueba el pago 14" |
| Aprobar comision | "Aprueba la comision 5" |
| Activar/cancelar contrato | "Activa el contrato 8" |

**Ejemplos:**
```
- "Actualiza la propiedad 12: 4 habitaciones, area 220m2, precio $195,000"
- "Cambia la descripcion de la propiedad 3 a: Hermosa casa con vista al rio"
- "Asigna la propiedad 5 al lead 10"
- "Sube el precio de la propiedad 6 a $200,000"
- "Cambia el estado del lead 4 a 'boiling'"
```

---

### 4. Eliminar y archivar

| Accion | Ejemplo |
|---|---|
| Eliminar propiedad | "Elimina la propiedad 15" (pedira confirmacion) |
| Archivar propiedad | "Archiva la propiedad 9, motivo: vendida fuera del sistema" |
| Archivar lead | "Archiva el lead 5, razon: cliente no responde" |
| Cancelar pago | "Cancela el pago 7, fue registrado por error" |

> Las acciones destructivas siempre piden confirmacion antes de ejecutarse.

---

### 5. Operaciones en lote (masivas)

| Accion | Ejemplo |
|---|---|
| Ajustar precios | "Baja un 5% todas las propiedades en Azogues" |
| Archivar leads frios | "Archiva todos los leads frios sin actividad en 30 dias" |
| Cambiar estado masivo | "Cambia a reservado todas las propiedades disponibles en Cuenca" |

**Ejemplos:**
```
- "Sube un 10% el precio de todas las propiedades disponibles en El Vergel"
- "Archiva leads con temperatura fria que no han tenido actividad en 60 dias"
```

---

### 6. Reportes y graficos

| Que pedir | Ejemplo |
|---|---|
| Propiedades por estado | "Dame un grafico de propiedades por estado" |
| Propiedades por tipo | "Reporte de propiedades por tipo" |
| Ventas por mes | "Muestrame las ventas por mes" |
| Visitas por propiedad | "Cuales propiedades tienen mas visitas?" |
| Comisiones por asesor | "Reporte de comisiones por asesor" |
| Contratos por tipo | "Grafico de contratos por tipo" |
| Leads por temperatura | "Muestrame los leads por temperatura" |
| Pagos por metodo | "Reporte de pagos por metodo de pago" |
| Dias en mercado | "Cuantos dias en promedio llevan las propiedades por tipo?" |
| Ofertas por estado | "Reporte de ofertas recibidas" |
| Tendencias | "Comparame las ventas de este mes vs el anterior" |
| Dashboard ejecutivo | "Dame un resumen ejecutivo del mes" |

**Ejemplos de reportes:**
```
- "Genera un reporte de ventas por mes"
- "Muestrame un grafico de leads por temperatura"
- "Cual es la tendencia de ingresos este trimestre vs el anterior?"
- "Dame el dashboard completo de hoy"
- "Cuantas visitas se hicieron esta semana por propiedad?"
```

---

### 7. Generacion de documentos PDF

| Documento | Ejemplo |
|---|---|
| Ficha de propiedad | "Genera el PDF de la propiedad 5" |
| Estado de cuenta de contrato | "Dame el estado de cuenta del contrato 3" |
| Cotizacion para lead | "Genera una cotizacion para el lead 8" |

**Ejemplos:**
```
- "Genera la ficha PDF de la propiedad 12"
- "Dame el PDF del estado de cuenta del contrato 7"
- "Genera cotizacion para el lead 15 con la propiedad 4"
```

---

### 8. Inteligencia artificial avanzada

| Capacidad | Ejemplo |
|---|---|
| Analisis de probabilidad de cierre | "Analiza la probabilidad del lead 5" |
| Riesgo de no renovacion (churn) | "Que contratos tienen riesgo de no renovar?" |
| Valoracion AVM con IA | "Recalcula el valor de mercado de la propiedad 8" |
| Generar descripcion marketing | "Genera descripcion de marketing para la propiedad 3" |
| Analisis de imagen (Vision) | Boton "Analizar Imagen IA" en ficha de propiedad |
| Redaccion de contratos | Boton "Generar Contrato IA" en ficha del contrato |

**Ejemplos:**
```
- "Que probabilidad tiene de cerrar el lead 12?"
- "Hay contratos en riesgo de no renovarse?"
- "Cuanto deberia costar la propiedad 5 segun el mercado?"
- "Genera una descripcion comercial emocional para la propiedad 7 y publicala en WordPress"
```

---

### 9. Comunicacion

| Accion | Ejemplo |
|---|---|
| Enviar email | "Envia un email a Maria Lopez con asunto 'Su propiedad' y dile que ya tenemos interesados" |
| WhatsApp a lead | "Genera link de WhatsApp para el lead 8 con mensaje: Hola, tenemos una propiedad ideal para usted" |

---

### 10. Memoria persistente

El agente recuerda cosas entre conversaciones:

| Accion | Ejemplo |
|---|---|
| Guardar dato | "Recuerda que el cliente Perez prefiere zona norte" |
| Guardar alerta | "Recuerdame que el contrato 5 necesita revision el 15 de mayo" |
| Consultar memoria | "Que sabes sobre el cliente Perez?" |

**Ejemplos:**
```
- "Recuerda que yo prefiero ver precios en formato corto"
- "Recuerda que el sector Misicata esta en alta demanda"
- "Que recuerdas sobre mis preferencias?"
```

---

### 11. Agente proactivo (automatico)

El sistema ejecuta un analisis diario automatico (cron) que notifica a los gerentes sobre:

- Pagos vencidos
- Propiedades estancadas (+90 dias)
- Contratos por vencer (30 dias)
- Leads calientes sin actividad (+7 dias)
- Nuevos leads (ultimas 24h)
- Visitas del dia

> Se ejecuta automaticamente cada dia. No necesitas pedirlo.

---

## Funciones desde botones (sin chat)

Estas funciones se ejecutan desde botones directos en las fichas, sin necesidad del chat:

| Boton | Donde | Que hace |
|---|---|---|
| Analizar Imagen IA | Ficha de propiedad | Analiza la foto con Vision AI: detecta condicion, problemas, sugiere staging |
| Generar Descripcion IA | Ficha de propiedad | Crea 3 versiones de descripcion (formal/emocional/directa) + titulares |
| Generar Contrato IA | Ficha del contrato | Redacta borrador legal completo del contrato en HTML |

---

## Tips para mejores resultados

1. **Se especifico**: "Muestrame casas en Cuenca menores a $200,000 con al menos 3 habitaciones" es mejor que "muestrame casas"
2. **Usa IDs cuando puedas**: "Actualiza la propiedad 5" es mas preciso que "actualiza la propiedad del vergel"
3. **Combina acciones**: "Crea un lead para Ana Torres, presupuesto $120,000, busca departamento en Cuenca, y agenda una visita a la propiedad 3 para el viernes a las 10:00"
4. **Pide reportes contextuales**: "Como van las ventas este mes comparado con el anterior?"
5. **Usa memoria**: "Recuerda que este cliente solo quiere primer piso" — lo recordara en futuras conversaciones

---

## Configuracion del agente

**Ajustes → Inmobiliaria → Agente IA:**

| Campo | Valor recomendado |
|---|---|
| Proveedor | Google Gemini |
| API Key | Tu key de Google AI Studio |
| Modelo | `gemini-2.0-flash` (rapido y gratuito) |
| Temperatura | 0.7 (balance creatividad/precision) |
| Max Tokens | 1000 |
| Agente Activo | Activado |

### Obtener API Key de Gemini (gratis)

1. Ir a [aistudio.google.com](https://aistudio.google.com)
2. Clic en **Get API Key** → **Create API Key**
3. Copiar la key y pegarla en Ajustes

> Gemini Flash tiene **1,500 peticiones/dia gratis** — mas que suficiente para uso diario.

---

## Resumen de todas las herramientas (37 total)

| # | Herramienta | Categoria |
|---|---|---|
| 1 | search_properties | Consulta |
| 2 | get_property_detail | Consulta |
| 3 | get_leads | Consulta |
| 4 | get_market_stats | Consulta |
| 5 | get_payments_contracts | Consulta |
| 6 | get_dashboard_summary | Consulta |
| 7 | get_report_data | Reportes |
| 8 | get_trend_analysis | Reportes |
| 9 | get_upcoming_visits | Consulta |
| 10 | get_client_summary | Consulta |
| 11 | search_contacts | Consulta |
| 12 | compare_properties | Consulta |
| 13 | create_lead | Crear |
| 14 | create_property | Crear |
| 15 | create_contract | Crear |
| 16 | create_payment | Crear |
| 17 | create_offer | Crear |
| 18 | create_commission | Crear |
| 19 | create_crm_activity | Crear |
| 20 | schedule_visit | Crear |
| 21 | update_lead | Modificar |
| 22 | update_property | Modificar |
| 23 | update_contract | Modificar |
| 24 | approve_payment | Modificar |
| 25 | approve_commission | Modificar |
| 26 | reserve_property | Modificar |
| 27 | sell_property | Modificar |
| 28 | delete_property | Eliminar |
| 29 | archive_property | Archivar |
| 30 | archive_lead | Archivar |
| 31 | cancel_payment | Cancelar |
| 32 | duplicate_property | Crear |
| 33 | batch_update_properties | Lote |
| 34 | batch_archive_leads | Lote |
| 35 | send_email | Comunicacion |
| 36 | send_whatsapp_lead | Comunicacion |
| 37 | generate_pdf_report | PDF |
| 38 | generate_quote_pdf | PDF |
| 39 | analyze_lead_probability | IA Avanzada |
| 40 | analyze_churn_risk | IA Avanzada |
| 41 | recalculate_avm_ai | IA Avanzada |
| 42 | generate_and_apply_description | IA Avanzada |
| 43 | save_memory | Memoria |
| 44 | recall_memory | Memoria |
