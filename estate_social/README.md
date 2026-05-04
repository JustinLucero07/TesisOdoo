# Configuración Meta Graph API — Instagram & Facebook Stats

> **Sistema:** Inmobi Odoo — Tesis de Grado  
> **App Meta:** Inmobi Odoo (ID: 943650865299170)  
> **Odoo:** http://localhost:8070

---

## Requisitos previos

Antes de empezar necesitas tener:

- [ ] Una **Página de Facebook** de tu inmobiliaria (no perfil personal)
- [ ] Una cuenta de **Instagram Business o Creator** vinculada a esa página
- [ ] Acceso de administrador a ambas
- [ ] Tu app `Inmobi Odoo` en Meta Developers (ya la tienes)

---

## PASO 1 — Vincula Instagram a tu Página de Facebook

Instagram Business debe estar conectado a tu Página de Facebook para que la API funcione.

1. Ve a tu **Página de Facebook** → Configuración  
2. Busca **Instagram** en el menú izquierdo  
3. Haz clic en **Conectar cuenta de Instagram**  
4. Inicia sesión con tu cuenta de Instagram Business

**Verificar que quedó vinculado:**  
→ https://www.facebook.com/pages — selecciona tu página → Configuración → Instagram

---

## PASO 2 — Configura Facebook Login en tu App

Tu app necesita el producto **Facebook Login para empresas** para generar tokens con permisos.

1. Ve a tu app:  
   → https://developers.facebook.com/apps/943650865299170

2. En el menú izquierdo haz clic en **Agregar producto**

3. Busca **"Facebook Login para empresas"** → clic en **Configurar**

4. En la configuración de Facebook Login, en el campo  
   **"URIs de redireccionamiento de OAuth válidos"** agrega:
   ```
   http://localhost:8070
   ```
   Guarda los cambios.

---

## PASO 3 — Activa los permisos de Instagram

1. En tu app ve a:  
   **Instagram → Configuración de la API**  
   → https://developers.facebook.com/apps/943650865299170/instagram-basic-display/basic-display/

2. En **Permisos y Funciones** (menú izquierdo de la app), busca y activa:

   | Permiso | Para qué sirve |
   |---------|----------------|
   | `instagram_basic` | Leer info básica de la cuenta IG |
   | `instagram_manage_insights` | Ver estadísticas de cada post (impresiones, alcance, likes, etc.) |
   | `pages_read_engagement` | Requerido por Meta para acceder a insights de IG |
   | `pages_show_list` | Ver páginas vinculadas |
   | `read_insights` | Estadísticas de posts de la Página de Facebook |
   | `pages_manage_posts` | Publicar en la página (ya deberías tenerlo) |

   > En modo **Desarrollo** no necesitas revisión de Meta — funciona directamente si eres admin de la app y de la página.

---

## PASO 4 — Obtén tu Instagram Business Account ID

Este es el ID de tu cuenta de Instagram Business (diferente al username).

**Opción A — Desde el Explorador de la API Graph:**

1. Ve al Explorador:  
   → https://developers.facebook.com/tools/explorer/

2. Selecciona tu app **Inmobi Odoo** (arriba a la derecha)

3. En el campo de consulta escribe:
   ```
   GET /me/accounts
   ```
   Haz clic en **Enviar** — te devuelve tus páginas con sus IDs

4. Copia el `id` de tu página y luego consulta:
   ```
   GET /{page-id}?fields=instagram_business_account
   ```
   El `id` dentro de `instagram_business_account` es tu **Instagram Business Account ID**

**Guarda ese ID** — lo necesitas en Odoo.

---

## PASO 5 — Genera el Page Access Token (token principal)

Este token da acceso a publicar y leer estadísticas. Es el más importante.

1. Ve al Explorador de la API Graph:  
   → https://developers.facebook.com/tools/explorer/

2. Configura esto:
   - **App:** Inmobi Odoo
   - **Tipo de token:** Token de usuario (por defecto)

3. Haz clic en **Generar token de acceso**

4. En el popup marca **todos** estos permisos:
   ```
   instagram_basic
   instagram_manage_insights
   instagram_content_publish
   pages_read_engagement
   pages_show_list
   pages_manage_posts
   read_insights
   ```

5. Autoriza con tu cuenta de Facebook

6. Copia el token generado (empieza con `EAAJ...`)

7. Ahora conviértelo en **Page Access Token** (token de la página, no del usuario):
   ```
   GET /me/accounts
   ```
   En la respuesta verás tus páginas — cada una tiene su propio `access_token`.  
   **Copia el `access_token` de tu página** (no el token del usuario).

---

## PASO 6 — Convierte el token a larga duración (No expira)

El token del Explorador dura **1 hora**. Necesitas uno permanente.

Abre la terminal y ejecuta (reemplaza los valores):

```bash
curl "https://graph.facebook.com/v25.0/oauth/access_token" \
  -d "grant_type=fb_exchange_token" \
  -d "client_id=943650865299170" \
  -d "client_secret=TU_APP_SECRET" \
  -d "fb_exchange_token=TOKEN_CORTO_DE_USUARIO"
```

**Dónde encontrar tu App Secret:**  
→ https://developers.facebook.com/apps/943650865299170/settings/basic/  
Campo: **Clave secreta de la app** (haz clic en "Mostrar")

El resultado será un **token de larga duración** (~60 días).  
Luego busca el Page Access Token de ese token largo:
```bash
curl "https://graph.facebook.com/v25.0/me/accounts?access_token=TOKEN_LARGO"
```

El `access_token` de tu página en esa respuesta **no expira nunca**.

---

## PASO 7 — Configura todo en Odoo

Ve a:  
**Odoo → Ajustes → (busca "Redes Sociales")** o  
**Ajustes → IA Inmobiliaria → Redes Sociales**

Completa estos campos:

| Campo en Odoo | Valor |
|---------------|-------|
| **Número WhatsApp Business** | Tu número con código de país, sin + (ej: `593981234567`) |
| **Facebook Page ID** | El `id` de tu página (obtenido en Paso 4, GET /me/accounts) |
| **Page Access Token** | El token permanente de la página (Paso 6) |
| **Instagram Business Account ID** | El ID obtenido en Paso 4 |
| **URL Pública del Servidor** | `http://localhost:8070` (o tu dominio si tienes) |

---

## PASO 8 — Verifica que funciona

### Verificar Instagram Stats

En el Explorador de la API Graph, prueba con el Post ID de un post publicado:

```
GET /{ig-media-id}/insights?metric=impressions,reach,likes,comments,shares,saved
```

Si devuelve datos → todo correcto.

### Verificar Facebook Page

```
GET /{page-id}/feed?fields=id,message,created_time
```

Si devuelve posts → el token tiene los permisos correctos.

---

## Links de referencia rápida

| Recurso | URL |
|---------|-----|
| Panel de tu app | https://developers.facebook.com/apps/943650865299170 |
| Explorador API Graph | https://developers.facebook.com/tools/explorer/ |
| Permisos y Funciones | https://developers.facebook.com/apps/943650865299170/app-review/permissions/ |
| Configuración básica (App Secret) | https://developers.facebook.com/apps/943650865299170/settings/basic/ |
| Instagram en tu app | https://developers.facebook.com/apps/943650865299170/instagram/ |
| Tus páginas de Facebook | https://www.facebook.com/pages |
| Documentación Insights Instagram | https://developers.facebook.com/docs/instagram-api/reference/ig-media/insights |
| Documentación Page Insights FB | https://developers.facebook.com/docs/graph-api/reference/v25.0/insights |
| Generar token larga duración | https://developers.facebook.com/docs/facebook-login/guides/access-tokens/get-long-lived |

---

## Solución de errores comunes

| Error | Causa | Solución |
|-------|-------|----------|
| `OAuthException: (#10)` | Token sin permisos suficientes | Regenera el token marcando todos los permisos del Paso 5 |
| `Invalid OAuth access token` | Token expirado | Sigue el Paso 6 para obtener token permanente |
| `Unsupported get request` | El post tiene menos de 24h | Espera 24h después de publicar para ver métricas |
| `Object does not exist` | El `ig_post_id` es incorrecto | Verifica que el post fue publicado vía API (no manualmente desde el celular) |
| `Media posted before business account conversion` | El post es anterior a convertir la cuenta a Business | Solo aplica a posts publicados después de configurar la cuenta Business |
| No aparece Instagram en `/me/accounts` | Instagram no está vinculado a la Página | Sigue el Paso 1 |

---

## Notas importantes

> **Instagram solo entrega estadísticas de:**
> - Posts publicados vía Graph API (los publicados manualmente desde la app no siempre tienen métricas via API)
> - Cuentas Business o Creator (no cuentas personales)
> - Posts con más de **24 horas** de publicados
> - El **token debe ser de la Página**, no del usuario personal

> **Modo Desarrollo vs Producción:**  
> En modo Desarrollo solo tú (admin de la app) puedes usar los permisos avanzados.  
> Para tu tesis esto es suficiente — no necesitas pasar a producción.
