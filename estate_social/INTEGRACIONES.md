# Integraciones de Redes Sociales — Inmobi

## 1. WhatsApp Business (Meta Cloud API)

### Qué hace
Envía recordatorios automáticos de citas al asesor 1 hora antes via WhatsApp.

### Requisitos
- Cuenta en [developers.facebook.com](https://developers.facebook.com)
- App tipo "Negocios" con WhatsApp habilitado
- Plantilla de mensaje aprobada en Meta

### Configuración paso a paso

1. Ve a [developers.facebook.com](https://developers.facebook.com) → tu app → **WhatsApp → Configuración de la API**
2. Copia el **Phone Number ID** (ej: `1117287444793731`)
3. Genera un **Access Token** desde esa misma página
4. Crea la plantilla `recordatorio_cita` en [business.facebook.com](https://business.facebook.com) → WhatsApp Manager → Plantillas:
   ```
   Categoría: Utilidad
   Nombre: recordatorio_cita
   Idioma: Spanish (ECU)
   Cuerpo:
   Recordatorio de cita: *{{1}}*
   Hora: {{2}}
   Cliente: {{3}}
   Propiedad: {{4}}
   ¡No olvides tu cita!
   ```
5. En modo prueba, agrega el número del asesor en Meta → **"Para" → Administrar lista**
6. En Odoo → **Ajustes → WhatsApp Citas** configura:
   - ✅ WhatsApp Activo
   - Phone Number ID
   - Access Token
   - Nombre de Plantilla: `recordatorio_cita`

### Cómo probar
- Crea una cita en Calendario con propiedad asignada y fecha = ahora + 30 min
- El asesor debe tener teléfono móvil en su ficha de Contacto
- Ve a **Ajustes → Técnico → Acciones programadas → "WhatsApp: Recordatorios de Citas"**
- Clic en **"Ejecutar manualmente"**
- Revisa el log: `INFO: Recordatorio enviado a asesor [nombre]`

### Limitaciones modo prueba
- Solo puedes enviar a números verificados manualmente en Meta (máx. 5)
- Para producción: verificar empresa en Meta Business → modo Producción

---

## 2. Facebook — Publicación Automática

### Qué hace
Publica propiedades directamente en tu página de Facebook desde Odoo con un clic.

### Requisitos
- Página de Facebook tipo Negocio (no perfil personal)
- App de Meta con permisos: `pages_manage_posts`, `pages_read_engagement`

### Configuración paso a paso

1. **Crea una página** (si no tienes): [facebook.com/pages/create](https://www.facebook.com/pages/create)

2. **Obtén el Page Access Token**:
   - Ve a [developers.facebook.com/tools/explorer](https://developers.facebook.com/tools/explorer/)
   - Selecciona tu app → en **"Usuario o página"** selecciona tu página
   - Agrega permisos: `pages_manage_posts`, `pages_read_engagement`
   - Clic en **"Generate Access Token"** → cópialo

3. **Obtén el Page ID**:
   - En el Explorador con token de página activo, ejecuta: `me?fields=id,name`
   - Copia el `id` que devuelve

4. En Odoo → **Ajustes → Redes Sociales** configura:
   - Facebook Page ID
   - Page Access Token

### Cómo usar
- Abre cualquier propiedad → pestaña **"Redes Sociales"**
- Clic en **"Publicar en Facebook"**
- El post aparece en tu página con el texto de la propiedad

### Nota
El token de página expira. Para un token permanente:
- Meta Business → Usuarios del sistema → crea usuario sistema → genera token sin expiración

---

## 3. Instagram Business — Publicación Automática

### Qué hace
Publica propiedades en tu cuenta de Instagram Business desde Odoo.

### Requisitos
- Cuenta de Instagram convertida a **Business** o **Creator**
- Vinculada a tu página de Facebook
- Permisos: `instagram_basic`, `instagram_content_publish`
- La imagen debe ser accesible por URL pública (WordPress o servidor expuesto)

### Configuración paso a paso

1. **Vincula Instagram a tu página de Facebook**:
   - Facebook → tu página → **Configuración → Instagram → Conectar cuenta**

2. **Obtén el Instagram Account ID**:
   - En el Explorador de la API Graph con tu Page Access Token
   - Ejecuta: `me?fields=instagram_business_account`
   - Copia el `id` del resultado

3. **URL pública de imágenes** — elige una opción:
   - **Opción A (recomendada)**: Publica la propiedad en WordPress primero → el sistema usa la URL de WordPress
   - **Opción B**: Expón tu servidor Odoo a internet y configura la URL pública en Ajustes

4. En Odoo → **Ajustes → Redes Sociales** configura:
   - Instagram Business Account ID
   - URL Pública del Servidor (si no usas WordPress)

### Cómo usar
- Abre cualquier propiedad → pestaña **"Redes Sociales"**
- Clic en **"Publicar en Instagram"**

### Limitaciones modo desarrollo
- Solo el administrador de la app puede publicar
- Para publicar desde cualquier cuenta: aprobación de Meta (`instagram_content_publish` requiere revisión)

---

## 4. Resumen de tokens y permisos

| Integración | Token necesario | Permisos |
|-------------|----------------|----------|
| WhatsApp recordatorios | Token de sistema (WhatsApp) | `whatsapp_business_messaging` |
| Facebook publicar | Page Access Token | `pages_manage_posts`, `pages_read_engagement` |
| Instagram publicar | Page Access Token | `instagram_basic`, `instagram_content_publish` |

---

## 5. Flujo de leads de WhatsApp al CRM (idea futura)

Cuando un cliente escribe al número de WhatsApp Business de la inmobiliaria, el sistema puede capturar ese mensaje y crear automáticamente un lead en el CRM.

### Cómo funcionaría
```
Cliente escribe WhatsApp
        ↓
Meta manda Webhook a Odoo (/whatsapp/inbound)
        ↓
Odoo busca si el número ya existe como contacto
        ↓
Si NO existe → crea res.partner con el número
        ↓
Crea crm.lead con:
  - lead_source = 'whatsapp'
  - Mensaje del cliente como descripción
  - Asignado al asesor de turno
        ↓
Asesor ve el lead en CRM con el mensaje original
```

### Para implementarlo se necesita
1. En Meta → tu app → WhatsApp → Configuración → **Webhook** → URL: `https://tuservidor.com/whatsapp/inbound`
2. Verificar el webhook con un token secreto
3. El servidor Odoo debe estar expuesto a internet (ngrok para pruebas)
