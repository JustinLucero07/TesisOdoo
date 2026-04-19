# Integración Formulario Houzez → Odoo CRM (vía Email/IMAP)

Guía de configuración para que los formularios de contacto del sitio WordPress
(tema Houzez) creen leads automáticamente en el CRM de Odoo.

Flujo de datos:
```
Usuario llena formulario en WordPress (Houzez)
        ↓
WordPress envía email a Gmail dedicado (leads.inmobi@gmail.com)
        ↓
Odoo lee ese Gmail cada 5 minutos (IMAP)
        ↓
Se crea un Lead en CRM → Odoo con nombre, email, teléfono y mensaje
```

---

## Requisitos previos

- WordPress con tema Houzez instalado y activo
- Plugin **FluentSMTP** instalado en WordPress
- Cuenta Gmail dedicada para recibir leads (ej: `leads.inmobi@gmail.com`)
- Odoo 19 corriendo (local o en servidor)
- Verificación en 2 pasos activa en la cuenta Gmail

---

## 1. Crear cuenta Gmail dedicada para leads

1. Ir a [accounts.google.com](https://accounts.google.com) y crear una cuenta nueva
   - Ejemplo: `leads.inmobi@gmail.com`
2. Activar verificación en 2 pasos:
   ```
   myaccount.google.com → Seguridad → Verificación en 2 pasos → Activar
   ```
3. Generar contraseña de aplicación:
   ```
   myaccount.google.com → Seguridad → Verificación en 2 pasos
   → Contraseñas de aplicaciones → Seleccionar app: Correo → Generar
   ```
   Guardar la clave de 16 caracteres que aparece (ej: `abcd efgh ijkl mnop`).

4. Activar acceso IMAP en ese Gmail:
   ```
   Gmail → ícono de engranaje → Ver toda la configuración
   → Reenvío y correo POP/IMAP → Habilitar IMAP → Guardar cambios
   ```

---

## 2. Configurar WordPress SMTP (FluentSMTP)

Esto soluciona el error **"Make sure Email function working on your server"** de Houzez.

1. En WordPress ir a:
   ```
   Plugins → Añadir nuevo → buscar "FluentSMTP" → Instalar y activar
   ```

2. Ir a:
   ```
   Ajustes → FluentSMTP → Settings → Add New Connection
   ```

3. Seleccionar **Gmail / Google Workspace** y configurar:

   | Campo | Valor |
   |-------|-------|
   | From Email | tu correo Gmail principal (no el de leads) |
   | From Name | Inmobi / nombre de tu inmobiliaria |
   | Driver | Gmail OAuth o SMTP |

   Si usas SMTP manual:
   | Campo | Valor |
   |-------|-------|
   | SMTP Host | `smtp.gmail.com` |
   | Puerto | `587` |
   | Encriptación | TLS |
   | Usuario | tu Gmail principal |
   | Contraseña | contraseña de aplicación de ese Gmail |

4. Hacer clic en **Save Settings** y luego **Send Test Email** para verificar.

---

## 3. Configurar Houzez para enviar al Gmail de leads

### Opción A — Desde el Personalizador

```
WordPress → Apariencia → Personalizar → Houzez Options → Email Settings
```
Cambiar el campo **Admin Notification Email** a:
```
leads.inmobi@gmail.com
```

### Opción B — Desde opciones de Houzez

```
wp-admin → Houzez → Property Options → Email Notifications
→ Agent Notification Email → leads.inmobi@gmail.com
```

### Opción C — Agregar en functions.php (si las anteriores no aparecen)

Pegar al final del archivo `functions.php` del tema hijo:

```php
// Forzar destinatario de emails de contacto Houzez a Gmail de leads
add_filter('houzez_contact_agent_email', function($email) {
    return 'leads.inmobi@gmail.com';
});
```

Verificar que Houzez envía el email al llenar un formulario de prueba revisando
la bandeja de entrada de `leads.inmobi@gmail.com`.

---

## 4. Configurar servidor de correo entrante en Odoo

1. En Odoo ir a:
   ```
   Ajustes → Técnico → Correo electrónico → Servidores de correo entrante
   → Crear
   ```
   > Si no aparece el menú "Técnico", activar primero el modo desarrollador:
   > `Ajustes → Activar el modo desarrollador`

2. Rellenar el formulario:

   | Campo | Valor |
   |-------|-------|
   | Nombre | Leads WordPress Houzez |
   | Tipo de servidor | IMAP |
   | Servidor | `imap.gmail.com` |
   | Puerto | `993` |
   | SSL/TLS | Activado |
   | Usuario | `leads.inmobi@gmail.com` |
   | Contraseña | contraseña de aplicación de 16 caracteres |

3. En la sección **Acciones**:

   | Campo | Valor |
   |-------|-------|
   | Crear un nuevo registro en | CRM |
   | Política | Crear nuevos leads |

4. Hacer clic en **Probar & Confirmar** → debe mostrar "Conexión exitosa".

5. Hacer clic en **Guardar**.

---

## 5. Verificar que llegan los leads

### Revisión manual inmediata

```
Ajustes → Técnico → Servidores de correo entrante
→ seleccionar "Leads WordPress Houzez" → Obtener correo ahora
```

### Revisión automática (cada 5 minutos)

Odoo ejecuta un cron job que revisa el correo automáticamente. Para
verificar que está activo:
```
Ajustes → Técnico → Automatización → Acciones programadas
→ buscar "Correo: Obtener correo" → verificar que está activo
```

### Ver leads creados

```
CRM → Leads (vista lista)
```
El lead aparecerá con:
- **Nombre:** asunto del email (nombre del contacto + propiedad)
- **Email y teléfono:** del formulario Houzez
- **Descripción:** mensaje completo del formulario
- **Propiedad de interés:** mencionada en el cuerpo del email

---

## 6. Prueba completa

1. Abrir el sitio WordPress y entrar a cualquier propiedad
2. Llenar el formulario de contacto con datos reales de prueba
3. Verificar que:
   - El email llega a `leads.inmobi@gmail.com`
   - En Odoo hacer clic en **Obtener correo ahora**
   - El lead aparece en **CRM → Leads**

---

## 7. Solución de problemas

| Problema | Causa probable | Solución |
|----------|---------------|----------|
| "Make sure Email function working" | WordPress sin SMTP | Instalar y configurar FluentSMTP (paso 2) |
| Email no llega al Gmail de leads | Houzez usa el email del agente, no el admin | Verificar paso 3, usar Opción C (functions.php) |
| Odoo no conecta al Gmail | Contraseña incorrecta o IMAP desactivado | Verificar contraseña de aplicación y IMAP activo |
| Lead sin datos del formulario | Email llegó pero vacío | Revisar que FluentSMTP envía el email completo con el mensaje |
| Error "Application-specific password required" | Usando contraseña normal de Gmail | Generar contraseña de aplicación (paso 1.3) |

---

## 8. Migración a producción

Cuando Odoo se despliegue en un servidor público (VPS), se puede usar el
webhook HTTP directo que no depende del email y es instantáneo:

```
Endpoint Odoo: POST /estate/wp/houzez/inquiry
Autenticación: token secreto en header / body
```

Configuración en Odoo:
```
Ajustes → Integración WordPress → Token Secreto (Webhook)
```

Configuración en WordPress `functions.php`:
```php
define('ODOO_WEBHOOK_URL',    'https://tu-dominio.com/estate/wp/houzez/inquiry');
define('ODOO_WEBHOOK_SECRET', 'tu_clave_secreta');
```

Ver código completo del hook en `estate_wordpress/controllers/main.py`.
