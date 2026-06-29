# Banco de pruebas — Chats del sistema Inmobi

Guía de preguntas para probar **todos los asistentes conversacionales** del sistema.
Marca ✅ si responde bien, ❌ si falla o responde de forma inconsistente.

> Sugerencia: prueba primero en **InmoBot (chat flotante)** y repite las mismas en la
> **página de Agente IA**, ya que comparten el mismo motor. El **bot de WhatsApp (n8n)**
> tiene su propia sección al final porque es para clientes finales.

---

## 1. InmoBot — chat flotante / página de Agente IA (Odoo)

### 1.1 Consultas básicas (lectura)
- ¿Cuántas propiedades tengo en total?
- Muéstrame las propiedades disponibles.
- ¿Qué propiedades hay en Cuenca por menos de 100.000?
- Dame el detalle de la propiedad PROP-0095.
- Busca al cliente Carlos.
- Dame el resumen del cliente Justin (perfil 360°).
- ¿Cuántos leads activos tengo?
- Muéstrame los leads calientes.
- Leads por temperatura.
- ¿Qué leads están "hirviendo" y sin respuesta?

### 1.2 Reportes y analítica
- Informe ejecutivo del mes.
- Dame el resumen del tablero (dashboard).
- ¿Cuál es la tendencia de ventas de este mes contra el anterior?
- Estadísticas del mercado.
- Compara la propiedad PROP-0095 con PROP-0100.
- Ranking de asesores del mes.
- ¿Cuántas propiedades llevan más de 60 días sin moverse?

### 1.3 Exportar / documentos
- Exporta el reporte de leads por temperatura a Excel.
- Genera el PDF de la ficha de la propiedad PROP-0095.
- Genera una cotización en PDF para el cliente Carlos sobre PROP-0095.
- Genera el pack de marketing de PROP-0095.
- Llévame a la vista de reportes de comisiones.

### 1.4 Calendario y visitas
- ¿Qué visitas tengo próximamente?
- Agenda una visita para la propiedad PROP-0095 con el cliente Carlos mañana a las 10.

### 1.5 Acciones sobre propiedades (escritura)
- Crea una propiedad: Casa en Cuenca, 3 habitaciones, 120 m², precio 95.000.
- Cambia el precio de PROP-0095 a 88.000.
- Mejora la descripción de PROP-0095 con IA.
- Recalcula el AVM de PROP-0095.
- Reserva la propiedad PROP-0095.
- ¿Qué puedo mejorar de la propiedad PROP-0095?
- ¿Quién está interesado en PROP-0095?

### 1.6 Acciones sobre leads / CRM
- Crea un lead: cliente Pedro, presupuesto 70.000, busca casa en Cuenca.
- Sube la temperatura del lead de Carlos a "caliente".
- ¿Qué probabilidad de cierre tiene el lead de Carlos?
- ¿Hay riesgo de que el lead de Carlos se enfríe (churn)?
- Crea una actividad de seguimiento para el lead de Carlos para el viernes.
- Envía un WhatsApp al lead de Carlos.

### 1.7 Contratos, pagos y comisiones
- Muéstrame los contratos y pagos activos.
- ¿Hay pagos vencidos?
- Crea un contrato para el lead de Carlos con la propiedad PROP-0095.
- Registra un pago de 5.000 para el contrato de Carlos.
- Aprueba el pago pendiente del contrato de Carlos.

### 1.8 Marketing e IA avanzada
- Planifica una campaña de marketing para PROP-0095.
- Genera y aplica una descripción comercial a PROP-0095.

### 1.9 Memoria del asistente
- Recuerda que mi asesor preferido es Justin. *(save_memory)*
- ¿Qué recuerdas de mis preferencias? *(recall_memory)*

### 1.10 Consulta libre (SQL)
- ¿Cuál es la propiedad más cara del catálogo?
- Dame el promedio de precio por ciudad.

### 1.11 Contexto y multi-turno (memoria de conversación)
1. Háblame de la propiedad PROP-0095.
2. ¿Y cuántas visitas tiene **esa propiedad**?
3. ¿Quién es el dueño **de esa**?
4. Genérame el PDF **de esa**.
> Debe entender "esa/anterior" sin volver a pedir el ID.

### 1.12 Casos límite (manejo de errores y "no encontrado")
- Dame el detalle de la propiedad PROP-9999. *(no existe → debe avisar con claridad)*
- Busca al cliente Zxqwerty. *(sin resultados → debe decir que no encontró)*
- asdkjahsd *(texto sin sentido → debe pedir reformular, no romperse)*
- Pregunta vacía / solo espacios.
- Una pregunta muy larga con varias peticiones a la vez (ej: "dame el informe ejecutivo, las propiedades disponibles y los leads calientes").
> ⚠️ Objetivo de estas pruebas: **nunca** debe responder "Sin respuesta del modelo".
> Debe responder con datos, decir que no encontró, o pedir que reformules.

### 1.13 Adjuntar documento (OCR) — botón 📎
- Sube una imagen/PDF de una cédula o un documento y pide: "extrae los datos".

### 1.14 Conocimiento / documentación (RAG) — `search_knowledge`
> Requiere haber indexado antes en **Ajustes → Agente IA → Reindexar conocimiento**.
- ¿Cómo creo un contrato en el sistema?
- ¿Cómo agendo una visita?
- ¿Qué hace el módulo de WordPress?
- ¿Para qué sirve el AVM?
- ¿Cómo configuro WhatsApp?
- ¿Qué permisos tiene el rol "Asesor"?
- ¿Cómo conecto Google Calendar?
- ¿Qué significa el estado "reservado" de una propiedad?
> Debe responder citando el manual/guía, no inventar. Si no está en la documentación, debe decirlo.

---

## 2. Bot de WhatsApp — "Asistente Virtual Inmobi" (n8n)

Pruebas desde el WhatsApp del negocio (cliente final). Mensajes típicos:

### 2.1 Búsqueda de propiedades
- Hola, busco una casa en Cuenca.
- Quiero un departamento de 2 habitaciones hasta 80.000.
- ¿Qué terrenos tienen disponibles?
- Muéstrame propiedades por sector.
- Busco algo por metraje, mínimo 150 m².

### 2.2 Detalle e interés
- Dame más información de esa propiedad.
- ¿Cuánto cuesta? ¿Tiene parqueadero?
- Quiero agendar una visita.
- Me interesa, ¿cómo sigo el proceso?

### 2.3 Captación / lead
- Soy nuevo, quiero que me asesoren.
- Necesito asesoría de crédito hipotecario.

### 2.4 Casos límite
- Mensaje sin sentido (ej: "asdfgh") → debe responder con cortesía y reencauzar.
- Pedir algo fuera de alcance (ej: "véndeme un carro") → debe aclarar que es inmobiliaria.

---

## 3. Qué observar en cada prueba

| Aspecto | Esperado |
|--------|----------|
| **Responde** | Siempre da una respuesta útil (datos, gráfico, PDF o aviso claro). |
| **Sin "Sin respuesta del modelo"** | Ese mensaje NO debe aparecer; si no hay datos, lo dice con palabras. |
| **Coherencia** | La respuesta corresponde a lo que se preguntó (no mezcla consultas anteriores). |
| **Acciones** | Al crear/actualizar, confirma con el resultado (ej: "Creé la propiedad PROP-0123"). |
| **Contexto** | Entiende "esa/el anterior" sin volver a pedir el ID. |
| **Errores claros** | Si falta configuración o el proveedor de IA falla, da un mensaje entendible. |

> Si un proveedor de IA se queda sin crédito o sin red, el agente debe **reintentar con el
> proveedor de respaldo** o mostrar un mensaje claro, sin tumbar el resto del sistema.
