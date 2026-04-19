# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A modular ERP suite for real estate management built on **Odoo 19 Community Edition** (Python/PostgreSQL backend, OWL JavaScript frontend). This is a graduate thesis project ("Tesis de Grado").

## Running the Server

```bash
source /home/justin/Documentos/Tesis/venv19/bin/activate
python /home/justin/Documentos/odoo19/odoo-bin -c /home/justin/Documentos/Tesis/odoo19.conf
# Access at http://localhost:8070
```

Server config: [odoo19.conf](odoo19.conf) — port 8070, DB `tesis_odoo19`, .

## Installing/Updating Modules

```bash
# Install or update specific modules (--stop-after-init for one-shot execution)
python /home/justin/Documentos/odoo19/odoo-bin \
  -c /home/justin/Documentos/Tesis/odoo19.conf \
  -d tesis_odoo19 \
  -u estate_management,estate_crm \
  --stop-after-init

# Install all custom modules from scratch
python /home/justin/Documentos/odoo19/odoo-bin \
  -c /home/justin/Documentos/Tesis/odoo19.conf \
  -d tesis_odoo19 \
  -i estate_management,estate_crm,estate_reports,estate_ai_agent,estate_document,estate_calendar,estate_social,estate_portal,estate_wordpress \
  --stop-after-init
```

## Running Tests

Odoo's built-in test runner (no dedicated test files exist yet in custom modules):

```bash
python /home/justin/Documentos/odoo19/odoo-bin \
  -c /home/justin/Documentos/Tesis/odoo19.conf \
  -d tesis_odoo19 \
  --test-enable \
  --stop-after-init \
  -u estate_management
```

## Python Dependencies (beyond Odoo requirements)

```bash
pip install qrcode[pil] google-generativeai openai openpyxl psycopg2-binary requests
```

## Architecture

### Module Dependency Tree

```
estate_management  (core — properties, contracts, payments, commissions, AVM, QR codes)
├── estate_crm        (extends crm.lead — lead scoring, budget matching, AI negotiation tips)
├── estate_calendar   (extends calendar.event — visit tracking, WhatsApp reminders via Meta Cloud API)
├── estate_document   (document storage linked to properties/leads/contacts)
├── estate_reports    (KPI dashboard, PDF contracts, Excel export)
├── estate_social     (Facebook/WhatsApp/Twitter share buttons)
├── estate_wordpress  (auto-publish and sync properties to WordPress REST API)
├── estate_portal     (owner-facing portal/extranet)
└── estate_ai_agent   (AI chat via Google Gemini or OpenAI; OWL widget + REST controller)
```

### Core Data Model

**`estate.property`** — central entity:
- Location fields (street, city, state, lat/lng), physical attributes (area, bedrooms, etc.)
- State machine: `available → reserved → sold/rented`
- AVM (Automated Valuation Model): `avm_estimated_price`, `avm_status` (fair/high/low)
- Computed: `qr_image`, `days_on_market`, `meeting_count`
- Relations: `owner_id`, `buyer_id`, `user_id` (advisor)
- WordPress sync: `wp_published`, `wp_post_id`

**`crm.lead`** (extended) — adds `target_property_id`, `client_budget`, `match_percentage`, `lead_score` (A/B/C), `lead_temperature` (cold/warm/hot/boiling), `smart_negotiation_tips`.

**`calendar.event`** (extended) — adds `property_id`, `appointment_type`, `visit_state`, `visit_rating`, `whatsapp_sent`.

### AI Agent Module

`estate_ai_agent` exposes a REST endpoint (`/estate/ai/chat`) and two OWL components (`ai_chat`, `ai_chat_float`). The `EstateAIConfig` model stores provider credentials (Gemini/OpenAI) and the chat history lives in `EstateAIChat`.

### Key Patterns

- All custom models mixin `mail.thread` and `mail.activity.mixin` for chatter support.
- Each module follows standard Odoo layout: `models/`, `views/`, `security/`, `data/`, `report/`, `static/`, `controllers/`.
- WhatsApp reminders use a scheduled cron job (defined in `estate_calendar/data/`) that fires 1 hour before appointments via Meta WhatsApp Cloud API.
- Property creation triggers automatic CRM lead matching (≥95% budget match).
