# Manual Técnico y de Despliegue

**Proyecto:** Sistema de gestión inmobiliaria sobre ERP Odoo 19 con agente inteligente.
**Dirigido a:** administradores de sistemas y desarrolladores.

---

## 1. Arquitectura general

El sistema sigue una **arquitectura de tres capas**:

| Capa | Tecnología | Responsabilidad |
|------|-----------|-----------------|
| Presentación | OWL / JavaScript (Odoo web), WordPress, widget flotante de IA | Interfaz de usuario |
| Lógica de negocio | Odoo 19 (Python) | Reglas de negocio, CRM, tareas programadas (cron) |
| Datos | PostgreSQL + sistema de archivos (filestore) | Persistencia relacional y adjuntos/QR |

Integraciones externas vía API: **Google Gemini / OpenAI** (IA), **WhatsApp Cloud API** (mensajería), **WordPress REST API** (portal) y **Google Calendar API** (visitas).

---

## 2. Requisitos del sistema

| Componente | Versión / detalle |
|-----------|-------------------|
| Sistema operativo (producción) | Ubuntu 24.04 LTS |
| Odoo | 19 Community |
| Python | 3.11+ |
| PostgreSQL | 15/16 |
| Proxy inverso | Nginx con SSL (Let's Encrypt) |
| Contenedores | Docker + Docker Compose |

### Dependencias Python adicionales
```bash
pip install qrcode[pil] google-generativeai openai openpyxl psycopg2-binary requests google-auth
```

---

## 3. Módulos del sistema

| Módulo | Función |
|--------|---------|
| `estate_management` | Núcleo: propiedades, contratos, pagos, comisiones, AVM, QR |
| `estate_crm` | Leads, scoring, match presupuestal, webhooks |
| `estate_calendar` | Visitas, recordatorios WhatsApp |
| `estate_gcal` | Sincronización con Google Calendar compartido |
| `estate_document` | Documentos vinculados + OCR (Gemini Vision) |
| `estate_reports` | Dashboard KPI, exportación PDF/Excel |
| `estate_social` | Publicación/compartir en redes sociales |
| `estate_wordpress` | Sincronización con el sitio WordPress |
| `estate_portal` | Portal del propietario |
| `estate_ai_agent` | Agente conversacional (Gemini/OpenAI) |
| `estate_audit` | Bitácora de auditoría |
| `estate_payroll` | Nómina de asesores |

---

## 4. Instalación en entorno de desarrollo (local)

```bash
# 1. Activar entorno virtual
source /home/justin/Documentos/Tesis/venv19/bin/activate

# 2. Instalar todos los módulos desde cero
python /home/justin/Documentos/odoo19/odoo-bin \
  -c /home/justin/Documentos/Tesis/odoo19.conf \
  -d tesis_odoo19 \
  -i estate_management,estate_crm,estate_reports,estate_ai_agent,estate_document,\
estate_calendar,estate_social,estate_portal,estate_wordpress \
  --stop-after-init

# 3. Levantar el servidor
python /home/justin/Documentos/odoo19/odoo-bin -c /home/justin/Documentos/Tesis/odoo19.conf
# Acceso: http://localhost:8070
```

**Actualizar un módulo** tras cambios:
```bash
python /home/justin/Documentos/odoo19/odoo-bin -c odoo19.conf -d tesis_odoo19 \
  -u nombre_modulo --stop-after-init
```

**Ejecutar pruebas:**
```bash
python /home/justin/Documentos/odoo19/odoo-bin -c odoo19.conf -d tesis_odoo19 \
  --test-enable --stop-after-init -u estate_calendar
```

---

## 5. Despliegue en producción (VPS)

El despliegue está contenerizado en la carpeta `deploy/`.

```
deploy/
├── docker-compose.yml          # Orquesta: PostgreSQL + Odoo + n8n
├── setup-vps.sh                # Inicializa el VPS (Ubuntu 24.04)
├── .env.example                # Plantilla de variables de entorno
├── nginx/nginx.conf            # Proxy inverso + SSL
└── odoo/
    ├── Dockerfile              # Imagen de Odoo con módulos custom
    ├── requirements-custom.txt # Dependencias Python
    └── conf/odoo.conf          # Configuración de Odoo
```

### 5.1. Servicios (docker-compose)

| Servicio | Imagen | Puerto |
|----------|--------|--------|
| `db` | postgres:16-alpine | 5432 (interno) |
| `odoo` | build local (Dockerfile) | 8069/8072 |
| `n8n` | n8nio/n8n:latest | automatización de flujos |

### 5.2. Pasos de despliegue

```bash
# 1. En el VPS (como root), clonar el proyecto y entrar a deploy/
cd /opt/inmobi/deploy

# 2. Copiar y completar variables de entorno
cp .env.example .env
nano .env       # POSTGRES_PASSWORD, ODOO_ADMIN_PASSWD, SMTP_*, N8N_ENCRYPTION_KEY

# 3. Editar dominios reales en setup-vps.sh y nginx/nginx.conf
#    (reemplazar erp.tudominio.com por el dominio real)

# 4. Ejecutar el script de inicialización (instala Docker, certbot, levanta servicios)
bash setup-vps.sh
```

El script `setup-vps.sh`:
1. Actualiza el sistema.
2. Instala Docker + Docker Compose.
3. Configura el firewall.
4. Levanta los contenedores.
5. Solicita el certificado SSL con **certbot** (Let's Encrypt).
6. Habilita el proxy inverso Nginx.

### 5.3. SSL y Nginx

El `nginx.conf` redirige `:80 → :443`, sirve el reto ACME de certbot (`/.well-known/acme-challenge`) y termina el TLS con:
```
ssl_protocols TLSv1.2 TLSv1.3;
proxy_pass http://odoo;        # tráfico web
proxy_pass http://odoo-chat;   # websockets / longpolling
```

---

## 6. Configuración de integraciones (en Ajustes de Odoo)

| Integración | Dónde se configura | Credenciales necesarias |
|-------------|--------------------|--------------------------|
| Agente IA | Ajustes → Asistente IA | API key de Gemini u OpenAI; proveedor |
| WhatsApp | Ajustes → (Calendario) WhatsApp | Phone Number ID + Access Token (Meta) |
| WordPress | Ajustes → WordPress | URL, usuario y Application Password |
| Google Calendar | Ajustes → Calendario (Visitas) | Modo + ID de calendario + JSON de cuenta de servicio |

> **Robustez:** todas las llamadas externas están protegidas con manejo de errores; si un servicio falla, la operación interna de Odoo no se interrumpe.

---

## 7. Respaldos (backups)

Respaldo automático diario configurado vía cron del sistema:

```bash
# Script: scripts/backup_odoo.sh  (pg_dump + filestore en .zip, retención 14 días)
0 2 * * * /home/justin/Documentos/Tesis/scripts/backup_odoo.sh >> ~/odoo_backups/cron.log 2>&1
```

Restauración: `scripts/restore_odoo.sh <archivo.zip>`.

---

## 8. Mantenimiento y operación

| Tarea | Comando / acción |
|-------|------------------|
| Ver logs (producción) | `docker compose logs -f odoo` |
| Reiniciar Odoo | `docker compose restart odoo` |
| Actualizar módulo | `docker compose exec odoo odoo -u <modulo> -d <db> --stop-after-init` |
| Limpiar caché de assets | Eliminar adjuntos `ir.attachment` tipo `*.assets_*` y recargar con Ctrl+Shift+R |

### Tareas programadas (cron de Odoo)
- **Recordatorios de visita por WhatsApp** (1 h antes de la cita).
- **Alertas de vencimiento de contratos**.
- **Agente IA: alertas proactivas diarias**.

---

## 9. Seguridad

- Acceso por **roles y grupos** (`ir.model.access.csv` por módulo).
- **Bitácora de auditoría** (`estate_audit`) de operaciones crear/editar/eliminar.
- Credenciales sensibles (API keys, JSON de servicio) almacenadas en parámetros del sistema, **fuera del código fuente**.
- Cifrado **SSL/TLS** en el proxy inverso.

---

*Manual Técnico y de Despliegue — Proyecto de Titulación, UPS Sede Cuenca.*
