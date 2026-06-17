# Guía de configuración — Google Calendar (Inmobi)

Sincroniza las visitas de Inmobi con Google Calendar. Hay **dos opciones** y se elige en
**Ajustes → Calendario (Visitas) → Modo de sincronización**.

---

# 🅰️ Opción A — Nativa (cada usuario con su cuenta)

Cada asesor conecta SU propia cuenta de Google y sus citas sincronizan con SU calendario.

## Parte 1 — Google Cloud (una sola vez, lo hace el administrador)

1. Entra a **https://console.cloud.google.com** con la cuenta de Google de la empresa.
2. Arriba, **crea un proyecto** (ej. "Inmobi") y selecciónalo.
3. Menú ☰ → **APIs y servicios → Biblioteca** → busca **"Google Calendar API"** → **Habilitar**.
4. Menú ☰ → **APIs y servicios → Pantalla de consentimiento de OAuth**:
   - Tipo de usuario: **Externo** → Crear.
   - Nombre de la app: *Inmobi*, correo de soporte y de contacto → Guardar y continuar.
   - En *Usuarios de prueba*, agrega los correos de los asesores que van a conectar su cuenta.
5. Menú ☰ → **APIs y servicios → Credenciales → Crear credenciales → ID de cliente de OAuth**:
   - Tipo de aplicación: **Aplicación web**.
   - Nombre: *Inmobi Odoo*.
   - En **URI de redireccionamiento autorizados**, agrega EXACTAMENTE:
     ```
     http://localhost:8070/google_account/authentication
     ```
     > En producción usa tu dominio real, ej:
     > `https://inmobi.tudominio.com/google_account/authentication`
   - **Crear**. Copia el **ID de cliente** y el **Secreto de cliente**.

## Parte 2 — En Odoo (administrador)

6. **Ajustes → Calendario (Visitas)** → Modo: **"Nativo de Odoo"** → Guardar.
7. **Ajustes → Ajustes generales** → busca la sección **Google Calendar**:
   - Pega el **ID de cliente** y el **Secreto de cliente** → Guardar.

## Parte 3 — Cada usuario

8. Abre la app **Calendario** de Odoo → botón **"Sincronizar con Google"** (o similar).
9. Inicia sesión con su cuenta Google y **acepta los permisos**.
10. Sus citas empiezan a sincronizar con su Google Calendar personal.

---

# 🅱️ Opción B — Calendario compartido (recomendada)

Todas las visitas van a **un único calendario del equipo** mediante una **cuenta de servicio**
(no depende de la cuenta de cada usuario).

## Parte 1 — Google Cloud (una sola vez)

1. **https://console.cloud.google.com** → crea/usa un proyecto (ej. "Inmobi").
2. **APIs y servicios → Biblioteca** → habilita **Google Calendar API**.
3. **APIs y servicios → Credenciales → Crear credenciales → Cuenta de servicio**:
   - Nombre: *inmobi-calendario* → Crear y continuar → (rol opcional) → Listo.
4. Entra a la cuenta de servicio recién creada → pestaña **Claves → Agregar clave → Crear clave nueva → JSON**.
   - Se descarga un archivo `.json`. **Guárdalo bien** (son las credenciales).
   - Anota el **email** de la cuenta de servicio (algo como
     `inmobi-calendario@inmobi-xxxx.iam.gserviceaccount.com`).

## Parte 2 — Google Calendar (el calendario compartido)

5. Entra a **https://calendar.google.com** con la cuenta de la empresa.
6. A la izquierda, junto a *"Otros calendarios"*, pulsa **+ → Crear calendario nuevo**:
   - Nombre: **"Visitas Inmobi"** → Crear calendario.
7. Abre la **Configuración** de ese calendario (pasa el mouse → ⋮ → Configuración).
8. En **"Compartir con determinadas personas o grupos"** → **Añadir personas**:
   - Pega el **email de la cuenta de servicio** (paso 4).
   - Permiso: **"Hacer cambios en los eventos"** → Enviar.
   - Agrega también a tu equipo (permiso de lectura) para que vean las visitas.
9. En esa misma página, baja hasta **"Integrar calendario"** y copia el **ID del calendario**
   (suele terminar en `@group.calendar.google.com`).

## Parte 3 — En Odoo (administrador)

10. **Ajustes → Calendario (Visitas)**:
    - Modo: **"Calendario compartido (cuenta de servicio)"**.
    - **ID del Calendario compartido**: pega el ID del paso 9.
    - **Credenciales (JSON)**: abre el archivo `.json` con un editor de texto y **pega todo su contenido**.
    - **Guardar**.

## Parte 4 — Probar

11. Agenda una **visita** en Odoo (una cita con una propiedad asignada).
12. Abre **https://calendar.google.com** → el calendario **"Visitas Inmobi"** debe mostrar el evento,
    con la propiedad, ubicación, cliente y asesor en la descripción.
13. Edita o cancela la visita en Odoo → el evento se **actualiza o borra** en Google automáticamente.

---

## Solución de problemas

| Problema | Causa / Solución |
|----------|------------------|
| La visita no aparece en Google (Opción B) | Verifica que el **email de la cuenta de servicio** tenga permiso *"Hacer cambios"* en el calendario, y que el **ID del calendario** y el **JSON** estén bien pegados. |
| "Calendar API has not been used / disabled" | Habilita **Google Calendar API** en el proyecto correcto (Parte 1). |
| Opción A: "redirect_uri_mismatch" | El URI de redireccionamiento en Google debe ser EXACTAMENTE el de Odoo (incluyendo http/https, dominio y puerto). |
| Nada se sincroniza | Revisa que el **Modo** correcto esté seleccionado en Ajustes y guardado. |

> **Nota:** si Google falla o no está configurado, la visita **se crea igual en Odoo** — la
> sincronización nunca rompe el trabajo diario.

---

*Inmobi Community — Sincronización con Google Calendar.*
