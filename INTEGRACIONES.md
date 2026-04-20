# Configuración de Integraciones Externas

Guía paso a paso para conectar el sistema con WhatsApp Business, WordPress/Houzez, Facebook e Instagram.

---

## Cómo llegan los leads automáticamente

```
Cliente escribe en WhatsApp / Facebook / Instagram
              ↓
     Meta envía el mensaje a Odoo
     vía webhook: POST /meta/webhook
              ↓
  Odoo crea el lead en el CRM automáticamente
  con fuente = WhatsApp / Facebook / Instagram
              ↓
  Si el mismo remitente escribe de nuevo en
  las próximas 24h → se agrega al mismo lead
  (no se duplica)
```

Para que esto funcione debes tener Odoo accesible desde internet (con dominio o ngrok en pruebas) y configurar el webhook en Meta una sola vez.

---

---

## 1. Webhook Meta — Configuración única para los 3 canales

WhatsApp, Facebook e Instagram usan la **misma infraestructura de webhooks** de Meta. Se configura una sola vez.

### Paso 1 — Elegir tu Token de Verificación

Es una cadena que tú inventas (cualquier texto sin espacios), por ejemplo: `inmobi_webhook_2025`

En Odoo: **Ajustes → WhatsApp Citas → Webhook Meta → Token de Verificación** → pegar el token.

### Paso 2 — Registrar el webhook en Meta

1. Ir a [developers.facebook.com](https://developers.facebook.com) → Tu App → **Webhooks**
2. Clic en **Agregar suscripción** (o editar si ya existe)
3. Completar:

| Campo | Valor |
|---|---|
| URL de devolución de llamada | `https://tu-dominio.com/meta/webhook` |
| Token de verificación | El mismo token que pusiste en Odoo |

4. Clic en **Verificar y guardar** — Meta hace un GET al endpoint con ese token, Odoo responde correctamente y la verificación pasa.

### Paso 3 — Suscribir los eventos

Después de verificar, suscribirse a los campos:

| Canal | Campo a suscribir |
|---|---|
| WhatsApp | `messages` |
| Facebook Messenger | `messages`, `messaging_postbacks` |
| Instagram DMs | `messages` |

> Para pruebas locales sin dominio puedes usar **ngrok**: `ngrok http 8070` y usar la URL `https://xxxx.ngrok.io/meta/webhook`

---

## 2. WhatsApp Business (Meta Cloud API)

Permite enviar **recordatorios automáticos de citas** al asesor y mensajes de seguimiento a clientes.

### Requisitos previos

- Cuenta en [Meta for Developers](https://developers.facebook.com)
- Número de teléfono activo registrado como WhatsApp Business
- Plantilla de mensaje aprobada por Meta (puede tardar 24–48 h)

### Pasos

**1. Crear la app en Meta**

1. Ir a [developers.facebook.com](https://developers.facebook.com) → **Mis apps** → **Crear app**
2. Tipo: **Business**
3. Agregar producto: **WhatsApp**

**2. Obtener credenciales**

En **WhatsApp → Configuración de la API**:

| Dato | Dónde encontrarlo |
|---|---|
| `Phone Number ID` | Panel de WhatsApp → "Número de teléfono" → ID numérico |
| `Access Token` | Meta Business → Configuración del negocio → Usuarios del sistema → Generar token (con permisos `whatsapp_business_messaging`) |

> Usar **token permanente** (de Usuario del sistema), no el temporal de prueba.

**3. Crear la plantilla de mensaje**

En **WhatsApp → Plantillas de mensajes** → Nueva plantilla:

- Nombre: `recordatorio_cita` (exactamente así)
- Categoría: **Utilidad**
- Idioma: **Español (Ecuador)**
- Cuerpo sugerido:

```
Recordatorio: tiene una cita {{1}} a las {{2}}.
Cliente: {{3}} | Propiedad: {{4}}
— Equipo Inmobiliario
```

Los parámetros corresponden a: `{{1}}` nombre del evento, `{{2}}` hora, `{{3}}` nombre del cliente, `{{4}}` nombre de la propiedad.

**4. Configurar en Odoo**

Ir a **Ajustes → Inmobiliaria → WhatsApp**:

| Campo | Valor |
|---|---|
| Activar WhatsApp | ✅ Activado |
| Phone Number ID | (el ID obtenido en paso 2) |
| Access Token (permanente) | (el token obtenido en paso 2) |
| Nombre de Plantilla | `recordatorio_cita` |
| Número WhatsApp Business | `593XXXXXXXXX` (sin +, con código de país) |

**5. Cron automático**

El sistema envía recordatorios **1 hora antes** de cada cita con propiedad asignada. El cron se activa automáticamente si la integración está habilitada.

### Limitaciones

- Los **mensajes de texto libre** solo funcionan si el cliente te escribió primero en las últimas **24 horas** (ventana de servicio al cliente de Meta).
- Para mensajes salientes sin restricción de tiempo, se requiere plantilla aprobada.

---

## 2. WordPress / Houzez

Publica y sincroniza propiedades automáticamente en tu sitio web Houzez.

### Requisitos previos

- WordPress con tema **Houzez** instalado
- Plugin **JWT Authentication for WP REST API** (recomendado) o usar Contraseña de Aplicación
- Plugin personalizado de webhook para recibir leads desde el formulario Houzez → Odoo (opcional)

### Pasos

**1. Crear Contraseña de Aplicación en WordPress**

En WordPress → **Usuarios → Tu perfil → Contraseñas de aplicación**:
- Nombre: `Odoo Integration`
- Copiar la contraseña generada (formato: `xxxx xxxx xxxx xxxx xxxx xxxx`)

**2. (Alternativa) Instalar JWT**

Instalar plugin: `JWT Authentication for WP REST API`

En `wp-config.php` agregar:
```php
define('JWT_AUTH_SECRET_KEY', 'una-clave-secreta-larga-y-aleatoria');
define('JWT_AUTH_CORS_ENABLE', true);
```

**3. Obtener IDs de taxonomías Houzez**

Los IDs ya están mapeados automáticamente en el sistema. Si necesitas ajustar para tu sitio:

- Tipos de propiedad: WordPress → **Propiedades → Tipos** → ver ID en la URL al editar
- Estados: WordPress → **Propiedades → Estados**
- Ciudades: WordPress → **Propiedades → Ciudades**

**4. Configurar en Odoo**

Ir a **Ajustes → Inmobiliaria → WordPress/Houzez**:

| Campo | Valor |
|---|---|
| URL de WordPress | `https://tudominio.com` |
| Usuario WordPress | Tu usuario administrador de WP |
| Contraseña / App Pass | La contraseña de aplicación |
| Método de Autenticación | `Contraseña de Aplicación` o `JWT` |
| Post Type | `property` (para Houzez) |
| Integración WordPress Activa | ✅ |
| Token Secreto (Webhook) | Cualquier cadena aleatoria (ej: `mi_token_secreto_2025`) |

Hacer clic en **Probar Conexión** para validar.

**5. Sincronizar Agentes**

Hacer clic en **Obtener Agentes de Houzez**. El sistema descarga los agentes registrados en WordPress para poder asignarlos al publicar propiedades.

En tu perfil de usuario (Odoo → preferencias) asigna tu **Agente WordPress** correspondiente.

**6. Publicar una propiedad**

Desde cualquier ficha de propiedad → botón **Publicar en WordPress**. El sistema:
- Crea o actualiza el post tipo `property` en Houzez
- Sincroniza título, precio, área, habitaciones, ciudad, tipo, estado y fotos
- Guarda el `wp_post_id` en la propiedad para actualizaciones futuras

**7. Recibir leads desde el formulario Houzez (webhook)**

En WordPress, el plugin de webhook debe enviar un `POST` a:

```
https://tu-odoo.com/estate/webhook/wp_lead
```

Con cabecera:
```
X-Webhook-Secret: mi_token_secreto_2025
```

Y cuerpo JSON:
```json
{
  "name": "Nombre del contacto",
  "email": "email@ejemplo.com",
  "phone": "+593981234567",
  "message": "Mensaje del formulario",
  "property_id": 42
}
```

El sistema crea automáticamente el lead en el CRM con fuente `WordPress/Houzez`.

---

## 3. Facebook

Permite **compartir propiedades** en páginas de Facebook. La integración es de difusión (publicar/compartir), no de mensajería automatizada.

### Configurar en Odoo

Ir a **Ajustes → Inmobiliaria → Redes Sociales**:

| Campo | Dónde obtenerlo |
|---|---|
| Facebook Page ID | Facebook → Tu página → **Acerca de** → ID de página (número al final de la URL) |
| Page Access Token | [developers.facebook.com](https://developers.facebook.com) → Tu App → **Herramientas → Explorador de la API Graph** → seleccionar tu página → copiar token |

### Usar desde una propiedad

Desde la ficha de propiedad → botón **Compartir en Facebook**:
- Si la propiedad está publicada en WordPress, comparte el enlace del post
- Si no, comparte el texto con los datos de la propiedad

### Crear un lead desde Facebook (manual)

Cuando un cliente comenta o envía un mensaje por Facebook:

1. Ir a **CRM → Oportunidades → Nuevo**
2. Llenar: nombre del lead, contacto, presupuesto
3. **Fuente del Lead** → `📘 Facebook`
4. El sistema crea automáticamente la actividad de seguimiento

---

## 4. Instagram

Instagram **no permite publicación automática desde terceros** sin una app aprobada por Meta (proceso de revisión de 4–8 semanas). El sistema ofrece:

- **Generación de caption lista** con hashtags optimizados para copiar y pegar
- **Enlace directo a la app** de Instagram

### Configurar en Odoo

Ir a **Ajustes → Inmobiliaria → Redes Sociales**:

| Campo | Dónde obtenerlo |
|---|---|
| Instagram Business Account ID | [developers.facebook.com](https://developers.facebook.com) → Tu App → **Instagram → Configuración de la API** → Account ID |
| URL Pública del Servidor | URL de tu Odoo si es accesible desde internet (para imágenes) |

> La cuenta de Instagram debe estar vinculada a una **Página de Facebook** y configurada como cuenta **Business** o **Creator**.

### Usar desde una propiedad

Desde la ficha de propiedad → botón **Compartir en Instagram**:

El sistema muestra una notificación con la caption lista, por ejemplo:

```
🏠 Casa Moderna El Vergel

📍 Cuenca
💰 $185,000.00
📐 220 m²  |  🛏️ 4 hab  |  🚿 3 baños

💬 WhatsApp: wa.me/593981234567
Ref: P00001

#casa #cuenca #inmobiliaria #bienesraices #realestate
#casaenventa #propiedades #ecuador #inversioninmobiliaria
```

Copia el texto, abre Instagram y pégalo junto a la foto de la propiedad.

### Crear un lead desde Instagram (manual)

Cuando alguien comenta o envía un DM en Instagram:

1. Ir a **CRM → Oportunidades → Nuevo**
2. **Fuente del Lead** → `📸 Instagram`
3. El sistema crea la actividad y registra el origen

---

## Resumen de dónde se configuran

Todos los parámetros se gestionan desde un solo lugar:

**Ajustes → (menú lateral) Inmobiliaria**

| Sección | Integración |
|---|---|
| WhatsApp | Meta Cloud API — recordatorios de citas |
| WordPress/Houzez | Publicación y sincronización de propiedades |
| Redes Sociales | Facebook Page ID/Token, Instagram Account ID, número WhatsApp Business |
