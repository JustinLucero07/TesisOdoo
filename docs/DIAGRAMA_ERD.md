# Diagrama Entidad-Relación (ERD) y Diccionario de Datos

**Proyecto:** Sistema de gestión inmobiliaria sobre ERP Odoo 19 (PostgreSQL).
**Base de datos:** `tesis_odoo19` (PostgreSQL).

> El modelo se construye sobre entidades nativas de Odoo (`res.partner`, `res.users`, `crm.lead`, `calendar.event`, `account.move`) extendidas con entidades propias del dominio inmobiliario.

---

## 1. Diagrama Entidad-Relación (núcleo del dominio)

```mermaid
erDiagram
    RES_PARTNER  ||--o{ ESTATE_PROPERTY : "owner_id / buyer_id"
    RES_USERS    ||--o{ ESTATE_PROPERTY : "user_id (asesor)"
    ESTATE_PROPERTY_TYPE ||--o{ ESTATE_PROPERTY : "property_type_id"

    ESTATE_PROPERTY ||--o{ ESTATE_PROPERTY_IMAGE     : "image_ids"
    ESTATE_PROPERTY ||--o{ ESTATE_PROPERTY_OFFER     : "offer_ids"
    ESTATE_PROPERTY ||--o{ ESTATE_PROPERTY_EXPENSE   : "expense_ids"
    ESTATE_PROPERTY ||--o{ ESTATE_PROPERTY_PRICE_HISTORY : "price_history_ids"
    ESTATE_PROPERTY ||--o{ ESTATE_APPRAISAL          : "appraisal_ids"
    ESTATE_PROPERTY ||--o{ ESTATE_COMMISSION         : "commission_ids"
    ESTATE_PROPERTY }o--o{ ESTATE_PROPERTY_TAG       : "tag_ids"

    ESTATE_PROPERTY ||--o{ ESTATE_CONTRACT  : "property_id"
    ESTATE_CONTRACT ||--o{ ESTATE_PAYMENT   : "payment_ids"
    ESTATE_CONTRACT ||--o{ ESTATE_CONTRACT  : "parent/child_contract"
    ESTATE_PROPERTY_OFFER ||--o| ESTATE_CONTRACT : "offer_id"

    RES_PARTNER ||--o{ ESTATE_CONTRACT : "partner_id (cliente)"
    RES_PARTNER ||--o{ ESTATE_PAYMENT  : "partner_id"
    ACCOUNT_MOVE ||--o{ ESTATE_PAYMENT : "invoice_id"

    CRM_LEAD ||--o| ESTATE_PROPERTY : "target_property_id"
    CRM_LEAD ||--o{ ESTATE_CLIENT_INTERACTION : "interaction_ids"
    RES_PARTNER ||--o{ CRM_LEAD : "partner_id"

    ESTATE_PROPERTY ||--o{ CALENDAR_EVENT : "property_id"
    RES_PARTNER     ||--o{ CALENDAR_EVENT : "client_id"
    CRM_LEAD        ||--o{ CALENDAR_EVENT : "lead_id"

    ESTATE_PROPERTY ||--o{ ESTATE_DOCUMENT : "property_id"
    CRM_LEAD        ||--o{ ESTATE_DOCUMENT : "lead_id"
    ESTATE_DOCUMENT_TYPE ||--o{ ESTATE_DOCUMENT : "document_type_id"
```

---

## 2. Entidades de soporte (IA, auditoría, reportes)

```mermaid
erDiagram
    RES_USERS ||--o{ ESTATE_AI_CHAT_HISTORY : "user_id"
    ESTATE_AI_CHAT_HISTORY ||--o{ ESTATE_AI_MESSAGE : "message_ids"
    ESTATE_AI_CHAT_HISTORY ||--o{ ESTATE_AI_FEEDBACK : "voto"
    RES_USERS ||--o{ ESTATE_AUDIT_LOG : "user_id (autor del cambio)"
    RES_USERS ||--o{ ESTATE_DASHBOARD : "user_id"
    RES_USERS ||--o{ ESTATE_SALES_TARGET : "user_id (meta por asesor)"
```

---

## 3. Diccionario de datos (entidades principales)

### 3.1. `estate.property` — Propiedad

| Campo | Tipo | Descripción |
|-------|------|-------------|
| name | Char | Referencia interna (PROP-XXXX) |
| title | Char | Título comercial |
| description | Html | Descripción |
| property_type_id | Many2one → estate.property.type | Tipo (casa, departamento…) |
| offer_type | Selection | Venta / Arriendo |
| street, city, state_id, country_id, zip_code | Char/M2o | Ubicación |
| latitude, longitude | Float | Coordenadas GPS |
| price, bottom_price | Float | Precio publicado / mínimo |
| area, bedrooms, bathrooms, parking_spaces, floor, year_built | Float/Int | Atributos físicos |
| state | Selection | disponible / reservada / vendida / arrendada |
| avm_estimated_price, avm_status, avm_last_calculated | Float/Sel/Datetime | Valoración automática (AVM) |
| ai_vision_description | Text | Descripción generada por IA |
| owner_id, buyer_id | Many2one → res.partner | Propietario / comprador |
| user_id, co_user_id | Many2one → res.users | Asesor / co-asesor |
| tag_ids | Many2many → estate.property.tag | Etiquetas |
| wp_published, wp_post_id | Bool/Int | Estado de sincronización WordPress |

### 3.2. `estate.contract` — Contrato

| Campo | Tipo | Descripción |
|-------|------|-------------|
| name | Char | Número de contrato |
| property_id | Many2one → estate.property | Propiedad |
| partner_id | Many2one → res.partner | Cliente |
| user_id | Many2one → res.users | Asesor |
| offer_id | Many2one → estate.property.offer | Oferta origen |
| contract_type | Selection | Venta / Arriendo |
| date_start, date_end | Date | Vigencia |
| amount | Float | Monto |
| state | Selection | borrador / activo / suspendido / renovado / vencido / cancelado |
| parent_contract_id, child_contract_ids | M2o/O2m | Renovaciones encadenadas |
| payment_ids | One2many → estate.payment | Pagos |
| total_paid, payment_count | Float/Int | Saldos calculados |
| customer_signature, signed_contract | Binary | Firma y documento firmado |

### 3.3. `estate.payment` — Pago

| Campo | Tipo | Descripción |
|-------|------|-------------|
| name | Char | Referencia del pago |
| contract_id | Many2one → estate.contract | Contrato |
| property_id | Many2one → estate.property | Propiedad |
| partner_id | Many2one → res.partner | Pagador |
| amount | Float | Monto |
| date | Date | Fecha |
| payment_method | Selection | Método |
| state | Selection | Estado del pago |
| invoice_id | Many2one → account.move | Factura asociada |

### 3.4. `crm.lead` (extendido) — Lead / Oportunidad

| Campo | Tipo | Descripción |
|-------|------|-------------|
| target_property_id | Many2one → estate.property | Propiedad objetivo |
| client_budget | Float | Presupuesto del cliente |
| match_percentage | Integer | % de coincidencia con propiedades |
| preferred_property_type_id, preferred_city, preferred_bedrooms | M2o/Char/Int | Preferencias |
| lead_score | Selection | A / B / C |
| lead_temperature | Selection | frío / tibio / caliente / hirviendo |
| expected_revenue, expected_commission | Float | Proyección comercial |

### 3.5. `calendar.event` (extendido) — Visita / Cita

| Campo | Tipo | Descripción |
|-------|------|-------------|
| property_id | Many2one → estate.property | Propiedad a visitar |
| client_id | Many2one → res.partner | Cliente de la visita |
| lead_id | Many2one → crm.lead | Oportunidad de origen |
| appointment_type | Selection | Visita / Reunión / Llamada / Firma |
| visit_state | Selection | Programada / Realizada / Cancelada |
| visit_result, visit_rating | Selection | Resultado y calificación |
| whatsapp_sent, survey_sent | Boolean | Control de notificaciones |
| gcal_event_id | Char | ID del evento en Google Calendar compartido |

### 3.6. `estate.document` — Documento

| Campo | Tipo | Descripción |
|-------|------|-------------|
| property_id, lead_id, partner_id | Many2one | Vínculo del documento |
| document_type_id | Many2one → estate.document.type | Tipo de documento |
| ocr_result | Text | Texto extraído por OCR (Gemini Vision) |

---

## 4. Notas de diseño

- Todas las entidades del dominio heredan `mail.thread` y `mail.activity.mixin` (chatter, seguimiento y actividades).
- Las entidades con teléfono usan el mixin `estate.phone.mixin`; las que usan IA, el mixin `estate.genai.mixin`.
- La integridad referencial se gestiona con `ondelete` apropiado (ej. `estate.property.property_id` en visitas usa `set null` para no perder el historial).

---

*Diagrama ERD y diccionario de datos — Proyecto de Titulación, UPS Sede Cuenca.*
