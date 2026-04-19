# Guía de Comandos del Agente IA Inmobiliario

Este documento describe todo lo que puedes pedirle al Agente IA desde el chat.
Accede en: **Inteligencia IA → Chat IA**

---

## CONSULTAS (preguntas de solo lectura)

### Propiedades

| Lo que dices | Qué hace el agente |
|---|---|
| `¿Cuántas propiedades disponibles hay?` | Lista todas las propiedades con estado "disponible" |
| `Busca casas en Cuenca con precio hasta $150,000` | Filtra por ciudad, tipo y precio |
| `Muéstrame departamentos disponibles en Quito` | Filtra por tipo y ciudad |
| `¿Cuántos días lleva sin venderse la propiedad #5?` | Muestra días en mercado |
| `¿Cuál es el precio AVM de la casa en Av. Solano?` | Muestra valoración automática |

### Leads y CRM

| Lo que dices | Qué hace el agente |
|---|---|
| `¿Cuáles son los leads más calientes?` | Lista leads con temperatura "hot" o "boiling" |
| `Muéstrame los prospectos con score A` | Filtra por puntuación alta |
| `¿Quiénes son los leads sin actividad esta semana?` | Detecta leads estancados |
| `Dame el resumen del lead de Juan Pérez` | Muestra datos completos del lead |
| `¿Cuántos leads vinieron de Instagram este mes?` | Estadística por fuente |

### Contratos y Pagos

| Lo que dices | Qué hace el agente |
|---|---|
| `¿Hay contratos que vencen pronto?` | Lista contratos por vencer en 30 días |
| `¿Cuánto hay pendiente de cobro?` | Total de pagos en estado pendiente |
| `Lista los pagos vencidos de esta semana` | Pagos atrasados con días de mora |
| `¿Cuál es el ingreso total de comisiones este mes?` | Suma de comisiones pagadas |

### Estadísticas y Reportes

| Lo que dices | Qué hace el agente |
|---|---|
| `Dame estadísticas del mercado en Cuenca` | Precio promedio, días en mercado, ventas |
| `Muestra un gráfico de propiedades por estado` | Genera gráfico de barras o circular |
| `Reporte de ventas por mes` | Gráfico de línea con evolución mensual |
| `Comisiones por asesor` | Tabla y gráfico comparativo |
| `¿Cuántas visitas tuvo cada propiedad?` | Ranking de visitas |

---

## ACCIONES (el agente modifica datos)

### Crear registros

| Lo que dices | Qué hace el agente |
|---|---|
| `Crea un lead para María García, interesada en casa de $200,000 en Cuenca` | Crea oportunidad en CRM |
| `Registra una nueva propiedad: Casa en Av. España, 3 hab, $180,000` | Crea propiedad |
| `Crea un contrato de arriendo para la propiedad #7 con Juan López` | Crea contrato |
| `Registra un pago de $500 para el contrato #3` | Crea pago |
| `Crea una oferta de $145,000 para la propiedad #5` | Registra oferta |
| `Apunta una comisión de $3,000 para el asesor Pedro` | Crea comisión |
| `Agenda una actividad de seguimiento para el lead #12: llamar mañana` | Crea actividad en CRM |

### Actualizar registros

| Lo que dices | Qué hace el agente |
|---|---|
| `Actualiza el precio de la propiedad #4 a $175,000` | Cambia el precio |
| `Cambia el estado de la propiedad #8 a reservada` | Actualiza estado |
| `Mueve el lead de Carlos Ruiz a etapa Propuesta` | Cambia etapa en CRM |
| `Actualiza el presupuesto del lead #15 a $250,000` | Modifica campo del lead |
| `Sube la temperatura del lead #9 a caliente` | Cambia temperatura |

### Acciones de negocio

| Lo que dices | Qué hace el agente |
|---|---|
| `Reserva la propiedad #6 para el cliente Ana Torres` | Cambia estado a reservado |
| `Aprueba el pago #22` | Marca el pago como pagado |
| `Aprueba la comisión #5` | Marca comisión como pagada |
| `Envía un email a juan@mail.com sobre la propiedad #3` | Envía email con asunto y cuerpo |
| `Genera el PDF del contrato #7` | Crea PDF descargable |

### Operaciones masivas ⚠️

> Estas operaciones requieren que respondas **"sí confirmo"** antes de ejecutarse.

| Lo que dices | Qué hace el agente |
|---|---|
| `Archiva todos los leads fríos sin actividad en 60 días` | Archiva leads masivamente |
| `Actualiza el precio de todas las casas en Cuenca a -5%` | Ajuste masivo de precios |
| `Cancela el pago #18` | Cancela pago (pide confirmación) |

---

## ANÁLISIS CON IA

| Lo que dices | Qué hace el agente |
|---|---|
| `Analiza la probabilidad de cierre del lead #14` | Evalúa señales de compra y da % |
| `¿Cuál es el riesgo de churn del contrato #3?` | Analiza días por vencer, mora y alertas |
| `Recalcula el AVM de la propiedad #5` | Busca comparables y estima valor |
| `Genera una descripción atractiva para la propiedad #9` | Redacta descripción de marketing |

---

## MEMORIA PERSISTENTE (el agente te recuerda entre sesiones)

| Lo que dices | Qué hace el agente |
|---|---|
| `Recuerda que prefiero las propiedades en Cuenca sobre $100,000` | Guarda preferencia |
| `Anota que el cliente Pérez es muy exigente con la ubicación` | Guarda dato de cliente |
| `Crea una alerta: revisar contratos cada lunes` | Guarda alerta |
| `¿Qué recuerdas de mí?` | Lista tus memorias activas |
| `¿Qué sabes del cliente García?` | Busca memorias relacionadas |

Las memorias se gestionan en: **Inteligencia IA → Memorias del Agente**

---

## REPORTES Y GRÁFICOS

Cuando pides un reporte, el agente genera automáticamente una tabla Markdown + un gráfico visual.

### Tipos de gráfico disponibles

Después de ver un reporte, puedes pedir:
- `Muéstralo en circular` → Gráfico de torta
- `Muéstralo en barras` → Gráfico de barras
- `Muéstralo en línea` → Gráfico de línea temporal

### Reportes disponibles

| Comando | Tipo de gráfico |
|---|---|
| `Propiedades por estado` | Circular |
| `Propiedades por tipo` | Barras |
| `Ventas por mes` | Línea |
| `Visitas por propiedad` | Barras |
| `Comisiones por asesor` | Barras |
| `Contratos por tipo` | Circular |
| `Gastos por tipo` | Circular |
| `Ofertas por estado` | Barras |
| `Leads por temperatura` | Circular |
| `Pagos por método` | Circular |
| `Días en mercado por tipo` | Barras |

---

## OCR — ANÁLISIS DE DOCUMENTOS

Desde el botón **OCR** en el chat puedes subir:
- Fotos de escrituras, contratos, cédulas
- PDFs de facturas o documentos

El agente extrae automáticamente los datos y luego puedes decirle:
- `Registra esta propiedad con esos datos`
- `Crea el contrato con la información extraída`

---

## FLUJO DE CONFIRMACIÓN PARA ACCIONES DESTRUCTIVAS

Cuando el agente detecta una acción destructiva o irreversible, responde con:

```
⚠️ CONFIRMACIÓN REQUERIDA: Estás a punto de [acción].
¿Confirmas? (responde "sí confirmo")
```

Solo responde **"sí confirmo"** para ejecutar. Cualquier otra respuesta cancela la acción.

---

## ALERTAS PROACTIVAS DIARIAS

Cada mañana el agente analiza automáticamente:
- Pagos vencidos ≥ 3 días
- Propiedades sin vender ≥ 90 días
- Contratos que vencen en 30 días
- Leads calientes sin actividad ≥ 7 días

Recibirás una notificación emergente con el resumen. También se registra en el historial del agente.

---

## HISTORIAL Y DASHBOARD

- **Inteligencia IA → Historial**: todas las conversaciones por usuario, tipo de consulta y tiempo de respuesta
- **Inteligencia IA → Memorias del Agente**: memorias guardadas, filtrables por tipo y usuario

---

## TIPS

- Puedes mezclar órdenes: *"Crea un lead para Ana Martínez de WhatsApp, presupuesto $120,000, y busca propiedades que le cuadren"*
- Habla en español, inglés o portugués — el agente detecta tu idioma automáticamente
- Usa los **chips de sugerencia** que aparecen después de cada respuesta para explorar rápidamente
- Si no sabes un ID, describe el nombre: *"la propiedad de la Av. España"*
