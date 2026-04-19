# Guia del Agente IA Inmobiliario — Inmobi

## Como acceder

Dentro de Odoo, el agente IA aparece como un icono flotante (chat) en la esquina inferior derecha. Tambien se puede acceder via:
- **Chat normal:** Endpoint `/estate_ai/chat` (widget flotante)
- **Chat streaming:** Endpoint `/estate_ai/chat/stream` (respuestas en tiempo real)
- **Briefing:** Endpoint `/estate_ai/briefing` (resumen del dia sin IA)

---

## Preguntas que puedes hacer y como responde

### 1. INVENTARIO Y PROPIEDADES

| Pregunta | Que hace el agente |
|----------|-------------------|
| "Cuantas propiedades tenemos disponibles?" | Consulta el inventario y muestra un resumen con totales por estado |
| "Busca casas en Cuenca con precio hasta $150,000" | Usa `search_properties` con filtros de ciudad, tipo y precio maximo |
| "Muestrame el detalle de la propiedad #5" | Usa `get_property_detail` y muestra todos los campos: precio, area, AVM, asesor, etc |
| "Compara la propiedad #3 con la #7" | Usa `compare_properties` y genera tabla comparativa lado a lado |
| "Cuales propiedades llevan mas de 60 dias sin vender?" | Busca por `days_on_market` y sugiere acciones |
| "Crea una propiedad: casa en Cuenca, $120,000, 3 habitaciones" | Usa `create_property` y confirma con el ID creado |
| "Cambia el precio de la propiedad #5 a $95,000" | Usa `update_property` con el nuevo precio |
| "Duplica la propiedad #3 con nuevo titulo" | Usa `duplicate_property` y crea un borrador |
| "Genera una descripcion de marketing para la propiedad #5" | Usa `generate_and_apply_description` con estilo formal/emocional |
| "Recalcula el valor AVM de la propiedad #10" | Usa `recalculate_avm_ai` y compara con el precio listado |
| "Reserva la propiedad #5 para Juan Perez" | Pide confirmacion y luego usa `reserve_property` |
| "Marca la propiedad #5 como vendida" | Pide confirmacion (accion destructiva) y usa `sell_property` |
| "Archiva la propiedad #8" | Pide confirmacion y usa `archive_property` |
| "Baja el precio un 5% a todas las propiedades en Ambato" | Usa `batch_update_properties` con ajuste porcentual |

### 2. CLIENTES Y CONTACTOS

| Pregunta | Que hace el agente |
|----------|-------------------|
| "Busca al cliente Maria Lopez" | Usa `search_contacts` por nombre y muestra leads/contratos vinculados |
| "Busca contactos con contratos activos" | Usa `search_contacts` con filtro `has_contracts=True` |
| "Dame el perfil completo del cliente Juan Perez" | Usa `get_client_summary` — leads, contratos, visitas, pagos pendientes |
| "Busca clientes interesados en casas en Cuenca" | Combina `search_contacts` + `get_leads` con filtros relevantes |

### 3. CRM Y LEADS

| Pregunta | Que hace el agente |
|----------|-------------------|
| "Cuales son los leads mas calientes?" | Usa `get_leads` con filtro `temperature=boiling` o `hot` |
| "Crea un lead para Pedro Garcia, busca casa en Cuenca, presupuesto $80,000" | Usa `create_lead` con todos los datos |
| "Sube la temperatura del lead #3 a 'hot'" | Usa `update_lead` con `temperature=hot` |
| "Asigna la propiedad #5 al lead #3" | Usa `update_lead` con `property_id=5` |
| "Crea una actividad de seguimiento en el lead #7" | Usa `create_crm_activity` con nota detallada |
| "Archiva los leads frios sin actividad en 30 dias" | Pide confirmacion y usa `batch_archive_leads` |
| "Analiza la probabilidad de cierre del lead #4" | Usa `analyze_lead_probability` — compara con historico |
| "Genera un link de WhatsApp para el lead #3" | Usa `send_whatsapp_lead` con mensaje personalizado |
| "Envia un email al cliente del lead #5" | Usa `send_email` con asunto y cuerpo |
| "Genera la cotizacion PDF del lead #3" | Usa `generate_quote_pdf` y devuelve link de descarga |

### 4. CONTRATOS Y PAGOS

| Pregunta | Que hace el agente |
|----------|-------------------|
| "Cuantos pagos vencidos hay?" | Usa `get_payments_contracts` y muestra tabla de vencidos |
| "Crea un contrato de venta para la propiedad #5 con Juan Perez por $120,000" | Usa `create_contract` |
| "Activa el contrato #12" | Usa `update_contract` con `action=activate` |
| "Registra un pago de $5,000 al contrato #12 por transferencia" | Usa `create_payment` |
| "Aprueba el pago #8" | Usa `approve_payment` |
| "Cancela el pago #8" | Pide confirmacion y usa `cancel_payment` |
| "Crea una oferta de $110,000 para la propiedad #5 de Maria Lopez" | Usa `create_offer` |
| "Registra una comision de $3,600 para el asesor Carlos" | Usa `create_commission` |
| "Aprueba la comision #15" | Usa `approve_commission` |
| "Analiza riesgo de churn en contratos proximos a vencer" | Usa `analyze_churn_risk` con prediccion |

### 5. CALENDARIO Y VISITAS

| Pregunta | Que hace el agente |
|----------|-------------------|
| "Cuales son mis visitas de esta semana?" | Usa `get_upcoming_visits` con `days_ahead=7` |
| "Visitas de hoy" | Usa `get_upcoming_visits` con `days_ahead=1` |
| "Agenda una visita a la propiedad #5 para Maria Lopez manana a las 10:00" | Usa `schedule_visit` |
| "Visitas del asesor Carlos esta semana" | Usa `get_upcoming_visits` con `advisor_name=Carlos` |

### 6. REPORTES Y ESTADISTICAS

| Pregunta | Que hace el agente |
|----------|-------------------|
| "Dame el briefing del dia" | Combina inventario + visitas de hoy + alertas + tendencias |
| "Como vamos este mes vs el mes pasado?" | Usa `get_trend_analysis` con comparativa de ventas, leads, ingresos |
| "Reporte de propiedades por estado" | Usa `get_report_data` con `properties_by_state` + tabla + grafico |
| "Grafico de leads por temperatura" | Usa `get_report_data` con `leads_by_temperature` + grafico de barra |
| "Reporte de comisiones por asesor" | Usa `get_report_data` con `commissions_by_advisor` |
| "Estadisticas del mercado en Cuenca" | Usa `get_market_stats` con filtro de ciudad |
| "Resumen ejecutivo del mes" | Usa `get_dashboard_summary` con metricas completas |
| "Genera el PDF de la ficha tecnica de la propiedad #5" | Usa `generate_pdf_report` con tipo `ficha_propiedad` |
| "Genera el estado de cuenta del contrato #12" | Usa `generate_pdf_report` con tipo `estado_cuenta_contrato` |
| "Ventas por mes" | Usa `get_report_data` con `sales_by_month` + grafico de barra |
| "Dias promedio en mercado por tipo de propiedad" | Usa `get_report_data` con `days_on_market_by_type` |
| "Gastos por tipo" | Usa `get_report_data` con `expenses_by_type` + grafico circular |
| "Ofertas por estado" | Usa `get_report_data` con `offers_by_state` |
| "Pagos por metodo" | Usa `get_report_data` con `payments_by_method` |

### 7. IA AVANZADA Y NEGOCIACION

| Pregunta | Que hace el agente |
|----------|-------------------|
| "El cliente ofrece $95,000 por la propiedad #5 que esta en $120,000, que hago?" | Consulta AVM, analiza diferencia y da 3 puntos de negociacion |
| "Recuerda que prefiero respuestas cortas" | Usa `save_memory` para guardar la preferencia |
| "Que memorias tienes guardadas?" | Usa `recall_memory` para listar hechos/preferencias |

### 8. OPERACIONES MASIVAS

| Pregunta | Que hace el agente |
|----------|-------------------|
| "Baja un 10% todas las propiedades disponibles en Ambato" | Pide confirmacion y usa `batch_update_properties` |
| "Archiva todos los leads frios sin actividad en 60 dias" | Pide confirmacion y usa `batch_archive_leads` |

---

## Tipos de respuesta

### Tablas
Cuando el resultado tiene multiples registros, el agente responde con tablas Markdown:

```
| ID | Propiedad | Ciudad | Precio | Estado |
|----|-----------|--------|--------|--------|
| 1  | Casa Sol  | Cuenca | $95,000 | Disponible |
```

### Graficos
Para reportes con datos numericos, el agente genera un grafico embebido:
```
[GRAFICO:barra,Disponibles:12,Vendidas:5,Alquiladas:3]
```
El frontend lo renderiza como un grafico Chart.js.

### Confirmacion de acciones
Para acciones que modifican datos:
```
Propiedad #5 creada correctamente (Ref: PROP-0005) - Casa en Cuenca, $120,000
```

### Confirmacion requerida (acciones destructivas)
```
CONFIRMACION REQUERIDA: Estas a punto de archivar 15 leads frios. Confirmas? (responde 'si confirmo')
```

### PDFs
```
Ficha tecnica generada: [Descargar PDF](http://localhost:8070/report/pdf/...)
```

---

## Comandos especiales

| Comando | Descripcion |
|---------|-------------|
| `/briefing` | Resumen matutino: inventario, visitas del dia, alertas, tendencias |
| "recuerda que..." | Guarda una preferencia/hecho para futuras conversaciones |
| "olvida que..." | Consulta y elimina memorias guardadas |

---

## Alertas proactivas

El agente incluye alertas al inicio de la conversacion si detecta:
- Pagos vencidos pendientes
- Leads calientes sin actividad en 7+ dias
- Contratos proximos a vencer (30 dias)
- Propiedades estancadas (90+ dias sin vender)

---

## Configuracion

**Ajustes > Agente IA:**
- Proveedor: Gemini o OpenAI
- API Key
- Modelo (gemini-2.0-flash recomendado)
- Temperatura (0.7 por defecto)
- Prompt del sistema personalizable
