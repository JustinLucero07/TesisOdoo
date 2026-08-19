# Inmobi App (Flutter)

App móvil (Android/iOS) para el mismo sistema Inmobi. No es un backend
aparte: habla directamente contra el Odoo existente (mismo login, misma
base de datos, mismos permisos por rol) vía el protocolo JSON-RPC que ya
usa el propio cliente web de Odoo — no requiere ningún módulo/endpoint
nuevo en el servidor.

## Qué hay hoy

5 secciones, con navegación inferior:

- **Inicio** (`lib/features/dashboard/`) — KPIs reales (disponibles, leads
  calientes, visitas de hoy, vendidas/arrendadas) y las visitas del día,
  con acceso directo a cada sección tocando una tarjeta.
- **Propiedades** (`lib/features/properties/`) — listado con miniatura,
  filtros por estado (disponible/reservada/vendida) y búsqueda; detalle con
  foto, precio, características y descripción.
- **CRM** (`lib/features/crm/`) — listado de leads (oportunidades) con
  filtro por temperatura (frío/tibio/caliente/hirviendo), puntuación A/B/C,
  % de coincidencia; detalle con botones directos de Llamar y WhatsApp.
- **Agenda** (`lib/features/visits/`) — franja de días + citas del día
  seleccionado (visitas, reuniones, llamadas, firmas), con estado
  (programada/realizada/cancelada); detalle de la cita.
- **Agente de IA** (`lib/features/chat/`) — chat conectado al endpoint de
  streaming ya existente (`/estate_ai/chat/stream`), el mismo que usa el
  chat flotante del ERP.

Login solo con usuario y contraseña — servidor y base de datos quedan
fijos en `lib/core/config.dart` (una sola vez para toda la empresa).

## Arquitectura

```
lib/
  core/
    api/odoo_client.dart      # cliente JSON-RPC genérico (login, call_kw)
    theme/app_theme.dart      # paleta navy/dorado, tipografía, tema Material 3
    widgets/                  # KpiCard, AppBadge, LoadingView, MessageView, InitialsAvatar
    config.dart                # servidor/base de datos fijos
  features/
    auth/                     # login + estado de sesión (Provider)
    dashboard/                # KPIs y resumen del día
    properties/                # modelo, servicio y pantallas
    crm/                        # leads: modelo, servicio y pantallas
    visits/                     # agenda/visitas: modelo, servicio y pantallas
    chat/                       # streaming SSE del agente de IA
    home/                        # shell con navegación inferior (5 tabs)
```

Cada `feature` sigue el mismo patrón: `*_model.dart` (mapea el JSON de
Odoo + estilos de badges), `*_service.dart` (llamadas ORM concretas), y
la(s) pantalla(s). Para agregar algo nuevo (contratos, documentos),
replicar ese patrón.

## Correr la app

```bash
flutter pub get
flutter run          # con un emulador/dispositivo Android conectado
# o, para probar rápido en escritorio Linux:
flutter run -d linux
```

## Pendiente (próximas iteraciones)

- **Crear/editar** desde la app (hoy es de solo lectura: propiedades, leads
  y visitas se consultan, no se crean ni editan desde el celular).
- **Persistir sesión** entre reinicios de la app (hoy pide login cada vez
  — es una simplificación deliberada del primer corte).
- **Compartir la ficha de propiedad** desde la app (ligado a la plantilla
  de WhatsApp `ficha_propiedad`, ver memoria del proyecto).
- **Notificaciones push** (recordatorios de visitas, leads calientes).
- Rendimiento de imágenes en el listado de propiedades: `image_main` es
  `fields.Binary` en el backend (no `fields.Image`), así que cada fila trae
  la imagen completa — funciona bien con 40 propiedades por página, pero si
  el catálogo crece mucho conviene agregar una miniatura computada en Odoo.
- Ícono y nombre de la app (hoy usa el placeholder de `flutter create`).
