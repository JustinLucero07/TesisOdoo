# -*- coding: utf-8 -*-
import json
import logging
import time

from datetime import datetime as _datetime, timedelta as _timedelta

from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from google import genai as new_genai
    NEW_GEMINI_SDK = True
except ImportError:
    NEW_GEMINI_SDK = False

GEMINI_AVAILABLE = NEW_GEMINI_SDK

# ---------------------------------------------------------------------------
# Tool definitions for OpenAI function calling
# ---------------------------------------------------------------------------
TOOLS_OPENAI = [
    {
        "type": "function",
        "function": {
            "name": "search_properties",
            "description": "Busca propiedades inmobiliarias en la base de datos según filtros.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "Ciudad de la propiedad"},
                    "property_type": {"type": "string", "description": "Tipo: casa, departamento, terreno, oficina"},
                    "max_price": {"type": "number", "description": "Precio máximo"},
                    "min_price": {"type": "number", "description": "Precio mínimo"},
                    "state": {"type": "string", "description": "Estado: available, sold, rented, reserved"},
                    "limit": {"type": "integer", "description": "Máximo de resultados (default 10)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_leads",
            "description": "Obtiene leads/oportunidades del CRM con sus datos y puntuación.",
            "parameters": {
                "type": "object",
                "properties": {
                    "temperature": {"type": "string", "description": "Filtrar por temperatura: cold, warm, hot, boiling"},
                    "score": {"type": "string", "description": "Filtrar por puntuación: low, medium, high"},
                    "limit": {"type": "integer", "description": "Máximo de resultados (default 10)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_market_stats",
            "description": "Obtiene estadísticas del mercado inmobiliario: precio promedio, días en mercado, ventas por ciudad/tipo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "Ciudad para filtrar estadísticas"},
                    "property_type": {"type": "string", "description": "Tipo de propiedad para filtrar"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_crm_activity",
            "description": "Crea una actividad de seguimiento en un lead del CRM.",
            "parameters": {
                "type": "object",
                "required": ["lead_id", "note"],
                "properties": {
                    "lead_id": {"type": "integer", "description": "ID del lead en el CRM"},
                    "summary": {"type": "string", "description": "Resumen corto de la actividad"},
                    "note": {"type": "string", "description": "Nota detallada de la actividad"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_lead",
            "description": "Crea un nuevo lead/oportunidad en el CRM.",
            "parameters": {
                "type": "object",
                "required": ["name", "contact_name"],
                "properties": {
                    "name": {"type": "string", "description": "Título del lead (ej: 'Busca casa en Cuenca')"},
                    "contact_name": {"type": "string", "description": "Nombre del cliente/prospecto"},
                    "email": {"type": "string", "description": "Email del cliente"},
                    "mobile": {"type": "string", "description": "Teléfono móvil del cliente"},
                    "client_budget": {"type": "number", "description": "Presupuesto disponible del cliente"},
                    "offer_type": {"type": "string", "description": "Tipo de oferta buscada: sale o rent"},
                    "city": {"type": "string", "description": "Ciudad donde busca propiedad"},
                    "notes": {"type": "string", "description": "Notas adicionales sobre el lead"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_property",
            "description": "Registra una nueva propiedad inmobiliaria en el sistema.",
            "parameters": {
                "type": "object",
                "required": ["title", "city", "price"],
                "properties": {
                    "title": {"type": "string", "description": "Título descriptivo de la propiedad"},
                    "city": {"type": "string", "description": "Ciudad donde está la propiedad"},
                    "price": {"type": "number", "description": "Precio de venta o alquiler"},
                    "area": {"type": "number", "description": "Área en metros cuadrados"},
                    "bedrooms": {"type": "integer", "description": "Número de habitaciones"},
                    "bathrooms": {"type": "integer", "description": "Número de baños"},
                    "offer_type": {"type": "string", "description": "Tipo: sale (venta) o rent (arriendo)"},
                    "street": {"type": "string", "description": "Dirección de la calle"},
                    "description": {"type": "string", "description": "Descripción de la propiedad"},
                    "property_type": {"type": "string", "description": "Tipo: casa, departamento, terreno, oficina, local"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_lead",
            "description": "Actualiza datos de un lead existente: etapa, temperatura, propiedad asignada, notas.",
            "parameters": {
                "type": "object",
                "required": ["lead_id"],
                "properties": {
                    "lead_id": {"type": "integer", "description": "ID del lead a actualizar"},
                    "stage_name": {"type": "string", "description": "Nueva etapa (ej: 'Negociación/Oferta')"},
                    "temperature": {"type": "string", "description": "Nueva temperatura: cold, warm, hot, boiling"},
                    "property_id": {"type": "integer", "description": "ID de la propiedad objetivo a asignar"},
                    "client_budget": {"type": "number", "description": "Nuevo presupuesto del cliente"},
                    "notes": {"type": "string", "description": "Nota o comentario a agregar al chatter"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_property",
            "description": "Actualiza CUALQUIER dato de una propiedad: precio, descripción, estado, habitaciones, área, tipo, propietario, asesor, coordenadas, etc.",
            "parameters": {
                "type": "object",
                "required": ["property_id"],
                "properties": {
                    "property_id": {"type": "integer", "description": "ID de la propiedad a actualizar"},
                    "price": {"type": "number", "description": "Nuevo precio"},
                    "description": {"type": "string", "description": "Nueva descripción"},
                    "title": {"type": "string", "description": "Nuevo título"},
                    "state": {"type": "string", "description": "Nuevo estado: available, reserved, sold, rented"},
                    "bedrooms": {"type": "integer", "description": "Número de habitaciones"},
                    "bathrooms": {"type": "integer", "description": "Número de baños"},
                    "area": {"type": "number", "description": "Área en m²"},
                    "street": {"type": "string", "description": "Dirección/calle"},
                    "city": {"type": "string", "description": "Ciudad"},
                    "offer_type": {"type": "string", "description": "Tipo de operación: sale o rent"},
                    "property_type": {"type": "string", "description": "Tipo de propiedad: casa, departamento, terreno, oficina"},
                    "owner_name": {"type": "string", "description": "Nombre del propietario (res.partner)"},
                    "advisor_name": {"type": "string", "description": "Nombre del asesor/agente responsable"},
                    "latitude": {"type": "number", "description": "Latitud GPS"},
                    "longitude": {"type": "number", "description": "Longitud GPS"},
                    "notes": {"type": "string", "description": "Nota a agregar al historial de la propiedad"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_property_detail",
            "description": "Obtiene el detalle completo de una propiedad: todos sus campos, propietario, asesor, estado, valoración AVM, coordenadas. Úsalo cuando el usuario pregunte por UNA propiedad específica.",
            "parameters": {
                "type": "object",
                "properties": {
                    "property_id": {"type": "integer", "description": "ID de la propiedad"},
                    "property_name": {"type": "string", "description": "Nombre, referencia o título parcial de la propiedad (si no se sabe el ID)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_property",
            "description": "ELIMINA PERMANENTEMENTE una propiedad del sistema. SOLO usar cuando el usuario haya confirmado explícitamente con 'sí confirmo'. Esta acción es IRREVERSIBLE.",
            "parameters": {
                "type": "object",
                "required": ["property_id"],
                "properties": {
                    "property_id": {"type": "integer", "description": "ID de la propiedad a eliminar"},
                    "confirmed": {"type": "boolean", "description": "Debe ser true, indica que el usuario confirmó la eliminación"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "duplicate_property",
            "description": "Duplica una propiedad existente como borrador para crear una nueva similar.",
            "parameters": {
                "type": "object",
                "required": ["property_id"],
                "properties": {
                    "property_id": {"type": "integer", "description": "ID de la propiedad a duplicar"},
                    "new_title": {"type": "string", "description": "Título para la copia (opcional)"},
                    "new_price": {"type": "number", "description": "Precio de la copia (opcional, si no se indica hereda el mismo)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_visit",
            "description": "Agenda una visita a una propiedad para un cliente/lead.",
            "parameters": {
                "type": "object",
                "required": ["property_id", "start_datetime", "partner_name"],
                "properties": {
                    "property_id": {"type": "integer", "description": "ID de la propiedad a visitar"},
                    "start_datetime": {"type": "string", "description": "Fecha y hora de la visita: YYYY-MM-DD HH:MM"},
                    "partner_name": {"type": "string", "description": "Nombre del cliente que visita"},
                    "notes": {"type": "string", "description": "Notas adicionales sobre la visita"},
                    "lead_id": {"type": "integer", "description": "ID del lead relacionado (opcional)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reserve_property",
            "description": "Marca una propiedad como reservada y la asigna a un comprador.",
            "parameters": {
                "type": "object",
                "required": ["property_id"],
                "properties": {
                    "property_id": {"type": "integer", "description": "ID de la propiedad a reservar"},
                    "buyer_name": {"type": "string", "description": "Nombre del comprador/arrendatario"},
                    "notes": {"type": "string", "description": "Notas sobre la reserva"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sell_property",
            "description": "Cierra una propiedad como vendida o alquilada.",
            "parameters": {
                "type": "object",
                "required": ["property_id", "close_type"],
                "properties": {
                    "property_id": {"type": "integer", "description": "ID de la propiedad"},
                    "close_type": {"type": "string", "description": "Tipo de cierre: sold (vendida) o rented (alquilada)"},
                    "final_price": {"type": "number", "description": "Precio final de cierre (opcional)"},
                    "notes": {"type": "string", "description": "Notas del cierre"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_whatsapp_lead",
            "description": "Genera un enlace de WhatsApp para contactar al cliente de un lead.",
            "parameters": {
                "type": "object",
                "required": ["lead_id"],
                "properties": {
                    "lead_id": {"type": "integer", "description": "ID del lead cuyo cliente se quiere contactar"},
                    "message": {"type": "string", "description": "Mensaje personalizado para enviar al cliente"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "archive_lead",
            "description": "Archiva o marca como perdido un lead del CRM.",
            "parameters": {
                "type": "object",
                "required": ["lead_id"],
                "properties": {
                    "lead_id": {"type": "integer", "description": "ID del lead a archivar"},
                    "reason": {"type": "string", "description": "Razón del archivo/pérdida"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_payments_contracts",
            "description": "Obtiene pagos vencidos, facturas pendientes y contratos próximos a vencer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days_ahead": {"type": "integer", "description": "Días hacia adelante para revisar contratos (default 30)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_dashboard_summary",
            "description": "Genera un resumen ejecutivo diario completo: propiedades, leads, visitas, ingresos, alertas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "period": {"type": "string", "description": "Período: today, week, month (default month)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_report_data",
            "description": (
                "Obtiene datos agregados para generar reportes visuales (gráficos y tablas). "
                "Úsala cuando el usuario pida un reporte, gráfico o análisis de: "
                "propiedades, contratos, pagos, ofertas, gastos, visitas, comisiones, leads."
            ),
            "parameters": {
                "type": "object",
                "required": ["report_type"],
                "properties": {
                    "report_type": {
                        "type": "string",
                        "description": (
                            "Tipo de reporte: "
                            "properties_by_state | properties_by_type | sales_by_month | "
                            "visits_by_property | commissions_by_advisor | contracts_by_type | "
                            "expenses_by_type | offers_by_state | leads_by_temperature | "
                            "payments_by_method | days_on_market_by_type"
                        ),
                    },
                    "limit": {"type": "integer", "description": "Máximo de ítems a retornar (default 8)"},
                },
            },
        },
    },
    # ── A1: CRUD Contratos / Pagos / Comisiones / Ofertas ─────────────────
    {"type": "function", "function": {
        "name": "create_contract",
        "description": "Crea un contrato inmobiliario vinculado a una propiedad y un cliente.",
        "parameters": {"type": "object", "required": ["property_id", "partner_name", "contract_type", "amount"], "properties": {
            "property_id":    {"type": "integer", "description": "ID de la propiedad"},
            "partner_name":   {"type": "string",  "description": "Nombre del cliente"},
            "contract_type":  {"type": "string",  "description": "Tipo: sale, rent, exclusive"},
            "amount":         {"type": "number",  "description": "Monto del contrato"},
            "date_start":     {"type": "string",  "description": "Fecha inicio YYYY-MM-DD (default hoy)"},
            "date_end":       {"type": "string",  "description": "Fecha fin YYYY-MM-DD (solo arriendos)"},
            "notes":          {"type": "string",  "description": "Cláusulas o notas adicionales"},
        }},
    }},
    {"type": "function", "function": {
        "name": "update_contract",
        "description": "Activa, cancela o actualiza un contrato inmobiliario existente.",
        "parameters": {"type": "object", "required": ["contract_id", "action"], "properties": {
            "contract_id": {"type": "integer", "description": "ID del contrato"},
            "action":      {"type": "string",  "description": "activate | cancel | expire"},
            "amount":      {"type": "number",  "description": "Nuevo monto (opcional)"},
            "notes":       {"type": "string",  "description": "Nota a registrar en el chatter"},
        }},
    }},
    {"type": "function", "function": {
        "name": "create_payment",
        "description": "Registra un pago inmobiliario (cuota) en un contrato.",
        "parameters": {"type": "object", "required": ["contract_id", "amount"], "properties": {
            "contract_id":     {"type": "integer", "description": "ID del contrato"},
            "amount":          {"type": "number",  "description": "Monto del pago"},
            "payment_method":  {"type": "string",  "description": "cash | bank | check | card | other"},
            "date":            {"type": "string",  "description": "Fecha YYYY-MM-DD (default hoy)"},
            "notes":           {"type": "string",  "description": "Observaciones"},
        }},
    }},
    {"type": "function", "function": {
        "name": "approve_payment",
        "description": "Marca como PAGADO un pago inmobiliario (estate.payment) pendiente.",
        "parameters": {"type": "object", "required": ["payment_id"], "properties": {
            "payment_id": {"type": "integer", "description": "ID del pago a aprobar"},
        }},
    }},
    {"type": "function", "function": {
        "name": "create_offer",
        "description": "Registra una oferta de compra sobre una propiedad.",
        "parameters": {"type": "object", "required": ["property_id", "partner_name", "offer_amount"], "properties": {
            "property_id":    {"type": "integer", "description": "ID de la propiedad"},
            "partner_name":   {"type": "string",  "description": "Nombre del comprador"},
            "offer_amount":   {"type": "number",  "description": "Monto ofertado"},
            "financing_type": {"type": "string",  "description": "cash | mortgage | owner | other"},
            "notes":          {"type": "string",  "description": "Observaciones"},
        }},
    }},
    {"type": "function", "function": {
        "name": "create_commission",
        "description": "Registra una comisión inmobiliaria para un asesor.",
        "parameters": {"type": "object", "required": ["property_id", "agent_name", "amount"], "properties": {
            "property_id":      {"type": "integer", "description": "ID de la propiedad"},
            "agent_name":       {"type": "string",  "description": "Nombre del asesor"},
            "amount":           {"type": "number",  "description": "Monto de la comisión"},
            "commission_type":  {"type": "string",  "description": "sale | rental | bonus"},
            "date":             {"type": "string",  "description": "Fecha YYYY-MM-DD"},
        }},
    }},
    {"type": "function", "function": {
        "name": "approve_commission",
        "description": "Aprueba o marca como pagada una comisión inmobiliaria.",
        "parameters": {"type": "object", "required": ["commission_id", "action"], "properties": {
            "commission_id": {"type": "integer", "description": "ID de la comisión"},
            "action":        {"type": "string",  "description": "approve (→ Aprobada) | pay (→ Pagada)"},
        }},
    }},
    # ── A2: Generar PDF ───────────────────────────────────────────────────
    {"type": "function", "function": {
        "name": "generate_pdf_report",
        "description": "Genera un PDF del sistema y devuelve un enlace de descarga directo.",
        "parameters": {"type": "object", "required": ["report_type", "record_id"], "properties": {
            "report_type": {"type": "string", "description": "ficha_propiedad | estado_cuenta_contrato | cotizacion_lead | comisiones_wizard"},
            "record_id":   {"type": "integer", "description": "ID del registro (propiedad, contrato o lead)"},
        }},
    }},
    # ── A4: Archivar ─────────────────────────────────────────────────────
    {"type": "function", "function": {
        "name": "archive_property",
        "description": "Archiva (desactiva) una propiedad del catálogo.",
        "parameters": {"type": "object", "required": ["property_id"], "properties": {
            "property_id": {"type": "integer", "description": "ID de la propiedad"},
            "reason":      {"type": "string",  "description": "Motivo del archivado"},
        }},
    }},
    {"type": "function", "function": {
        "name": "cancel_payment",
        "description": "Cancela/anula un pago inmobiliario registrado por error.",
        "parameters": {"type": "object", "required": ["payment_id"], "properties": {
            "payment_id": {"type": "integer", "description": "ID del pago a cancelar"},
            "reason":     {"type": "string",  "description": "Motivo de la cancelación"},
        }},
    }},
    # ── A5: Lote ──────────────────────────────────────────────────────────
    {"type": "function", "function": {
        "name": "batch_update_properties",
        "description": "Actualiza en lote propiedades que cumplan filtros (máx 50). Ideal para ajustes masivos de precio o estado.",
        "parameters": {"type": "object", "properties": {
            "city":          {"type": "string",  "description": "Filtrar por ciudad"},
            "state_filter":  {"type": "string",  "description": "Estado actual: available | reserved | sold | rented"},
            "new_price_pct": {"type": "number",  "description": "Ajuste % de precio (ej: -5 = bajar 5%)"},
            "new_state":     {"type": "string",  "description": "Nuevo estado a asignar"},
            "notes":         {"type": "string",  "description": "Nota para el chatter de cada propiedad"},
        }},
    }},
    {"type": "function", "function": {
        "name": "batch_archive_leads",
        "description": "Archiva en lote leads fríos o inactivos según criterios.",
        "parameters": {"type": "object", "properties": {
            "temperature":    {"type": "string",  "description": "Archivar leads con temperatura: cold | warm"},
            "days_inactive":  {"type": "integer", "description": "Archivar leads sin actividad en X días"},
            "reason":         {"type": "string",  "description": "Motivo del archivado"},
        }},
    }},
    # ── A6: Email ─────────────────────────────────────────────────────────
    {"type": "function", "function": {
        "name": "send_email",
        "description": "Envía un email a un cliente o contacto desde el sistema.",
        "parameters": {"type": "object", "required": ["subject", "body"], "properties": {
            "partner_name": {"type": "string", "description": "Nombre del destinatario (busca en contactos)"},
            "email_to":     {"type": "string", "description": "Email directo del destinatario"},
            "subject":      {"type": "string", "description": "Asunto del correo"},
            "body":         {"type": "string", "description": "Cuerpo del correo"},
        }},
    }},
    # ── B1: Lead Scoring IA ───────────────────────────────────────────────
    {"type": "function", "function": {
        "name": "analyze_lead_probability",
        "description": "Analiza con IA la probabilidad de cierre de un lead versus histórico de ventas.",
        "parameters": {"type": "object", "required": ["lead_id"], "properties": {
            "lead_id": {"type": "integer", "description": "ID del lead a analizar"},
        }},
    }},
    # ── B2: Churn ─────────────────────────────────────────────────────────
    {"type": "function", "function": {
        "name": "analyze_churn_risk",
        "description": "Detecta contratos/inquilinos con alto riesgo de no renovar.",
        "parameters": {"type": "object", "properties": {
            "days_to_expiry": {"type": "integer", "description": "Analizar contratos que vencen en X días (default 60)"},
        }},
    }},
    # ── B3: AVM IA ────────────────────────────────────────────────────────
    {"type": "function", "function": {
        "name": "recalculate_avm_ai",
        "description": "Recalcula el valor de mercado de una propiedad usando IA y comparables.",
        "parameters": {"type": "object", "required": ["property_id"], "properties": {
            "property_id": {"type": "integer", "description": "ID de la propiedad"},
        }},
    }},
    # ── B4: Descripción + WP ──────────────────────────────────────────────
    {"type": "function", "function": {
        "name": "generate_and_apply_description",
        "description": "Genera descripción de marketing para una propiedad, opcionalmente la guarda y/o publica en WordPress.",
        "parameters": {"type": "object", "required": ["property_id"], "properties": {
            "property_id": {"type": "integer", "description": "ID de la propiedad"},
            "style":       {"type": "string",  "description": "formal | emocional | directo"},
            "apply":       {"type": "boolean", "description": "Si True, guarda la descripción"},
            "publish_wp":  {"type": "boolean", "description": "Si True, publica en WordPress"},
        }},
    }},
    # ── B5: Memoria persistente ───────────────────────────────────────────
    {"type": "function", "function": {
        "name": "save_memory",
        "description": "Guarda un hecho, preferencia o dato importante para recordar en futuras conversaciones.",
        "parameters": {"type": "object", "required": ["content"], "properties": {
            "content":     {"type": "string", "description": "Hecho o preferencia a recordar"},
            "memory_type": {"type": "string", "description": "preference | fact | client | alert"},
        }},
    }},
    {"type": "function", "function": {
        "name": "recall_memory",
        "description": "Recupera memorias guardadas sobre el negocio, clientes o preferencias del usuario.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "Qué buscar (vacío = devuelve todo)"},
        }},
    }},
    # ── C1: Búsqueda de Contactos ─────────────────────────────────────────
    {"type": "function", "function": {
        "name": "search_contacts",
        "description": "Busca clientes/contactos en el sistema por nombre, email, teléfono o empresa. Devuelve su historial de leads y contratos.",
        "parameters": {"type": "object", "properties": {
            "query":        {"type": "string",  "description": "Nombre, email o teléfono a buscar"},
            "has_contracts": {"type": "boolean", "description": "Si True, solo contactos con contratos activos"},
            "limit":        {"type": "integer", "description": "Máximo de resultados (default 10)"},
        }},
    }},
    # ── C2: Comparar Propiedades ──────────────────────────────────────────
    {"type": "function", "function": {
        "name": "compare_properties",
        "description": "Compara dos o más propiedades lado a lado: precio, área, habitaciones, días en mercado, AVM, etc.",
        "parameters": {"type": "object", "required": ["property_ids"], "properties": {
            "property_ids": {"type": "array", "items": {"type": "integer"}, "description": "Lista de IDs de propiedades a comparar (mín 2)"},
        }},
    }},
    # ── C3: Análisis de Tendencias ────────────────────────────────────────
    {"type": "function", "function": {
        "name": "get_trend_analysis",
        "description": "Compara métricas del período actual vs período anterior: ventas, leads generados, ingresos, tiempo en mercado. Detecta tendencias positivas/negativas.",
        "parameters": {"type": "object", "properties": {
            "metric":  {"type": "string", "description": "sales | leads | revenue | days_on_market | all (default all)"},
            "period":  {"type": "string", "description": "month | quarter | year (default month)"},
        }},
    }},
    # ── C4: Próximas Visitas ──────────────────────────────────────────────
    {"type": "function", "function": {
        "name": "get_upcoming_visits",
        "description": "Lista las visitas/citas programadas en el calendario inmobiliario para los próximos días.",
        "parameters": {"type": "object", "properties": {
            "days_ahead": {"type": "integer", "description": "Días hacia adelante (default 7)"},
            "advisor_name": {"type": "string", "description": "Filtrar por nombre de asesor (opcional)"},
        }},
    }},
    # ── C5: Resumen de Cliente ─────────────────────────────────────────────
    {"type": "function", "function": {
        "name": "get_client_summary",
        "description": "Genera un perfil 360° de un cliente: leads activos, contratos, pagos pendientes, visitas, historial de interacciones.",
        "parameters": {"type": "object", "required": ["partner_name"], "properties": {
            "partner_name": {"type": "string", "description": "Nombre (parcial) del cliente"},
            "partner_id":   {"type": "integer", "description": "ID del contacto (si se conoce)"},
        }},
    }},
    # ── C6: Cotización PDF ────────────────────────────────────────────────
    {"type": "function", "function": {
        "name": "generate_quote_pdf",
        "description": "Genera una cotización en PDF para un cliente con detalles de una propiedad específica.",
        "parameters": {"type": "object", "required": ["lead_id"], "properties": {
            "lead_id":     {"type": "integer", "description": "ID del lead para el que se genera la cotización"},
            "property_id": {"type": "integer", "description": "ID de la propiedad a cotizar (opcional, usa la asignada al lead)"},
        }},
    }},
    # ── HERRAMIENTA UNIVERSAL: Consulta SQL directa (solo lectura) ─────────
    {"type": "function", "function": {
        "name": "query_database",
        "description": (
            "Ejecuta una consulta SQL de SOLO LECTURA contra la base de datos para responder "
            "CUALQUIER pregunta sobre el sistema. Usa esta herramienta cuando ninguna otra "
            "herramienta específica pueda responder la pregunta del usuario. "
            "COLUMNAS PRINCIPALES DE CADA TABLA: "
            "estate_property: id, name(referencia), title, price, area, bedrooms, bathrooms, "
            "parking_spaces, floor, year_built, city, street, state(selection: available/reserved/sold/rented), "
            "offer_type(sale/rent), property_type_id(FK→estate_property_type.id), "
            "user_id(FK→res_users.id = asesor), owner_id(FK→res_partner.id), "
            "buyer_id(FK→res_partner.id), date_listed, date_sold, days_on_market, "
            "commission_percentage, commission_amount, avm_estimated_price, avm_status. "
            "estate_property_type: id, name. "
            "estate_property_tag: id, name, color. "
            "crm_lead: id, name, contact_name, email_from, phone, type(lead/opportunity), "
            "user_id(FK→res_users.id), partner_id(FK→res_partner.id), "
            "stage_id(FK→crm_stage.id), probability, expected_revenue. "
            "estate_contract: id, name, property_id, partner_id, user_id, contract_type(sale/rent/exclusive), "
            "amount, state(draft/active/expired/cancelled), date_start, date_end. "
            "estate_payment: id, contract_id, amount, state(pending/paid/cancelled), "
            "payment_method, payment_date. "
            "estate_commission: id, property_id, user_id, amount, commission_type, state. "
            "estate_property_offer: id, property_id, partner_id, offer_amount, state, date. "
            "estate_property_expense: id, property_id, amount, expense_type, state. "
            "calendar_event: id, name, start, stop, property_id, user_id. "
            "res_partner: id, name, email, phone, city, is_company. "
            "res_users: id, login, partner_id(FK→res_partner.id). "
            "REGLA CRÍTICA SOBRE res_users: res_users NO TIENE columna 'name'. "
            "Para obtener el nombre de un usuario SIEMPRE haz JOIN con res_partner: "
            "JOIN res_users ru ON ... JOIN res_partner rp ON ru.partner_id = rp.id, "
            "y usa rp.name para el nombre del usuario/asesor. "
            "REGLA CRÍTICA SOBRE property_type: estate_property NO TIENE columna 'property_type'. "
            "Usa property_type_id y haz JOIN con estate_property_type para obtener el nombre: "
            "JOIN estate_property_type ept ON ep.property_type_id = ept.id, y usa ept.name. "
            "SOLO SELECT permitido. Limita siempre a máximo 50 filas."
        ),
        "parameters": {"type": "object", "required": ["sql"], "properties": {
            "sql": {"type": "string", "description": "Consulta SQL SELECT (solo lectura, máx 50 filas)"},
            "explanation": {"type": "string", "description": "Breve explicación de qué busca esta consulta"},
        }},
    }},
]


# ── Destructive actions that require user confirmation ─────────────────────
DESTRUCTIVE_TOOLS = {
    'sell_property', 'reserve_property', 'archive_lead', 'archive_property',
    'cancel_payment', 'update_contract', 'batch_archive_leads', 'batch_update_properties',
}


# ── Modelos Gemini válidos en la API pública ──────────────────────────────────
_VALID_GEMINI_MODELS = {
    'gemini-2.5-flash', 'gemini-2.5-pro-preview-03-25',
    'gemini-1.5-flash', 'gemini-1.5-flash-8b', 'gemini-1.5-pro',
}

# Modelo por defecto (el más rápido y económico disponible)
_DEFAULT_GEMINI_MODEL = 'gemini-2.5-flash'

def _normalize_gemini_model(model):
    """Return a valid Gemini model name. Falls back to gemini-2.5-flash for invalid names."""
    if not model:
        return _DEFAULT_GEMINI_MODEL
    model = model.replace('models/', '').strip()
    if model in _VALID_GEMINI_MODELS:
        return model
    # Map old/deprecated aliases to current models
    _aliases = {
        'gemini-flash': _DEFAULT_GEMINI_MODEL,
        'gemini-flash-latest': _DEFAULT_GEMINI_MODEL,
        'gemini-2.0-flash': _DEFAULT_GEMINI_MODEL,
        'gemini-2.0-flash-lite': _DEFAULT_GEMINI_MODEL,
        'gemini-2.0-flash-exp': _DEFAULT_GEMINI_MODEL,
        'gemini-pro': 'gemini-1.5-pro',
    }
    if model in _aliases:
        return _aliases[model]
    # Unknown model — log and fallback
    _logger.warning("Modelo Gemini desconocido: '%s'. Usando %s.", model, _DEFAULT_GEMINI_MODEL)
    return _DEFAULT_GEMINI_MODEL


def _parse_gemini_error(err_str):
    """
    Parse a Gemini API error string and return (error_type, message, retry_seconds).
    error_type: '429' | '503' | 'other'
    """
    import re
    if '429' in err_str or 'RESOURCE_EXHAUSTED' in err_str:
        # Extract retry delay if present ("retry in 13s" or "retryDelay: 13s")
        match = re.search(r'retry[^\d]*(\d+)', err_str, re.IGNORECASE)
        secs = int(match.group(1)) + 2 if match else 60
        # Quota type
        if 'free_tier' in err_str or 'FreeTier' in err_str:
            msg = (
                f'⚠️ **Cuota gratuita agotada** — el plan gratuito de Gemini solo permite '
                f'**20 requests/día**.\n\n'
                f'**Opciones:**\n'
                f'- Espera ~{secs}s e intenta de nuevo\n'
                f'- Activa facturación en [Google AI Studio](https://aistudio.google.com) '
                f'para límites mayores (~$0.10/millón de tokens)\n'
                f'- O usa OpenAI GPT-4o Mini (más estable): cambia el proveedor en '
                f'**Ajustes → Agente IA**'
            )
        else:
            msg = (
                f'⚠️ **Límite de requests alcanzado** (429). '
                f'Espera {secs} segundos e intenta de nuevo.'
            )
        return '429', msg, secs
    if '503' in err_str or 'UNAVAILABLE' in err_str or 'high demand' in err_str:
        return '503', None, None
    return 'other', None, None


class EstateAIController(http.Controller):

    @http.route('/estate_ai/chat', type='jsonrpc', auth='user', methods=['POST'])
    def chat(self, message, **kwargs):
        """Process a chat message and return AI response with memory and tool calling."""
        start_time = time.time()

        ICP = request.env['ir.config_parameter'].sudo()
        ai_active = ICP.get_param('estate_ai.active', 'True')
        if ai_active != 'True':
            return {'response': '⚠️ El agente IA está desactivado. Contacte al administrador.'}

        provider = ICP.get_param('estate_ai.provider', 'chatgpt')
        api_key = ICP.get_param('estate_ai.api_key', '')
        model = _normalize_gemini_model(ICP.get_param('estate_ai.model', ''))
        
        temperature = float(ICP.get_param('estate_ai.temperature', '0.7'))
        max_tokens = int(ICP.get_param('estate_ai.max_tokens', '1500'))
        system_prompt = ICP.get_param('estate_ai.system_prompt', '')

        if not api_key:
            return {'response': '⚠️ No se ha configurado la API Key. Vaya a Configuración > Agente IA.'}

        context_data = self._get_system_context()
        user_lang = request.env.user.lang or 'es_EC'
        lang_instruction = "Responde SIEMPRE en español, a menos que el usuario escriba en otro idioma."
        if user_lang.startswith('en'):
            lang_instruction = "Respond in English unless the user writes in another language."
        elif user_lang.startswith('pt'):
            lang_instruction = "Responda sempre em Português, a menos que o usuário escreva em outro idioma."

        # Inject persistent memories (B5)
        memories_text = ''
        try:
            memories = request.env['estate.ai.memory'].sudo().get_active_memories_for_user(
                request.env.user.id, limit=15
            )
            if memories:
                mem_lines = [f"- [{m['memory_type']}] {m['title']}: {m['content']}" for m in memories]
                memories_text = "\nMEMORIAS PERSISTENTES DEL USUARIO:\n" + "\n".join(mem_lines) + "\n"
        except Exception:
            pass

        full_system_prompt = f"""{system_prompt}

{lang_instruction}

Eres el Asistente Ejecutivo Inteligente de la Inmobiliaria. Tienes acceso COMPLETO al sistema.
TU MISIÓN: Consultar, crear, actualizar y controlar el sistema inmobiliario desde esta conversación.

REGLA ABSOLUTA: NUNCA digas 'no puedo', 'no tengo la capacidad', 'no tengo acceso' o 'no es posible'.
Tienes la herramienta query_database que te permite ejecutar CUALQUIER consulta SQL SELECT
contra toda la base de datos. Si ninguna otra herramienta sirve, usa query_database con un SQL
apropiado. Tienes acceso a TODA la información del sistema sin excepción.

DATOS ACTUALES DEL SISTEMA:
{context_data}
{memories_text}
CAPACIDADES COMPLETAS (usa las herramientas):
- CONSULTAR: buscar propiedades, ver leads, estadísticas de mercado, pagos vencidos, resumen ejecutivo
- CLIENTES: search_contacts (busca por nombre/email/tel), get_client_summary (perfil 360°)
- ANALÍTICA: get_trend_analysis (tendencias período actual vs anterior), compare_properties (comparativa)
- CALENDARIO: get_upcoming_visits (próximas visitas), schedule_visit (agendar)
- CREAR: leads, propiedades, contratos, pagos, ofertas, comisiones, actividades
- ACTUALIZAR: precio/descripción/estado de propiedades, etapa/temperatura/presupuesto de leads
- GESTIONAR: reservar/vender propiedades, archivar leads, generar links de WhatsApp, enviar emails
- IA AVANZADA: analizar probabilidad de cierre, riesgo de churn, recalcular AVM, generar descripciones
- MEMORIA: guardar preferencias/hechos con save_memory, consultar con recall_memory
- REPORTES PDF: generate_pdf_report | generate_quote_pdf (cotización para cliente)
- SQL DIRECTO: query_database — ejecuta cualquier SELECT contra la BD para responder lo que sea
- OPERACIONES MASIVAS: batch_update_properties, batch_archive_leads

DETECCIÓN DE INTENCIÓN — actúa directamente según lo que el usuario quiera:
- "busca/encuentra/muéstrame [cliente/contacto]" → usa search_contacts
- "compara propiedad X con Y" → usa compare_properties con los IDs
- "cómo vamos este mes/trimestre" → usa get_trend_analysis
- "visitas de esta semana/próximos días" → usa get_upcoming_visits
- "resumen de cliente/perfil de [nombre]" → usa get_client_summary
- "cotización para [lead]" → usa generate_quote_pdf
- "briefing/resumen del día" → usa get_dashboard_summary + get_upcoming_visits + get_trend_analysis
- "reporte de [tema]" → usa get_report_data con el report_type correcto

ASISTENTE DE NEGOCIACIÓN:
Cuando un cliente haga una oferta o pregunte por precio, analiza:
1. Llama recalculate_avm_ai para obtener el valor de mercado actualizado
2. Compara la oferta con el AVM: si oferta < 90% del AVM, sugiere contraoferta en 95%
3. Si avm_status='low' (propiedad sobrevaluada), da argumentos para aceptar rebajas moderadas
4. Si avm_status='high' (propiedad subvaluada), recomienda mantener el precio o subirlo
5. Siempre termina con 3 puntos de negociación concretos

INSTRUCCIONES DE RESPUESTA:
1. Sé proactivo: si el usuario dice "crea un lead para Juan", HAZLO directamente con las herramientas.
2. Confirma siempre las acciones realizadas con el ID creado/actualizado.
3. Usa tablas Markdown para listados (columnas separadas por |).
4. REGLA OBLIGATORIA PARA REPORTES Y GRÁFICOS:
   Cuando el usuario pida reporte, gráfico, estadística, resumen de datos, o use palabras como
   "muéstrame", "cuántos hay por", "reporte de", "gráfico de", "estadísticas" → DEBES llamar
   a la herramienta get_report_data. NUNCA respondas con solo texto cuando se pide un gráfico.
   a. Llama SIEMPRE a get_report_data con el report_type correcto.
   b. Con los datos recibidos genera el formato [GRAFICO:tipo,Label1:Valor1,Label2:Valor2,...]:
      - chart_hint=barra → [GRAFICO:barra,Label1:Valor1,Label2:Valor2]
      - chart_hint=circular → [GRAFICO:circular,Label1:Valor1,Label2:Valor2]
      - chart_hint=linea → [GRAFICO:linea,Label1:Valor1,Label2:Valor2]
   c. Después del gráfico, incluye tabla Markdown con los mismos datos.
   d. Ejemplo: si get_report_data devuelve {"data":{"Disponibles":12,"Vendidas":9,"Alquiladas":3},"chart_hint":"circular"}
      tu respuesta DEBE incluir: [GRAFICO:circular,Disponibles:12,Vendidas:9,Alquiladas:3]
5. report_types disponibles: properties_by_state, properties_by_type, sales_by_month, visits_by_property,
   commissions_by_advisor, contracts_by_type, expenses_by_type, offers_by_state,
   leads_by_temperature, payments_by_method, days_on_market_by_type.
6. ACCIONES DESTRUCTIVAS (archivar, cancelar, eliminar masivo): ANTES de ejecutar, responde con:
   "⚠️ CONFIRMACIÓN REQUERIDA: Estás a punto de [acción]. ¿Confirmas? (responde 'sí confirmo')"
   Solo ejecuta cuando el usuario confirme explícitamente.
7. Si detectas alertas críticas (pagos vencidos, leads sin actividad), menciónalas proactivamente.
8. Usa save_memory para guardar preferencias o datos importantes del usuario para futuras sesiones.
9. Para el BRIEFING MATUTINO, combina: resumen ejecutivo + visitas del día + tendencias + alertas críticas."""

        query_type = self._classify_query(message)

        # Load conversation history for memory
        conversation_history = self._get_conversation_history(request.env.user.id)

        try:
            if provider == 'chatgpt':
                response = self._query_chatgpt_with_tools(
                    api_key, model, temperature, max_tokens,
                    full_system_prompt, message, conversation_history)
            elif provider == 'gemini':
                response = self._query_gemini_with_tools(
                    api_key, model, temperature, max_tokens,
                    full_system_prompt, message, conversation_history)
            else:
                response = '❌ Proveedor de IA no soportado.'
        except Exception as e:
            _logger.error("Error en agente IA: %s", str(e))
            response = f'❌ Error al procesar la consulta: {str(e)}'

        processing_time = time.time() - start_time
        request.env['estate.ai.chat.history'].sudo().create({
            'user_id': request.env.user.id,
            'query': message,
            'response': response,
            'query_type': query_type,
            'processing_time': processing_time,
        })

        return {'response': response, 'query_type': query_type}

    # -----------------------------------------------------------------------
    # Conversation History
    # -----------------------------------------------------------------------
    def _get_conversation_history(self, user_id):
        """Load last 20 messages from history as alternating user/assistant pairs."""
        history = request.env['estate.ai.chat.history'].sudo().search(
            [('user_id', '=', user_id)],
            order='create_date asc',
            limit=20,
        )
        messages = []
        for h in history:
            messages.append({"role": "user", "content": h.query})
            messages.append({"role": "assistant", "content": h.response or ''})
        return messages

    # -----------------------------------------------------------------------
    # Tool Execution
    # -----------------------------------------------------------------------
    def _execute_tool(self, tool_name, args, env=None):
        """Execute a tool call and return a JSON-serializable result string."""
        if env is None:
            env = request.env
        try:
            if tool_name == 'search_properties':
                domain = []
                if args.get('city'):
                    domain.append(('city', 'ilike', args['city']))
                if args.get('state'):
                    domain.append(('state', '=', args['state']))
                if args.get('max_price'):
                    domain.append(('price', '<=', args['max_price']))
                if args.get('min_price'):
                    domain.append(('price', '>=', args['min_price']))
                if args.get('property_type'):
                    domain.append(('property_type_id.name', 'ilike', args['property_type']))
                limit = int(args.get('limit', 10))
                props = env['estate.property'].sudo().search(domain, limit=limit)
                result = [
                    {
                        'id': p.id, 'ref': p.name, 'titulo': p.title,
                        'ciudad': p.city, 'precio': p.price,
                        'estado': p.state, 'area': p.area,
                        'habitaciones': p.bedrooms, 'tipo': p.property_type_id.name,
                        'dias_mercado': p.days_on_market,
                        'avm_status': p.avm_status,
                    }
                    for p in props
                ]
                return json.dumps(result, ensure_ascii=False)

            elif tool_name == 'get_leads':
                domain = [('type', '=', 'lead')]
                if args.get('temperature'):
                    domain.append(('lead_temperature', '=', args['temperature']))
                if args.get('score'):
                    domain.append(('lead_score', '=', args['score']))
                limit = int(args.get('limit', 10))
                leads = env['crm.lead'].sudo().search(domain, limit=limit)
                result = [
                    {
                        'id': l.id, 'nombre': l.name,
                        'cliente': l.partner_id.name if l.partner_id else l.contact_name,
                        'presupuesto': l.client_budget,
                        'temperatura': l.lead_temperature,
                        'puntuacion': l.lead_score,
                        'match': l.match_percentage,
                        'propiedad': l.target_property_id.title if l.target_property_id else None,
                        'etapa': l.stage_id.name if l.stage_id else None,
                    }
                    for l in leads
                ]
                return json.dumps(result, ensure_ascii=False)

            elif tool_name == 'get_market_stats':
                domain = [('state', '=', 'sold'), ('days_on_market', '>', 0)]
                if args.get('city'):
                    domain.append(('city', 'ilike', args['city']))
                if args.get('property_type'):
                    domain.append(('property_type_id.name', 'ilike', args['property_type']))
                sold = env['estate.property'].sudo().search(domain, limit=100)
                if not sold:
                    return json.dumps({'error': 'Sin datos suficientes para el filtro indicado.'})
                prices = sold.mapped('price')
                days = sold.mapped('days_on_market')
                stats = {
                    'total_vendidas': len(sold),
                    'precio_promedio': round(sum(prices) / len(prices), 2),
                    'precio_minimo': min(prices),
                    'precio_maximo': max(prices),
                    'dias_promedio_venta': round(sum(days) / len(days), 1),
                    'comision_total': round(sum(sold.mapped('commission_amount')), 2),
                }
                return json.dumps(stats, ensure_ascii=False)

            elif tool_name == 'create_crm_activity':
                lead_id = int(args.get('lead_id', 0))
                if not lead_id:
                    return json.dumps({'error': 'lead_id requerido'})
                lead = env['crm.lead'].sudo().browse(lead_id)
                if not lead.exists():
                    return json.dumps({'error': f'Lead {lead_id} no encontrado'})
                lead.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary=args.get('summary', 'Seguimiento IA'),
                    note=args.get('note', ''),
                    user_id=lead.user_id.id or env.uid,
                )
                return json.dumps({'success': True, 'mensaje': f'Actividad creada en lead #{lead_id}: {lead.name}'})

            elif tool_name == 'create_lead':
                vals = {
                    'name': args.get('name', 'Lead desde Agente IA'),
                    'contact_name': args.get('contact_name', ''),
                    'email_from': args.get('email', ''),
                    'phone': args.get('mobile', '') or args.get('phone', ''),
                    'type': 'opportunity',
                    'description': args.get('notes', ''),
                }
                if args.get('client_budget'):
                    vals['client_budget'] = float(args['client_budget'])
                # Find or create partner
                if args.get('contact_name'):
                    partner = env['res.partner'].sudo().search(
                        [('name', 'ilike', args['contact_name'])], limit=1)
                    if partner:
                        vals['partner_id'] = partner.id
                lead = env['crm.lead'].sudo().create(vals)
                # Post a note if city provided
                if args.get('city'):
                    lead.message_post(body=f"🤖 Agente IA — Ciudad buscada: {args['city']}")
                return json.dumps({
                    'success': True,
                    'lead_id': lead.id,
                    'mensaje': f"Lead #{lead.id} creado: '{lead.name}' para {args.get('contact_name', '?')}",
                })

            elif tool_name == 'create_property':
                # Resolve property type
                ptype = None
                if args.get('property_type'):
                    ptype = env['estate.property.type'].sudo().search(
                        [('name', 'ilike', args['property_type'])], limit=1)
                vals = {
                    'title': args.get('title', ''),
                    'city': args.get('city', ''),
                    'price': float(args.get('price', 0)),
                    'offer_type': args.get('offer_type', 'sale'),
                    'state': 'available',
                }
                if args.get('area'):
                    vals['area'] = float(args['area'])
                if args.get('bedrooms'):
                    vals['bedrooms'] = int(args['bedrooms'])
                if args.get('bathrooms'):
                    vals['bathrooms'] = int(args['bathrooms'])
                if args.get('street'):
                    vals['street'] = args['street']
                if args.get('description'):
                    vals['description'] = args['description']
                if ptype:
                    vals['property_type_id'] = ptype.id
                prop = env['estate.property'].sudo().create(vals)
                return json.dumps({
                    'success': True,
                    'property_id': prop.id,
                    'ref': prop.name,
                    'mensaje': f"Propiedad '{prop.title}' registrada con referencia {prop.name} (ID #{prop.id})",
                })

            elif tool_name == 'update_lead':
                lead_id = int(args.get('lead_id', 0))
                if not lead_id:
                    return json.dumps({'error': 'lead_id requerido'})
                lead = env['crm.lead'].sudo().browse(lead_id)
                if not lead.exists():
                    return json.dumps({'error': f'Lead {lead_id} no encontrado'})
                vals = {}
                if args.get('temperature'):
                    vals['lead_temperature'] = args['temperature']
                if args.get('client_budget'):
                    vals['client_budget'] = float(args['client_budget'])
                if args.get('property_id'):
                    prop = env['estate.property'].sudo().browse(int(args['property_id']))
                    if prop.exists():
                        vals['target_property_id'] = prop.id
                if args.get('stage_name'):
                    stage = env['crm.stage'].sudo().search(
                        [('name', 'ilike', args['stage_name'])], limit=1)
                    if stage:
                        vals['stage_id'] = stage.id
                if vals:
                    lead.write(vals)
                if args.get('notes'):
                    lead.message_post(body=f"🤖 Agente IA: {args['notes']}")
                return json.dumps({
                    'success': True,
                    'mensaje': f"Lead #{lead_id} '{lead.name}' actualizado correctamente.",
                    'cambios': list(vals.keys()),
                })

            elif tool_name == 'get_property_detail':
                pid = int(args.get('property_id', 0))
                prop = None
                if pid:
                    prop = env['estate.property'].sudo().browse(pid)
                    if not prop.exists():
                        prop = None
                if not prop and args.get('property_name'):
                    prop = env['estate.property'].sudo().search(
                        [('title', 'ilike', args['property_name'])], limit=1)
                    if not prop:
                        prop = env['estate.property'].sudo().search(
                            [('name', 'ilike', args['property_name'])], limit=1)
                if not prop:
                    return json.dumps({'error': 'Propiedad no encontrada. Proporciona el ID o el nombre.'})
                return json.dumps({
                    'id': prop.id,
                    'ref': prop.name,
                    'titulo': prop.title,
                    'ciudad': prop.city,
                    'calle': prop.street or '',
                    'precio': prop.price,
                    'area_m2': prop.area,
                    'habitaciones': prop.bedrooms,
                    'banos': prop.bathrooms,
                    'estado': prop.state,
                    'tipo_operacion': prop.offer_type,
                    'tipo_propiedad': prop.property_type_id.name if prop.property_type_id else '',
                    'propietario': prop.owner_id.name if prop.owner_id else '',
                    'asesor': prop.user_id.name if prop.user_id else '',
                    'descripcion': (prop.description or '')[:500],
                    'avm_precio': prop.avm_estimated_price if hasattr(prop, 'avm_estimated_price') else 0,
                    'avm_estado': prop.avm_status if hasattr(prop, 'avm_status') else '',
                    'dias_en_mercado': prop.days_on_market if hasattr(prop, 'days_on_market') else 0,
                    'latitud': prop.latitude if hasattr(prop, 'latitude') else 0,
                    'longitud': prop.longitude if hasattr(prop, 'longitude') else 0,
                    'activa': prop.active,
                })

            elif tool_name == 'update_property':
                property_id = int(args.get('property_id', 0))
                if not property_id:
                    return json.dumps({'error': 'property_id requerido'})
                prop = env['estate.property'].sudo().browse(property_id)
                if not prop.exists():
                    return json.dumps({'error': f'Propiedad {property_id} no encontrada'})
                vals = {}
                if args.get('price') is not None:
                    vals['price'] = float(args['price'])
                if args.get('description'):
                    vals['description'] = args['description']
                if args.get('title'):
                    vals['title'] = args['title']
                if args.get('state') and args['state'] in ('available', 'reserved', 'sold', 'rented'):
                    vals['state'] = args['state']
                if args.get('bedrooms') is not None:
                    vals['bedrooms'] = int(args['bedrooms'])
                if args.get('bathrooms') is not None:
                    vals['bathrooms'] = int(args['bathrooms'])
                if args.get('area') is not None:
                    vals['area'] = float(args['area'])
                if args.get('street'):
                    vals['street'] = args['street']
                if args.get('city'):
                    vals['city'] = args['city']
                if args.get('offer_type') and args['offer_type'] in ('sale', 'rent'):
                    vals['offer_type'] = args['offer_type']
                if args.get('property_type'):
                    ptype = env['estate.property.type'].sudo().search(
                        [('name', 'ilike', args['property_type'])], limit=1)
                    if ptype:
                        vals['property_type_id'] = ptype.id
                if args.get('owner_name'):
                    owner = env['res.partner'].sudo().search(
                        [('name', 'ilike', args['owner_name'])], limit=1)
                    if owner:
                        vals['owner_id'] = owner.id
                if args.get('advisor_name'):
                    advisor = env['res.users'].sudo().search(
                        [('name', 'ilike', args['advisor_name'])], limit=1)
                    if advisor:
                        vals['user_id'] = advisor.id
                if args.get('latitude') is not None and hasattr(prop, 'latitude'):
                    vals['latitude'] = float(args['latitude'])
                if args.get('longitude') is not None and hasattr(prop, 'longitude'):
                    vals['longitude'] = float(args['longitude'])
                if vals:
                    prop.write(vals)
                if args.get('notes'):
                    prop.message_post(body=f"🤖 Agente IA: {args['notes']}")
                return json.dumps({
                    'success': True,
                    'property_id': prop.id,
                    'ref': prop.name,
                    'mensaje': f"Propiedad '{prop.title}' ({prop.name}) actualizada correctamente.",
                    'campos_actualizados': list(vals.keys()),
                })

            elif tool_name == 'delete_property':
                if not args.get('confirmed'):
                    return json.dumps({
                        'requiere_confirmacion': True,
                        'mensaje': '⚠️ CONFIRMACIÓN REQUERIDA: Esta acción eliminará la propiedad PERMANENTEMENTE y no se puede deshacer. Responde "sí confirmo" para continuar.',
                    })
                property_id = int(args.get('property_id', 0))
                prop = env['estate.property'].sudo().browse(property_id)
                if not prop.exists():
                    return json.dumps({'error': f'Propiedad {property_id} no encontrada'})
                title = prop.title
                ref = prop.name
                try:
                    prop.unlink()
                    return json.dumps({
                        'success': True,
                        'mensaje': f"Propiedad '{title}' ({ref}) eliminada permanentemente del sistema.",
                    })
                except Exception as e:
                    return json.dumps({'error': f'No se puede eliminar: {str(e)}. Intenta archivarla en su lugar.'})

            elif tool_name == 'duplicate_property':
                property_id = int(args.get('property_id', 0))
                prop = env['estate.property'].sudo().browse(property_id)
                if not prop.exists():
                    return json.dumps({'error': f'Propiedad {property_id} no encontrada'})
                default = {'state': 'available'}
                if args.get('new_title'):
                    default['title'] = args['new_title']
                if args.get('new_price'):
                    default['price'] = float(args['new_price'])
                new_prop = prop.copy(default=default)
                return json.dumps({
                    'success': True,
                    'property_id': new_prop.id,
                    'ref': new_prop.name,
                    'mensaje': f"Propiedad duplicada: '{new_prop.title}' (ID #{new_prop.id}, ref {new_prop.name}). Estado: disponible.",
                })

            elif tool_name == 'schedule_visit':
                property_id = int(args.get('property_id', 0))
                if not property_id:
                    return json.dumps({'error': 'property_id requerido'})
                prop = env['estate.property'].sudo().browse(property_id)
                if not prop.exists():
                    return json.dumps({'error': f'Propiedad {property_id} no encontrada'})
                # Parse datetime
                from datetime import datetime, timedelta
                try:
                    start_dt = datetime.strptime(args['start_datetime'], '%Y-%m-%d %H:%M')
                except Exception:
                    return json.dumps({'error': 'Formato de fecha inválido. Use YYYY-MM-DD HH:MM'})
                end_dt = start_dt + timedelta(hours=1)
                # Find or create partner
                partner = None
                if args.get('partner_name'):
                    partner = env['res.partner'].sudo().search(
                        [('name', 'ilike', args['partner_name'])], limit=1)
                event_vals = {
                    'name': f"Visita: {prop.title}",
                    'start': start_dt,
                    'stop': end_dt,
                    'description': args.get('notes', f"Visita agendada por Agente IA"),
                    'user_id': env.uid,
                }
                # Add property if the field exists (estate_calendar module)
                if 'property_id' in env['calendar.event']._fields:
                    event_vals['property_id'] = property_id
                if partner:
                    event_vals['partner_ids'] = [(4, partner.id)]
                event = env['calendar.event'].sudo().create(event_vals)
                # Link to lead if provided
                if args.get('lead_id'):
                    lead = env['crm.lead'].sudo().browse(int(args['lead_id']))
                    if lead.exists():
                        lead.message_post(body=f"🗓️ Visita agendada para {start_dt.strftime('%d/%m/%Y %H:%M')} — Propiedad: {prop.title}")
                return json.dumps({
                    'success': True,
                    'event_id': event.id,
                    'mensaje': f"Visita agendada el {start_dt.strftime('%d/%m/%Y a las %H:%M')} para '{prop.title}'",
                })

            elif tool_name == 'reserve_property':
                property_id = int(args.get('property_id', 0))
                if not property_id:
                    return json.dumps({'error': 'property_id requerido'})
                prop = env['estate.property'].sudo().browse(property_id)
                if not prop.exists():
                    return json.dumps({'error': f'Propiedad {property_id} no encontrada'})
                vals = {'state': 'reserved'}
                if args.get('buyer_name'):
                    buyer = env['res.partner'].sudo().search(
                        [('name', 'ilike', args['buyer_name'])], limit=1)
                    if buyer:
                        vals['buyer_id'] = buyer.id
                prop.write(vals)
                note = args.get('notes', 'Reservada vía Agente IA')
                if args.get('buyer_name'):
                    note += f" — Comprador: {args['buyer_name']}"
                prop.message_post(body=f"🤖 {note}")
                return json.dumps({
                    'success': True,
                    'mensaje': f"Propiedad '{prop.title}' marcada como RESERVADA.",
                })

            elif tool_name == 'sell_property':
                property_id = int(args.get('property_id', 0))
                if not property_id:
                    return json.dumps({'error': 'property_id requerido'})
                prop = env['estate.property'].sudo().browse(property_id)
                if not prop.exists():
                    return json.dumps({'error': f'Propiedad {property_id} no encontrada'})
                close_type = args.get('close_type', 'sold')
                vals = {'state': close_type if close_type in ('sold', 'rented') else 'sold'}
                if args.get('final_price'):
                    vals['price'] = float(args['final_price'])
                from datetime import date
                vals['date_sold'] = date.today()
                prop.write(vals)
                estado_str = 'VENDIDA' if vals['state'] == 'sold' else 'ALQUILADA'
                note = args.get('notes', f"Cerrada como {estado_str} vía Agente IA")
                prop.message_post(body=f"🤖 {note}")
                return json.dumps({
                    'success': True,
                    'mensaje': f"Propiedad '{prop.title}' marcada como {estado_str}. Precio final: ${prop.price:,.2f}",
                })

            elif tool_name == 'send_whatsapp_lead':
                lead_id = int(args.get('lead_id', 0))
                if not lead_id:
                    return json.dumps({'error': 'lead_id requerido'})
                lead = env['crm.lead'].sudo().browse(lead_id)
                if not lead.exists():
                    return json.dumps({'error': f'Lead {lead_id} no encontrado'})
                partner = lead.partner_id
                phone = ''
                if partner:
                    phone = partner.mobile or partner.phone or ''
                if not phone:
                    phone = lead.mobile or lead.phone or ''
                if not phone:
                    return json.dumps({'error': 'El cliente no tiene número de teléfono registrado.'})
                # Clean phone number
                phone_clean = ''.join(c for c in phone if c.isdigit() or c == '+')
                if phone_clean.startswith('0'):
                    phone_clean = '+593' + phone_clean[1:]
                default_msg = args.get('message') or (
                    f"Hola {lead.contact_name or (partner.name if partner else 'estimado cliente')}, "
                    f"le contactamos de nuestra inmobiliaria respecto a su interés en propiedades. "
                    f"¿Tiene un momento para hablar?"
                )
                import urllib.parse
                wa_url = f"https://wa.me/{phone_clean.replace('+','')}?text={urllib.parse.quote(default_msg)}"
                return json.dumps({
                    'success': True,
                    'whatsapp_url': wa_url,
                    'telefono': phone_clean,
                    'cliente': partner.name if partner else lead.contact_name,
                    'mensaje': f"Enlace de WhatsApp generado para {partner.name if partner else lead.contact_name} ({phone_clean}): {wa_url}",
                })

            elif tool_name == 'archive_lead':
                lead_id = int(args.get('lead_id', 0))
                if not lead_id:
                    return json.dumps({'error': 'lead_id requerido'})
                lead = env['crm.lead'].sudo().browse(lead_id)
                if not lead.exists():
                    return json.dumps({'error': f'Lead {lead_id} no encontrado'})
                nombre = lead.name
                reason = args.get('reason', 'Archivado vía Agente IA')
                lead.message_post(body=f"🤖 Archivado: {reason}")
                lead.write({'active': False})
                return json.dumps({
                    'success': True,
                    'mensaje': f"Lead #{lead_id} '{nombre}' archivado. Motivo: {reason}",
                })

            elif tool_name == 'get_payments_contracts':
                from datetime import date, timedelta
                today = date.today()
                days_ahead = int(args.get('days_ahead', 30))
                limit_date = today + timedelta(days=days_ahead)
                # Overdue invoices
                overdue = env['account.move'].sudo().search([
                    ('move_type', '=', 'out_invoice'),
                    ('payment_state', 'in', ('not_paid', 'partial')),
                    ('invoice_date_due', '<', today),
                ])
                # Expiring contracts
                expiring = env['estate.property'].sudo().search([
                    ('contract_end_date', '!=', False),
                    ('contract_end_date', '>=', today),
                    ('contract_end_date', '<=', limit_date),
                    ('state', '=', 'rented'),
                ])
                result = {
                    'facturas_vencidas': [
                        {
                            'id': inv.id,
                            'numero': inv.name,
                            'cliente': inv.partner_id.name if inv.partner_id else '',
                            'monto': inv.amount_residual,
                            'vencimiento': str(inv.invoice_date_due),
                        }
                        for inv in overdue[:20]
                    ],
                    'contratos_por_vencer': [
                        {
                            'id': p.id,
                            'ref': p.name,
                            'titulo': p.title,
                            'fin_contrato': str(p.contract_end_date),
                            'dias_restantes': (p.contract_end_date - today).days,
                        }
                        for p in expiring
                    ],
                    'total_facturas_vencidas': len(overdue),
                    'monto_total_vencido': round(sum(overdue.mapped('amount_residual')), 2),
                    'contratos_proximos_vencer': len(expiring),
                }
                return json.dumps(result, ensure_ascii=False, default=str)

            elif tool_name == 'get_dashboard_summary':
                from datetime import date, timedelta
                today = date.today()
                period = args.get('period', 'month')
                if period == 'today':
                    start = today
                elif period == 'week':
                    start = today - timedelta(days=7)
                else:
                    start = today.replace(day=1)

                props = env['estate.property'].sudo().search([])
                available = props.filtered(lambda p: p.state == 'available')
                sold_period = props.filtered(
                    lambda p: p.state == 'sold' and p.date_sold and p.date_sold >= start)
                rented = props.filtered(lambda p: p.state == 'rented')
                reserved = props.filtered(lambda p: p.state == 'reserved')

                leads = env['crm.lead'].sudo().search([('type', '=', 'lead')])
                hot_leads = leads.filtered(lambda l: l.lead_temperature in ('hot', 'boiling'))
                new_leads = env['crm.lead'].sudo().search([
                    ('type', '=', 'lead'),
                    ('create_date', '>=', str(start)),
                ])

                # Visits in period
                visits = env['calendar.event'].sudo().search([
                    ('start', '>=', str(start)),
                ])
                try:
                    done_visits = visits.filtered(lambda v: getattr(v, 'visit_state', '') == 'done')
                except Exception:
                    done_visits = []

                invoices_period = env['account.move'].sudo().search([
                    ('move_type', '=', 'out_invoice'),
                    ('invoice_date', '>=', str(start)),
                    ('state', '=', 'posted'),
                ])
                revenue = sum(invoices_period.mapped('amount_total'))
                commissions = sum(sold_period.mapped('commission_amount'))

                # Stagnant properties (45+ days without visits)
                stagnant = available.filtered(lambda p: (p.days_on_market or 0) > 45)

                summary = {
                    'periodo': f"{start} a {today}",
                    'inventario': {
                        'total': len(props),
                        'disponibles': len(available),
                        'vendidas_periodo': len(sold_period),
                        'alquiladas': len(rented),
                        'reservadas': len(reserved),
                        'estancadas_45dias': len(stagnant),
                    },
                    'crm': {
                        'total_leads': len(leads),
                        'leads_calientes': len(hot_leads),
                        'nuevos_periodo': len(new_leads),
                    },
                    'visitas': {
                        'agendadas_periodo': len(visits),
                        'realizadas': len(done_visits),
                    },
                    'financiero': {
                        'ingresos_periodo': round(revenue, 2),
                        'comisiones_generadas': round(commissions, 2),
                        'facturas_emitidas': len(invoices_period),
                    },
                    'alertas': [],
                }
                if stagnant:
                    summary['alertas'].append(f"⚠️ {len(stagnant)} propiedad(es) llevan 45+ días sin vender")
                if hot_leads:
                    summary['alertas'].append(f"🔥 {len(hot_leads)} lead(s) calientes/hirviendo esperan atención")
                return json.dumps(summary, ensure_ascii=False, default=str)

            elif tool_name == 'get_report_data':
                return self._execute_report_data(args, env)

            # ── A1: CRUD Contratos ─────────────────────────────────────────────
            elif tool_name == 'create_contract':
                prop = env['estate.property'].sudo().browse(int(args['property_id']))
                if not prop.exists():
                    return json.dumps({'error': f"Propiedad {args['property_id']} no encontrada"})
                partner = env['res.partner'].sudo().search(
                    [('name', 'ilike', args['partner_name'])], limit=1)
                if not partner:
                    partner = env['res.partner'].sudo().create({'name': args['partner_name']})
                from datetime import date as _date
                contract_vals = {
                    'property_id': prop.id,
                    'partner_id': partner.id,
                    'contract_type': args.get('contract_type', 'sale'),
                    'amount': float(args['amount']),
                    'date_start': args.get('date_start') or str(_date.today()),
                    'user_id': env.uid,
                }
                if args.get('date_end'):
                    contract_vals['date_end'] = args['date_end']
                if args.get('notes'):
                    contract_vals['notes'] = args['notes']
                contract = env['estate.contract'].sudo().create(contract_vals)
                contract.message_post(body='🤖 Contrato creado por el Agente IA.')
                return json.dumps({'success': True, 'contract_id': contract.id,
                    'ref': contract.name,
                    'mensaje': f"Contrato {contract.name} creado para '{partner.name}' — {prop.title} — ${float(args['amount']):,.2f}"})

            elif tool_name == 'update_contract':
                contract = env['estate.contract'].sudo().browse(int(args['contract_id']))
                if not contract.exists():
                    return json.dumps({'error': f"Contrato {args['contract_id']} no encontrado"})
                action = args.get('action', '')
                if action == 'activate':
                    contract.action_activate()
                elif action == 'cancel':
                    contract.action_cancel()
                elif action == 'expire':
                    contract.action_set_expired()
                if args.get('amount'):
                    contract.write({'amount': float(args['amount'])})
                note = args.get('notes', f'Actualizado vía Agente IA: {action}')
                contract.message_post(body=f'🤖 {note}')
                return json.dumps({'success': True,
                    'mensaje': f"Contrato {contract.name} actualizado — acción: {action}"})

            elif tool_name == 'create_payment':
                contract = env['estate.contract'].sudo().browse(int(args['contract_id']))
                if not contract.exists():
                    return json.dumps({'error': f"Contrato {args['contract_id']} no encontrado"})
                from datetime import date as _date
                pay_vals = {
                    'contract_id': contract.id,
                    'amount': float(args['amount']),
                    'payment_method': args.get('payment_method', 'bank'),
                    'date': args.get('date') or str(_date.today()),
                }
                if args.get('notes'):
                    pay_vals['notes'] = args['notes']
                payment = env['estate.payment'].sudo().create(pay_vals)
                return json.dumps({'success': True, 'payment_id': payment.id,
                    'ref': payment.name,
                    'mensaje': f"Pago {payment.name} de ${float(args['amount']):,.2f} registrado en contrato {contract.name}"})

            elif tool_name == 'approve_payment':
                payment = env['estate.payment'].sudo().browse(int(args['payment_id']))
                if not payment.exists():
                    return json.dumps({'error': f"Pago {args['payment_id']} no encontrado"})
                payment.action_confirm()
                return json.dumps({'success': True,
                    'mensaje': f"Pago {payment.name} de ${payment.amount:,.2f} marcado como PAGADO ✅"})

            elif tool_name == 'create_offer':
                prop = env['estate.property'].sudo().browse(int(args['property_id']))
                if not prop.exists():
                    return json.dumps({'error': f"Propiedad {args['property_id']} no encontrada"})
                partner = env['res.partner'].sudo().search(
                    [('name', 'ilike', args['partner_name'])], limit=1)
                if not partner:
                    partner = env['res.partner'].sudo().create({'name': args['partner_name']})
                offer = env['estate.property.offer'].sudo().create({
                    'property_id': prop.id,
                    'partner_id': partner.id,
                    'offer_amount': float(args['offer_amount']),
                    'financing_type': args.get('financing_type', 'cash'),
                    'notes': args.get('notes', 'Oferta registrada por Agente IA'),
                })
                return json.dumps({'success': True, 'offer_id': offer.id,
                    'ref': offer.name,
                    'mensaje': f"Oferta {offer.name} de ${float(args['offer_amount']):,.2f} registrada para '{partner.name}' en {prop.title}"})

            elif tool_name == 'create_commission':
                prop = env['estate.property'].sudo().browse(int(args['property_id']))
                if not prop.exists():
                    return json.dumps({'error': f"Propiedad {args['property_id']} no encontrada"})
                user = env['res.users'].sudo().search(
                    [('name', 'ilike', args['agent_name'])], limit=1)
                if not user:
                    return json.dumps({'error': f"Asesor '{args['agent_name']}' no encontrado"})
                from datetime import date as _date
                comm = env['estate.commission'].sudo().create({
                    'property_id': prop.id,
                    'user_id': user.id,
                    'amount': float(args['amount']),
                    'type': args.get('commission_type', 'sale'),
                    'date': args.get('date') or str(_date.today()),
                })
                return json.dumps({'success': True, 'commission_id': comm.id,
                    'ref': comm.name,
                    'mensaje': f"Comisión {comm.name} de ${float(args['amount']):,.2f} registrada para {user.name}"})

            elif tool_name == 'approve_commission':
                comm = env['estate.commission'].sudo().browse(int(args['commission_id']))
                if not comm.exists():
                    return json.dumps({'error': f"Comisión {args['commission_id']} no encontrada"})
                action = args.get('action', 'approve')
                new_state = 'approved' if action == 'approve' else 'paid'
                comm.write({'state': new_state})
                label = 'APROBADA ✅' if new_state == 'approved' else 'PAGADA 💰'
                return json.dumps({'success': True,
                    'mensaje': f"Comisión {comm.name} de ${comm.amount:,.2f} marcada como {label}"})

            # ── A2: PDF ────────────────────────────────────────────────────────
            elif tool_name == 'generate_pdf_report':
                rtype = args.get('report_type', '')
                rid = int(args.get('record_id', 0))
                report_map = {
                    'ficha_propiedad':       ('estate_management.action_report_ficha_tecnica', 'estate.property'),
                    'estado_cuenta_contrato': ('estate_reports.action_report_contract_statement', 'estate.contract'),
                    'cotizacion_lead':        ('estate_crm.action_report_crm_quotation', 'crm.lead'),
                }
                if rtype not in report_map:
                    return json.dumps({'error': f"report_type '{rtype}' no reconocido. Usa: {', '.join(report_map)}"})
                import base64
                xmlid, model = report_map[rtype]
                report_action = env.ref(xmlid, raise_if_not_found=False)
                if not report_action:
                    return json.dumps({'error': f"Reporte {xmlid} no encontrado"})
                record = env[model].sudo().browse(rid)
                if not record.exists():
                    return json.dumps({'error': f"Registro {rid} no encontrado en {model}"})
                pdf_content, _ = report_action._render_qweb_pdf([rid])
                attachment = env['ir.attachment'].sudo().create({
                    'name': f'{rtype}_{rid}.pdf',
                    'datas': base64.b64encode(pdf_content).decode(),
                    'res_model': model,
                    'res_id': rid,
                    'mimetype': 'application/pdf',
                })
                url = f'/web/content/{attachment.id}?download=true'
                return json.dumps({'success': True, 'url': url,
                    'mensaje': f"PDF generado ✅ → [Descargar aquí]({url})"})

            # ── A4: Archivar ───────────────────────────────────────────────────
            elif tool_name == 'archive_property':
                prop = env['estate.property'].sudo().browse(int(args['property_id']))
                if not prop.exists():
                    return json.dumps({'error': f"Propiedad {args['property_id']} no encontrada"})
                title = prop.title
                reason = args.get('reason', 'Archivada vía Agente IA')
                prop.message_post(body=f'🤖 Archivada: {reason}')
                prop.write({'active': False})
                return json.dumps({'success': True,
                    'mensaje': f"Propiedad '{title}' archivada. Motivo: {reason}"})

            elif tool_name == 'cancel_payment':
                payment = env['estate.payment'].sudo().browse(int(args['payment_id']))
                if not payment.exists():
                    return json.dumps({'error': f"Pago {args['payment_id']} no encontrado"})
                reason = args.get('reason', 'Cancelado vía Agente IA')
                payment.message_post(body=f'🤖 Cancelado: {reason}')
                payment.action_cancel()
                return json.dumps({'success': True,
                    'mensaje': f"Pago {payment.name} anulado. Motivo: {reason}"})

            # ── A5: Lote ───────────────────────────────────────────────────────
            elif tool_name == 'batch_update_properties':
                domain = []
                if args.get('city'):
                    domain.append(('city', 'ilike', args['city']))
                if args.get('state_filter'):
                    domain.append(('state', '=', args['state_filter']))
                props = env['estate.property'].sudo().search(domain, limit=50)
                if not props:
                    return json.dumps({'error': 'No se encontraron propiedades con esos filtros'})
                vals = {}
                if args.get('new_state') and args['new_state'] in ('available', 'reserved', 'sold', 'rented'):
                    vals['state'] = args['new_state']
                if args.get('new_price_pct'):
                    pct = float(args['new_price_pct']) / 100
                    for p in props:
                        p.write({'price': round(p.price * (1 + pct), 2)})
                    if vals:
                        props.write(vals)
                    note = args.get('notes', f'Precio ajustado {args["new_price_pct"]}% vía Agente IA')
                    for p in props:
                        p.message_post(body=f'🤖 Lote: {note}')
                    return json.dumps({'success': True,
                        'affected': len(props),
                        'mensaje': f"{len(props)} propiedades actualizadas — precio {args['new_price_pct']}%"})
                if vals:
                    props.write(vals)
                note = args.get('notes', 'Actualización masiva vía Agente IA')
                for p in props:
                    p.message_post(body=f'🤖 Lote: {note}')
                return json.dumps({'success': True, 'affected': len(props),
                    'mensaje': f"{len(props)} propiedades actualizadas: {list(vals.keys())}"})

            elif tool_name == 'batch_archive_leads':
                from datetime import date as _date, timedelta
                domain = [('type', '=', 'lead'), ('active', '=', True)]
                if args.get('temperature'):
                    domain.append(('lead_temperature', '=', args['temperature']))
                if args.get('days_inactive'):
                    cutoff = str(_date.today() - timedelta(days=int(args['days_inactive'])))
                    domain.append(('write_date', '<', cutoff))
                leads = env['crm.lead'].sudo().search(domain, limit=50)
                if not leads:
                    return json.dumps({'error': 'No se encontraron leads con esos criterios'})
                reason = args.get('reason', 'Archivado masivo vía Agente IA')
                for l in leads:
                    l.message_post(body=f'🤖 Archivado: {reason}')
                leads.write({'active': False})
                return json.dumps({'success': True, 'affected': len(leads),
                    'mensaje': f"{len(leads)} leads archivados. Motivo: {reason}"})

            # ── A6: Email ──────────────────────────────────────────────────────
            elif tool_name == 'send_email':
                email_to = args.get('email_to', '')
                partner = None
                if args.get('partner_name') and not email_to:
                    partner = env['res.partner'].sudo().search(
                        [('name', 'ilike', args['partner_name'])], limit=1)
                    if partner:
                        email_to = partner.email or ''
                if not email_to:
                    return json.dumps({'error': 'No se encontró email del destinatario'})
                mail = env['mail.mail'].sudo().create({
                    'subject': args['subject'],
                    'body_html': args['body'],
                    'email_to': email_to,
                    'author_id': env.user.partner_id.id,
                })
                mail.send()
                return json.dumps({'success': True,
                    'mensaje': f"Email enviado a {email_to} — Asunto: {args['subject']}"})

            # ── B1: Lead Scoring IA ────────────────────────────────────────────
            elif tool_name == 'analyze_lead_probability':
                lead = env['crm.lead'].sudo().browse(int(args['lead_id']))
                if not lead.exists():
                    return json.dumps({'error': f"Lead {args['lead_id']} no encontrado"})
                # Recopilar historico de leads cerrados
                won_leads = env['crm.lead'].sudo().search([
                    ('stage_id.is_won', '=', True), ('type', '=', 'opportunity')], limit=30)
                lost_leads = env['crm.lead'].sudo().search([
                    ('active', '=', False), ('probability', '<', 10)], limit=20)
                won_summary = [{'budget': l.client_budget, 'match': l.match_percentage,
                    'visits': l.completed_visits_count if hasattr(l, 'completed_visits_count') else 0,
                    'score': l.lead_score, 'temp': l.lead_temperature} for l in won_leads[:15]]
                lost_summary = [{'budget': l.client_budget, 'match': l.match_percentage,
                    'score': l.lead_score, 'temp': l.lead_temperature} for l in lost_leads[:10]]
                return json.dumps({
                    'lead_id': lead.id, 'nombre': lead.name,
                    'cliente': lead.partner_id.name if lead.partner_id else lead.contact_name,
                    'presupuesto': lead.client_budget, 'match': lead.match_percentage,
                    'temperatura': lead.lead_temperature, 'puntuacion': lead.lead_score,
                    'visitas': getattr(lead, 'completed_visits_count', 0),
                    'historico_ganados': won_summary, 'historico_perdidos': lost_summary,
                    'instruccion': 'Con estos datos, calcula la probabilidad de cierre 0-100%, clasifica A/B/C, da 3 factores clave y una acción recomendada.',
                }, ensure_ascii=False)

            # ── B2: Churn ──────────────────────────────────────────────────────
            elif tool_name == 'analyze_churn_risk':
                from datetime import date as _date, timedelta
                today = _date.today()
                days = int(args.get('days_to_expiry', 60))
                limit_date = today + timedelta(days=days)
                contracts = env['estate.contract'].sudo().search([
                    ('state', '=', 'active'), ('contract_type', '=', 'rent'),
                    ('date_end', '!=', False), ('date_end', '<=', str(limit_date)),
                ])
                result = []
                for c in contracts:
                    days_left = (c.date_end - today).days if c.date_end else 999
                    overdue_payments = env['estate.payment'].sudo().search_count([
                        ('contract_id', '=', c.id), ('state', '=', 'pending'),
                        ('date', '<', str(today)),
                    ])
                    maintenance_open = 0
                    if 'estate.tenant.request' in env:
                        maintenance_open = env['estate.tenant.request'].sudo().search_count([
                            ('property_id', '=', c.property_id.id), ('state', 'not in', ('done', 'cancel')),
                        ])
                    risk = 'ALTO' if (days_left < 30 or overdue_payments >= 2) else \
                           'MEDIO' if (days_left < 45 or overdue_payments == 1) else 'BAJO'
                    result.append({
                        'contrato': c.name, 'cliente': c.partner_id.name,
                        'propiedad': c.property_id.title,
                        'dias_para_vencer': days_left, 'pagos_vencidos': overdue_payments,
                        'mantenimientos_abiertos': maintenance_open, 'riesgo': risk,
                    })
                result.sort(key=lambda x: {'ALTO': 0, 'MEDIO': 1, 'BAJO': 2}[x['riesgo']])
                return json.dumps({'total_analizados': len(result), 'contratos': result,
                    'alto_riesgo': sum(1 for r in result if r['riesgo'] == 'ALTO')},
                    ensure_ascii=False)

            # ── B3: AVM IA ─────────────────────────────────────────────────────
            elif tool_name == 'recalculate_avm_ai':
                prop = env['estate.property'].sudo().browse(int(args['property_id']))
                if not prop.exists():
                    return json.dumps({'error': f"Propiedad {args['property_id']} no encontrada"})
                comp_domain = [('state', '=', 'sold'), ('property_type_id', '=', prop.property_type_id.id)]
                if prop.city:
                    comp_domain.append(('city', 'ilike', prop.city))
                comparables = env['estate.property'].sudo().search(comp_domain, limit=20)
                comp_data = [{'precio': c.price, 'area': c.area or 0,
                    'habitaciones': c.bedrooms or 0, 'ciudad': c.city,
                    'precio_m2': round(c.price / c.area, 2) if c.area else 0,
                    'dias_venta': c.days_on_market or 0} for c in comparables]
                return json.dumps({
                    'propiedad': {'id': prop.id, 'titulo': prop.title, 'precio_actual': prop.price,
                        'area': prop.area or 0, 'habitaciones': prop.bedrooms or 0,
                        'ciudad': prop.city, 'tipo': prop.property_type_id.name},
                    'comparables': comp_data,
                    'instruccion': (
                        'Con los comparables, calcula el valor justo de mercado de esta propiedad. '
                        'Devuelve: {"valor_estimado": X, "rango_min": Y, "rango_max": Z, '
                        '"confianza_pct": W, "estado_avm": "fair|high|low", "factores": [...], "recomendacion": "..."}'
                    ),
                }, ensure_ascii=False)

            # ── B4: Descripción + WP ───────────────────────────────────────────
            elif tool_name == 'generate_and_apply_description':
                prop = env['estate.property'].sudo().browse(int(args['property_id']))
                if not prop.exists():
                    return json.dumps({'error': f"Propiedad {args['property_id']} no encontrada"})
                style = args.get('style', 'emocional')
                style_map = {
                    'formal': 'profesional y técnico, orientado a inversores',
                    'emocional': 'emotivo y aspiracional, orientado a familias',
                    'directo': 'conciso y directo, con bullet points de beneficios',
                }
                style_desc = style_map.get(style, style_map['emocional'])
                prop_info = (
                    f"Título: {prop.title}\nTipo: {prop.property_type_id.name}\n"
                    f"Ciudad: {prop.city}\nÁrea: {prop.area}m²\n"
                    f"Habitaciones: {prop.bedrooms}\nBaños: {prop.bathrooms}\n"
                    f"Precio: ${prop.price:,.0f}\n"
                    f"Descripción actual: {prop.description or '(sin descripción)'}"
                )
                # If apply=True, we return instructions for the LLM to call update_property after generating
                result = {
                    'property_id': prop.id, 'titulo': prop.title,
                    'info': prop_info, 'estilo': style_desc,
                    'instruccion': (
                        f'Genera una descripción de marketing estilo {style_desc} para esta propiedad. '
                        'Luego, si apply=True, llama a update_property para guardarla.'
                    ),
                    'apply': args.get('apply', False),
                    'publish_wp': args.get('publish_wp', False),
                }
                if args.get('apply') and prop.description:
                    # Already has a description — signal to apply immediately after generation
                    result['nota'] = 'Después de generar, usa update_property para actualizar la descripción.'
                if args.get('publish_wp'):
                    # Check if WordPress integration available
                    has_wp = 'wp_published' in env['estate.property']._fields
                    result['wp_available'] = has_wp
                    if has_wp:
                        result['nota_wp'] = 'Después de actualizar la descripción, llama a update_property con state=available para publicar en WP.'
                return json.dumps(result, ensure_ascii=False)

            # ── B5: Memoria ────────────────────────────────────────────────────
            elif tool_name == 'save_memory':
                if 'estate.ai.memory' not in env:
                    return json.dumps({'error': 'Módulo de memoria no instalado aún'})
                mem = env['estate.ai.memory'].sudo().create({
                    'user_id': env.uid,
                    'content': args['content'],
                    'memory_type': args.get('memory_type', 'fact'),
                })
                return json.dumps({'success': True, 'memory_id': mem.id,
                    'mensaje': f"Memorizado ✅: {args['content'][:80]}"})

            elif tool_name == 'recall_memory':
                if 'estate.ai.memory' not in env:
                    return json.dumps({'memories': [], 'mensaje': 'Sin memorias guardadas aún'})
                domain = [('user_id', '=', env.uid)]
                query = args.get('query', '')
                if query:
                    domain.append(('content', 'ilike', query))
                memories = env['estate.ai.memory'].sudo().search(domain, order='create_date desc', limit=20)
                return json.dumps({'memories': [
                    {'id': m.id, 'tipo': m.memory_type, 'contenido': m.content,
                     'fecha': str(m.create_date)[:10]} for m in memories
                ]}, ensure_ascii=False)

            # ── C1: Búsqueda de Contactos ──────────────────────────────────────
            elif tool_name == 'search_contacts':
                from datetime import date as _date
                query = args.get('query', '')
                limit = int(args.get('limit', 10))
                domain = [('active', '=', True)]
                if query:
                    domain = ['|', '|', ('name', 'ilike', query),
                              ('email', 'ilike', query), ('phone', 'ilike', query)]
                partners = env['res.partner'].sudo().search(domain, limit=limit)
                result = []
                for p in partners:
                    # count leads and contracts
                    lead_count = env['crm.lead'].sudo().search_count([('partner_id', '=', p.id)])
                    contract_count = env['estate.contract'].sudo().search_count([
                        ('partner_id', '=', p.id), ('state', '=', 'active')])
                    if args.get('has_contracts') and contract_count == 0:
                        continue
                    result.append({
                        'id': p.id,
                        'nombre': p.name,
                        'email': p.email or '',
                        'telefono': p.phone or '',
                        'empresa': p.parent_id.name if p.parent_id else '',
                        'leads_activos': lead_count,
                        'contratos_activos': contract_count,
                    })
                return json.dumps(result[:limit], ensure_ascii=False)

            # ── C2: Comparar Propiedades ────────────────────────────────────────
            elif tool_name == 'compare_properties':
                ids = args.get('property_ids', [])
                if len(ids) < 2:
                    return json.dumps({'error': 'Se requieren al menos 2 IDs de propiedades para comparar'})
                props = env['estate.property'].sudo().browse(ids).filtered('id')
                result = []
                for p in props:
                    result.append({
                        'id': p.id,
                        'ref': p.name,
                        'titulo': p.title,
                        'ciudad': p.city,
                        'precio': p.price,
                        'area_m2': p.area,
                        'habitaciones': p.bedrooms,
                        'banos': p.bathrooms,
                        'tipo': p.property_type_id.name if p.property_type_id else '',
                        'estado': p.state,
                        'dias_mercado': p.days_on_market,
                        'precio_m2': round(p.price / p.area, 2) if p.area else None,
                        'avm_precio': p.avm_estimated_price,
                        'avm_status': p.avm_status,
                        'asesor': p.user_id.name if p.user_id else '',
                    })
                return json.dumps({'comparacion': result}, ensure_ascii=False)

            # ── C3: Análisis de Tendencias ──────────────────────────────────────
            elif tool_name == 'get_trend_analysis':
                from datetime import date as _date, timedelta
                metric = args.get('metric', 'all')
                period = args.get('period', 'month')
                today = _date.today()

                if period == 'month':
                    cur_start = today.replace(day=1)
                    prev_end = cur_start - timedelta(days=1)
                    prev_start = prev_end.replace(day=1)
                    cur_label = cur_start.strftime('%B %Y')
                    prev_label = prev_start.strftime('%B %Y')
                elif period == 'quarter':
                    q = (today.month - 1) // 3
                    cur_start = today.replace(month=q * 3 + 1, day=1)
                    prev_end = cur_start - timedelta(days=1)
                    prev_start = prev_end.replace(day=1).replace(month=((prev_end.month - 1) // 3) * 3 + 1)
                    cur_label = f'Q{q+1} {today.year}'
                    prev_label = f'Q{((prev_end.month - 1) // 3) + 1} {prev_end.year}'
                else:  # year
                    cur_start = today.replace(month=1, day=1)
                    prev_start = cur_start.replace(year=today.year - 1)
                    prev_end = cur_start - timedelta(days=1)
                    cur_label = str(today.year)
                    prev_label = str(today.year - 1)

                trends = {}

                if metric in ('sales', 'all'):
                    cur_sales = env['estate.property'].sudo().search_count([
                        ('state', '=', 'sold'), ('date_sold', '>=', str(cur_start))])
                    prev_sales = env['estate.property'].sudo().search_count([
                        ('state', '=', 'sold'),
                        ('date_sold', '>=', str(prev_start)),
                        ('date_sold', '<=', str(prev_end))])
                    delta = cur_sales - prev_sales
                    trends['ventas'] = {
                        cur_label: cur_sales, prev_label: prev_sales,
                        'variacion': f"{'+' if delta >= 0 else ''}{delta}",
                        'tendencia': '📈' if delta > 0 else ('📉' if delta < 0 else '➡️'),
                    }

                if metric in ('leads', 'all'):
                    cur_leads = env['crm.lead'].sudo().search_count([
                        ('create_date', '>=', str(cur_start))])
                    prev_leads = env['crm.lead'].sudo().search_count([
                        ('create_date', '>=', str(prev_start)),
                        ('create_date', '<=', str(prev_end))])
                    delta = cur_leads - prev_leads
                    trends['leads_nuevos'] = {
                        cur_label: cur_leads, prev_label: prev_leads,
                        'variacion': f"{'+' if delta >= 0 else ''}{delta}",
                        'tendencia': '📈' if delta > 0 else ('📉' if delta < 0 else '➡️'),
                    }

                if metric in ('revenue', 'all'):
                    cur_rev_props = env['estate.property'].sudo().search([
                        ('state', '=', 'sold'), ('date_sold', '>=', str(cur_start))])
                    prev_rev_props = env['estate.property'].sudo().search([
                        ('state', '=', 'sold'),
                        ('date_sold', '>=', str(prev_start)),
                        ('date_sold', '<=', str(prev_end))])
                    cur_rev = sum(cur_rev_props.mapped('price'))
                    prev_rev = sum(prev_rev_props.mapped('price'))
                    delta_pct = round((cur_rev - prev_rev) / prev_rev * 100, 1) if prev_rev else 0
                    trends['ingresos'] = {
                        cur_label: round(cur_rev, 2), prev_label: round(prev_rev, 2),
                        'variacion_pct': f"{'+' if delta_pct >= 0 else ''}{delta_pct}%",
                        'tendencia': '📈' if delta_pct > 0 else ('📉' if delta_pct < 0 else '➡️'),
                    }

                if metric in ('days_on_market', 'all'):
                    sold_now = env['estate.property'].sudo().search([
                        ('state', '=', 'sold'), ('date_sold', '>=', str(cur_start)),
                        ('days_on_market', '>', 0)])
                    sold_prev = env['estate.property'].sudo().search([
                        ('state', '=', 'sold'),
                        ('date_sold', '>=', str(prev_start)),
                        ('date_sold', '<=', str(prev_end)),
                        ('days_on_market', '>', 0)])
                    cur_dom = round(sum(sold_now.mapped('days_on_market')) / len(sold_now), 1) if sold_now else 0
                    prev_dom = round(sum(sold_prev.mapped('days_on_market')) / len(sold_prev), 1) if sold_prev else 0
                    delta = round(cur_dom - prev_dom, 1)
                    trends['dias_en_mercado_promedio'] = {
                        cur_label: cur_dom, prev_label: prev_dom,
                        'variacion': f"{'+' if delta >= 0 else ''}{delta}",
                        'tendencia': '📈' if delta < 0 else ('📉' if delta > 0 else '➡️'),
                    }

                return json.dumps({'periodo': period, 'tendencias': trends}, ensure_ascii=False)

            # ── C4: Próximas Visitas ────────────────────────────────────────────
            elif tool_name == 'get_upcoming_visits':
                from datetime import datetime as _dt, timedelta
                days = int(args.get('days_ahead', 7))
                now = _dt.now()
                future = now + timedelta(days=days)
                domain = [
                    ('start', '>=', str(now)),
                    ('start', '<=', str(future)),
                ]
                if args.get('advisor_name'):
                    domain.append(('user_id.name', 'ilike', args['advisor_name']))
                # Try estate calendar events first
                try:
                    events = env['calendar.event'].sudo().search(domain, order='start asc', limit=20)
                    result = []
                    for e in events:
                        prop = getattr(e, 'property_id', None)
                        result.append({
                            'id': e.id,
                            'titulo': e.name,
                            'inicio': str(e.start)[:16],
                            'fin': str(e.stop)[:16] if e.stop else '',
                            'propiedad': prop.title if prop else '',
                            'asesor': e.user_id.name if e.user_id else '',
                            'tipo': getattr(e, 'appointment_type', '') or '',
                            'estado_visita': getattr(e, 'visit_state', '') or '',
                        })
                    return json.dumps({'visitas': result, 'total': len(result)}, ensure_ascii=False)
                except Exception as ev_err:
                    return json.dumps({'error': str(ev_err)})

            # ── C5: Resumen de Cliente ──────────────────────────────────────────
            elif tool_name == 'get_client_summary':
                partner = None
                if args.get('partner_id'):
                    partner = env['res.partner'].sudo().browse(int(args['partner_id']))
                    if not partner.exists():
                        partner = None
                if not partner and args.get('partner_name'):
                    partner = env['res.partner'].sudo().search(
                        [('name', 'ilike', args['partner_name'])], limit=1)
                if not partner:
                    return json.dumps({'error': 'Cliente no encontrado'})

                leads = env['crm.lead'].sudo().search([('partner_id', '=', partner.id)], limit=10)
                contracts = env['estate.contract'].sudo().search([('partner_id', '=', partner.id)])
                payments_pending = env['estate.payment'].sudo().search([
                    ('partner_id', '=', partner.id), ('state', '=', 'pending')]) if hasattr(env['estate.payment']._fields, 'partner_id') else []
                try:
                    visits = env['calendar.event'].sudo().search([
                        ('partner_ids', 'in', [partner.id])], order='start desc', limit=5)
                    visit_list = [{'titulo': v.name, 'fecha': str(v.start)[:16]} for v in visits]
                except Exception:
                    visit_list = []

                summary = {
                    'id': partner.id,
                    'nombre': partner.name,
                    'email': partner.email or '',
                    'telefono': partner.phone or '',
                    'leads': [{'id': l.id, 'nombre': l.name, 'temperatura': l.lead_temperature,
                                'etapa': l.stage_id.name if l.stage_id else '',
                                'presupuesto': l.client_budget} for l in leads],
                    'contratos': [{'id': c.id, 'tipo': c.contract_type,
                                    'estado': c.state, 'monto': c.amount,
                                    'propiedad': c.property_id.title if c.property_id else ''
                                    } for c in contracts],
                    'ultimas_visitas': visit_list,
                    'total_leads': len(leads),
                    'total_contratos': len(contracts),
                }
                return json.dumps(summary, ensure_ascii=False)

            # ── C6: Cotización PDF ──────────────────────────────────────────────
            elif tool_name == 'generate_quote_pdf':
                lead_id = int(args.get('lead_id', 0))
                if not lead_id:
                    return json.dumps({'error': 'lead_id requerido'})
                lead = env['crm.lead'].sudo().browse(lead_id)
                if not lead.exists():
                    return json.dumps({'error': f'Lead #{lead_id} no encontrado'})
                # Use the property from arg or from lead
                prop_id = args.get('property_id') or (lead.target_property_id.id if lead.target_property_id else None)
                if not prop_id:
                    return json.dumps({'error': 'No hay propiedad asignada al lead. Asigna una primero con update_lead.'})
                base_url = env['ir.config_parameter'].sudo().get_param('web.base.url', 'http://localhost:8069')
                pdf_url = f"{base_url}/report/pdf/estate_crm.action_report_cotizacion_lead/{lead_id}"
                return json.dumps({
                    'success': True,
                    'pdf_url': pdf_url,
                    'mensaje': f"Cotización generada para Lead #{lead_id} — [{lead.name}]({pdf_url})",
                    'link': pdf_url,
                }, ensure_ascii=False)

            # ── HERRAMIENTA UNIVERSAL: SQL de solo lectura ──────────────────
            elif tool_name == 'query_database':
                sql = (args.get('sql') or '').strip()
                if not sql:
                    return json.dumps({'error': 'Se requiere una consulta SQL'})
                # Security: only allow SELECT statements
                sql_upper = sql.upper().lstrip()
                forbidden = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'CREATE',
                             'TRUNCATE', 'GRANT', 'REVOKE', 'EXECUTE', 'COPY']
                if not sql_upper.startswith('SELECT') and not sql_upper.startswith('WITH'):
                    return json.dumps({'error': 'Solo se permiten consultas SELECT (solo lectura)'})
                for word in forbidden:
                    # Check for forbidden keywords as whole words (not inside column names)
                    import re
                    if re.search(rf'\b{word}\b', sql_upper):
                        return json.dumps({'error': f'Operación {word} no permitida. Solo SELECT.'})
                # Force LIMIT if not present
                if 'LIMIT' not in sql_upper:
                    sql = sql.rstrip(';') + ' LIMIT 50'
                try:
                    env.cr.execute(sql)
                    columns = [desc[0] for desc in env.cr.description] if env.cr.description else []
                    rows = env.cr.dictfetchall()
                    return json.dumps({
                        'columns': columns,
                        'rows': rows,
                        'row_count': len(rows),
                        'explanation': args.get('explanation', ''),
                    }, ensure_ascii=False, default=str)
                except Exception as sql_err:
                    return json.dumps({'error': f'Error SQL: {str(sql_err)}'})

            return json.dumps({'error': f'Herramienta desconocida: {tool_name}'})

        except Exception as e:
            _logger.error("Error ejecutando herramienta %s: %s", tool_name, str(e))
            return json.dumps({'error': str(e)})

    # -----------------------------------------------------------------------
    # Report Data Tool
    # -----------------------------------------------------------------------
    def _execute_report_data(self, args, env):
        """Return aggregated data for a given report_type so the AI can render charts/tables."""
        report_type = args.get('report_type', '')
        limit = int(args.get('limit', 8))

        try:
            if report_type == 'properties_by_state':
                states = [
                    ('available', 'Disponibles'),
                    ('reserved', 'Reservadas'),
                    ('sold', 'Vendidas'),
                    ('rented', 'Alquiladas'),
                ]
                data = {label: env['estate.property'].sudo().search_count([('state', '=', key)])
                        for key, label in states}
                return json.dumps({'report': 'Propiedades por Estado', 'data': data,
                                   'chart_hint': 'circular'}, ensure_ascii=False)

            elif report_type == 'properties_by_type':
                types = env['estate.property.type'].sudo().search([], limit=limit)
                data = {}
                for t in types:
                    cnt = env['estate.property'].sudo().search_count([('property_type_id', '=', t.id)])
                    if cnt:
                        data[t.name] = cnt
                return json.dumps({'report': 'Propiedades por Tipo', 'data': data,
                                   'chart_hint': 'barra'}, ensure_ascii=False)

            elif report_type == 'sales_by_month':
                env.cr.execute("""
                    SELECT TO_CHAR(date_sold, 'Mon YYYY') as mes,
                           COUNT(*) as ventas,
                           COALESCE(SUM(price), 0) as ingresos
                    FROM estate_property
                    WHERE state = 'sold' AND date_sold IS NOT NULL
                    GROUP BY TO_CHAR(date_sold, 'Mon YYYY'), DATE_TRUNC('month', date_sold)
                    ORDER BY DATE_TRUNC('month', date_sold) DESC
                    LIMIT %s
                """, (limit,))
                rows = env.cr.dictfetchall()
                data = {r['mes']: int(r['ventas']) for r in reversed(rows)}
                return json.dumps({'report': 'Ventas por Mes', 'data': data,
                                   'chart_hint': 'linea',
                                   'detalle': rows}, ensure_ascii=False, default=str)

            elif report_type == 'visits_by_property':
                env.cr.execute("""
                    SELECT ep.title as propiedad, COUNT(ce.id) as visitas
                    FROM calendar_event ce
                    JOIN estate_property ep ON ce.property_id = ep.id
                    WHERE ce.property_id IS NOT NULL
                    GROUP BY ep.title
                    ORDER BY visitas DESC
                    LIMIT %s
                """, (limit,))
                rows = env.cr.dictfetchall()
                data = {r['propiedad']: int(r['visitas']) for r in rows}
                return json.dumps({'report': 'Visitas por Propiedad', 'data': data,
                                   'chart_hint': 'barra'}, ensure_ascii=False)

            elif report_type == 'commissions_by_advisor':
                from datetime import date
                start_month = date.today().replace(day=1)
                sold = env['estate.property'].sudo().search([
                    ('state', '=', 'sold'),
                    ('date_sold', '>=', start_month),
                    ('user_id', '!=', False),
                ])
                data = {}
                for p in sold:
                    name = p.user_id.name
                    data[name] = round(data.get(name, 0) + (p.commission_amount or 0), 2)
                data = {k: v for i, (k, v) in enumerate(
                    sorted(data.items(), key=lambda x: x[1], reverse=True)
                ) if i < limit}
                return json.dumps({'report': 'Comisiones por Asesor (Mes)', 'data': data,
                                   'chart_hint': 'barra'}, ensure_ascii=False)

            elif report_type == 'contracts_by_type':
                types = [('sale', 'Venta'), ('rent', 'Alquiler'), ('exclusivity', 'Exclusividad')]
                data = {label: env['estate.contract'].sudo().search_count(
                    [('contract_type', '=', key), ('state', '=', 'active')])
                        for key, label in types}
                return json.dumps({'report': 'Contratos Activos por Tipo', 'data': data,
                                   'chart_hint': 'circular'}, ensure_ascii=False)

            elif report_type == 'expenses_by_type':
                env.cr.execute("""
                    SELECT expense_type, COALESCE(SUM(amount), 0) as total
                    FROM estate_property_expense
                    WHERE state != 'cancelled'
                    GROUP BY expense_type
                    ORDER BY total DESC
                    LIMIT %s
                """, (limit,))
                rows = env.cr.dictfetchall()
                data = {r['expense_type']: float(f"{float(r['total']):.2f}") for r in rows}
                return json.dumps({'report': 'Gastos por Tipo', 'data': data,
                                   'chart_hint': 'circular'}, ensure_ascii=False)

            elif report_type == 'offers_by_state':
                states = [
                    ('draft', 'Borrador'), ('submitted', 'Presentada'),
                    ('countered', 'Contraoferta'), ('accepted', 'Aceptada'),
                    ('rejected', 'Rechazada'), ('expired', 'Expirada'),
                ]
                data = {label: env['estate.property.offer'].sudo().search_count([('state', '=', key)])
                        for key, label in states}
                data = {k: v for k, v in data.items() if v > 0}
                return json.dumps({'report': 'Ofertas por Estado', 'data': data,
                                   'chart_hint': 'barra'}, ensure_ascii=False)

            elif report_type == 'leads_by_temperature':
                temps = [('cold', 'Frío'), ('warm', 'Tibio'), ('hot', 'Caliente'), ('boiling', 'Hirviendo')]
                data = {label: env['crm.lead'].sudo().search_count(
                    [('lead_temperature', '=', key), ('type', '=', 'lead')])
                        for key, label in temps}
                return json.dumps({'report': 'Leads por Temperatura', 'data': data,
                                   'chart_hint': 'barra'}, ensure_ascii=False)

            elif report_type == 'payments_by_method':
                env.cr.execute("""
                    SELECT payment_method, COALESCE(SUM(amount), 0) as total
                    FROM estate_payment
                    WHERE state = 'paid'
                    GROUP BY payment_method
                    ORDER BY total DESC
                    LIMIT %s
                """, (limit,))
                rows = env.cr.dictfetchall()
                data = {r['payment_method']: float(f"{float(r['total']):.2f}") for r in rows}
                return json.dumps({'report': 'Pagos por Método', 'data': data,
                                   'chart_hint': 'circular'}, ensure_ascii=False)

            elif report_type == 'days_on_market_by_type':
                env.cr.execute("""
                    SELECT pt.name as tipo, ROUND(AVG(ep.days_on_market)::numeric, 1) as promedio
                    FROM estate_property ep
                    JOIN estate_property_type pt ON ep.property_type_id = pt.id
                    WHERE ep.state = 'sold' AND ep.days_on_market > 0
                    GROUP BY pt.name
                    ORDER BY promedio DESC
                    LIMIT %s
                """, (limit,))
                rows = env.cr.dictfetchall()
                data = {r['tipo']: float(r['promedio']) for r in rows}
                return json.dumps({'report': 'Días Promedio en Mercado por Tipo', 'data': data,
                                   'chart_hint': 'barra'}, ensure_ascii=False)

            return json.dumps({'error': f'report_type desconocido: {report_type}'})

        except Exception as e:
            _logger.error("Error en get_report_data(%s): %s", report_type, str(e))
            return json.dumps({'error': str(e)})

    # -----------------------------------------------------------------------
    # OpenAI with Tool Calling
    # -----------------------------------------------------------------------
    def _query_chatgpt_with_tools(self, api_key, model, temperature, max_tokens,
                                   system_prompt, message, history):
        """Query OpenAI ChatGPT with conversation history and tool calling."""
        if not OPENAI_AVAILABLE:
            return '❌ La librería openai no está instalada. Ejecute: pip install openai'

        client = openai.OpenAI(api_key=api_key)

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": message})

        max_iterations = 4
        for _ in range(max_iterations):
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=TOOLS_OPENAI,
                tool_choice="auto",
            )
            choice = response.choices[0]

            if choice.finish_reason == 'tool_calls':
                # Execute each tool call and append results
                assistant_msg = choice.message
                messages.append(assistant_msg)
                for tc in (assistant_msg.tool_calls or []):
                    try:
                        args = json.loads(tc.function.arguments)
                    except (json.JSONDecodeError, TypeError):
                        args = {}
                    tool_result = self._execute_tool(tc.function.name, args)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": tool_result,
                    })
            else:
                return choice.message.content

        return choice.message.content or '❌ Sin respuesta tras múltiples iteraciones.'

    # -----------------------------------------------------------------------
    # Gemini with Tool Calling (new SDK)
    # -----------------------------------------------------------------------
    def _query_gemini_with_tools(self, api_key, model, temperature, max_tokens,
                                  system_prompt, message, history):
        """Query Google Gemini with conversation history and tool calling."""
        if not GEMINI_AVAILABLE:
            return '❌ Las librerías de Google Gemini no están instaladas.'

        if NEW_GEMINI_SDK:
            import time as _time
            last_error = None
            # Retry hasta 3 veces en caso de 503 UNAVAILABLE
            for attempt in range(3):
                try:
                    client = new_genai.Client(
                        api_key=api_key,
                        http_options=new_genai.types.HttpOptions(api_version='v1beta'),
                    )

                    # Build function declarations for Gemini
                    func_declarations = []
                    for tool_def in TOOLS_OPENAI:
                        fn = tool_def['function']
                        params = fn.get('parameters', {})
                        properties = {}
                        for prop_name, prop_def in params.get('properties', {}).items():
                            gtype = new_genai.types.Type.STRING
                            if prop_def.get('type') == 'number':
                                gtype = new_genai.types.Type.NUMBER
                            elif prop_def.get('type') == 'integer':
                                gtype = new_genai.types.Type.INTEGER
                            properties[prop_name] = new_genai.types.Schema(
                                type=gtype,
                                description=prop_def.get('description', ''),
                            )
                        gemini_schema = new_genai.types.Schema(
                            type=new_genai.types.Type.OBJECT,
                            properties=properties,
                        ) if properties else None
                        func_declarations.append(
                            new_genai.types.FunctionDeclaration(
                                name=fn['name'],
                                description=fn.get('description', ''),
                                parameters=gemini_schema,
                            )
                        )

                    gemini_tool = new_genai.types.Tool(function_declarations=func_declarations)

                    # Build contents (history + current message)
                    contents = []
                    for h in history:
                        role = 'user' if h['role'] == 'user' else 'model'
                        contents.append(new_genai.types.Content(
                            role=role,
                            parts=[new_genai.types.Part.from_text(text=h['content'])],
                        ))
                    contents.append(new_genai.types.Content(
                        role='user',
                        parts=[new_genai.types.Part.from_text(text=message)],
                    ))

                    config = new_genai.types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=temperature,
                        max_output_tokens=max_tokens,
                        tools=[gemini_tool],
                    )

                    max_iterations = 4
                    for _ in range(max_iterations):
                        response = client.models.generate_content(
                            model=model or _DEFAULT_GEMINI_MODEL,
                            contents=contents,
                            config=config,
                        )
                        candidate = response.candidates[0] if response.candidates else None
                        if not candidate:
                            break

                        # Check for function calls
                        function_calls = []
                        text_parts = []
                        for part in (candidate.content.parts or []):
                            if hasattr(part, 'function_call') and part.function_call:
                                function_calls.append(part.function_call)
                            elif hasattr(part, 'text') and part.text:
                                text_parts.append(part.text)

                        if function_calls:
                            # Append model response
                            contents.append(candidate.content)
                            # Execute tools and append results
                            function_responses = []
                            for fc in function_calls:
                                fc_args = dict(fc.args) if fc.args else {}
                                tool_result_str = self._execute_tool(fc.name, fc_args)
                                try:
                                    tool_result = json.loads(tool_result_str)
                                    if not isinstance(tool_result, dict):
                                        tool_result = {'result': tool_result}
                                except Exception:
                                    tool_result = {'result': tool_result_str}
                                function_responses.append(
                                    new_genai.types.Part.from_function_response(
                                        name=fc.name,
                                        response=tool_result,
                                    )
                                )
                            contents.append(new_genai.types.Content(
                                role='user',
                                parts=function_responses,
                            ))
                        else:
                            return ''.join(text_parts) or response.text

                    return response.text or '❌ Sin respuesta tras múltiples iteraciones.'

                except Exception as e:
                    last_error = e
                    err_str = str(e)
                    etype, emsg, esecs = _parse_gemini_error(err_str)
                    if etype == '429':
                        # Cuota agotada — no reintentar, devolver mensaje claro
                        _logger.warning("Gemini 429 cuota agotada: %s", err_str[:200])
                        return emsg
                    if etype == '503':
                        wait = 5 * (attempt + 1)
                        _logger.warning("Gemini 503 intento %d/3 — esperando %ds", attempt + 1, wait)
                        _time.sleep(wait)
                        continue
                    # Otro error — no reintentar
                    _logger.error("Error Gemini: %s", err_str)
                    return f'❌ Error con Gemini: {err_str}'

            # Agotados los reintentos 503
            return (
                '❌ Gemini no disponible tras 3 intentos (alta demanda). '
                'Prueba con **gemini-2.5-flash** o baja los tokens máximos en Ajustes → Agente IA.'
            )

        return "❌ Error: SDK google-genai no disponible. Ejecute: pip install google-genai"

    # -----------------------------------------------------------------------
    # System Context
    # -----------------------------------------------------------------------
    def _get_system_context(self):
        """Get comprehensive system data for AI context."""
        env = request.env
        props = env['estate.property'].sudo().search([])
        available = props.filtered(lambda p: p.state == 'available')
        sold = props.filtered(lambda p: p.state == 'sold')
        rented = props.filtered(lambda p: p.state == 'rented')
        total_value = sum(props.mapped('price'))
        clients = env['res.partner'].sudo().search([('active', '=', True)])
        leads = env['crm.lead'].sudo().search([])
        pipeline_stats = {}
        for lead in leads:
            stage = lead.stage_id.name or 'Nuevo'
            pipeline_stats[stage] = pipeline_stats.get(stage, 0) + 1
        invoices = env['account.move'].sudo().search([('move_type', '=', 'out_invoice')])
        total_invoiced = sum(invoices.mapped('amount_total'))
        total_commissions = sum(props.filtered(lambda p: p.state == 'sold').mapped('commission_amount'))
        try:
            attendances = env['hr.attendance'].sudo().search([('check_out', '=', False)])
            present_count = len(attendances)
        except Exception:
            present_count = 0

        context = f"""== RESUMEN EJECUTIVO INMOBILIARIO ==
INVENTARIO: {len(props)} propiedades (${total_value:,.2f}) | {len(available)} Disponibles, {len(sold)} Vendidas, {len(rented)} Alquiladas.
FINANZAS: Total Facturado: ${total_invoiced:,.2f} | Comisiones: ${total_commissions:,.2f} | Facturas: {len(invoices)}
CRM: {len(clients)} clientes | {len(leads)} leads | Etapas: {pipeline_stats}
PERSONAL: {present_count} agentes con check-in activo
TOP 10 DISPONIBLES:
"""
        for p in available[:10]:
            context += f"  - {p.name} | {p.title} | {p.city} | ${p.price:,.2f} | {p.property_type_id.name}\n"
        return context

    # -----------------------------------------------------------------------
    # Query Classification
    # -----------------------------------------------------------------------
    def _classify_query(self, message):
        msg = message.lower()
        # Report keywords have HIGHEST priority (even if message also mentions "propiedad")
        if any(w in msg for w in ['reporte', 'informe', 'estadístic', 'dashboard', 'resumen',
                                    'gráfico', 'grafico', 'comision', 'ingreso', 'por estado',
                                    'por tipo', 'por mes', 'por asesor', 'tendencia', 'cuántos hay',
                                    'cuantos hay', 'desglose']):
            return 'report'
        elif any(w in msg for w in ['recuerda', 'memoria', 'anota', 'olvida', 'preferencia']):
            return 'memory'
        elif any(w in msg for w in ['contrato', 'pago', 'cuota', 'vencid', 'arrendamiento', 'alquiler']):
            return 'contract'
        elif any(w in msg for w in ['lead', 'prospecto', 'cliente', 'crm', 'oportunidad', 'temperatura',
                                    'interaccion', 'matchmaker']):
            return 'client'
        elif any(w in msg for w in ['propiedad', 'casa', 'departamento', 'terreno', 'oficina', 'inmueble',
                                   'precio', 'área', 'habitacion', 'baño', 'duplica', 'archiva', 'elimina']):
            return 'property'
        return 'general'

    # Smart tool selection — send only relevant tools based on query type to save tokens
    # -----------------------------------------------------------------------
    _TOOLS_BY_CATEGORY = {
        'property': [
            'search_properties', 'get_property_detail', 'create_property', 'update_property',
            'archive_property', 'delete_property', 'duplicate_property', 'reserve_property',
            'sell_property', 'schedule_visit', 'get_market_stats', 'batch_update_properties',
            'recalculate_avm_ai', 'generate_and_apply_description', 'compare_properties',
            'get_trend_analysis', 'get_report_data', 'query_database',
        ],
        'client': [
            'get_leads', 'create_lead', 'update_lead', 'archive_lead', 'batch_archive_leads',
            'create_crm_activity', 'send_whatsapp_lead', 'schedule_visit', 'search_properties',
            'analyze_lead_probability', 'send_email', 'search_contacts', 'get_client_summary',
            'generate_quote_pdf', 'get_upcoming_visits', 'query_database',
        ],
        'contract': [
            'get_payments_contracts', 'create_contract', 'update_contract', 'create_payment',
            'approve_payment', 'cancel_payment', 'create_offer', 'create_commission',
            'approve_commission', 'analyze_churn_risk', 'generate_pdf_report', 'query_database',
        ],
        'report': [
            'get_report_data', 'get_dashboard_summary', 'get_market_stats', 'get_payments_contracts',
            'get_leads', 'search_properties', 'generate_pdf_report', 'get_trend_analysis',
            'get_upcoming_visits', 'query_database',
        ],
        'memory': [
            'save_memory', 'recall_memory', 'get_leads', 'search_properties', 'query_database',
        ],
        'general': [
            'search_properties', 'get_property_detail', 'get_leads', 'get_market_stats',
            'get_dashboard_summary', 'create_lead', 'create_property', 'update_property',
            'update_lead', 'schedule_visit', 'get_payments_contracts', 'save_memory', 'recall_memory',
            'search_contacts', 'get_client_summary', 'compare_properties', 'get_trend_analysis',
            'get_upcoming_visits', 'get_report_data', 'query_database',
        ],
    }

    def _get_tools_for_query(self, query_type):
        """Return only the tools relevant to this query type, reducing token usage."""
        allowed = self._TOOLS_BY_CATEGORY.get(query_type, self._TOOLS_BY_CATEGORY['general'])
        return [t for t in TOOLS_OPENAI if t['function']['name'] in allowed]

    # -----------------------------------------------------------------------
    # Public API endpoints
    # -----------------------------------------------------------------------
    # -----------------------------------------------------------------------
    # Streaming Chat Endpoint (SSE) — faster perceived response
    # -----------------------------------------------------------------------
    @http.route('/estate_ai/chat/stream', type='http', auth='user', methods=['POST'], csrf=False)
    def chat_stream(self, **kwargs):
        """
        Streaming SSE endpoint for the AI chat.
        Sends status events during tool-calling, then streams the final text
        word-by-word so the user sees the response as it is built.
        """
        try:
            data = json.loads(request.httprequest.data or '{}')
        except Exception:
            data = kwargs
        message = (data.get('message') or '').strip()
        session_id = (data.get('session_id') or '').strip() or None
        if not message:
            def _empty():
                yield 'data: {"error":"Mensaje vacío"}\n\ndata: [DONE]\n\n'
            return request.make_response(_empty(), headers=[
                ('Content-Type', 'text/event-stream; charset=utf-8'),
                ('Cache-Control', 'no-cache'),
            ])

        # Pre-fetch ALL database-dependent data NOW, while the cursor is still open.
        # The generate() generator runs AFTER the request cursor is closed (Werkzeug SSE).
        user_id = request.env.user.id
        db_name = request.env.cr.dbname

        ICP = request.env['ir.config_parameter'].sudo()
        ai_active = ICP.get_param('estate_ai.active', 'True')
        api_key = ICP.get_param('estate_ai.api_key', '')
        model = _normalize_gemini_model(ICP.get_param('estate_ai.model', ''))
        temperature = float(ICP.get_param('estate_ai.temperature', '0.7'))
        # Default 800 tokens — sufficient for most answers, avoids 503 overload
        max_tokens = int(ICP.get_param('estate_ai.max_tokens', '800'))
        system_extra = ICP.get_param('estate_ai.system_prompt', '')

        context = self._get_system_context()
        history = self._get_conversation_history(user_id)
        query_type = self._classify_query(message)
        # Only load tools relevant to this query — reduces token count significantly
        active_tools = self._get_tools_for_query(query_type)
        ctrl = self

        full_system = (
            f"{system_extra}\n\n"
            "Eres el Asistente Ejecutivo Inteligente de la Inmobiliaria con acceso COMPLETO al sistema. "
            "Puedes CONSULTAR, CREAR, ACTUALIZAR y CONTROLAR: propiedades, leads, visitas, contratos y más. "
            "Responde siempre en español, de forma concisa y profesional. "
            "Cuando el usuario pida crear, actualizar o gestionar algo, usa las herramientas disponibles y confirma con el ID resultante.\n\n"
            "REGLA ABSOLUTA: NUNCA digas 'no puedo', 'no tengo la capacidad', 'no tengo acceso' o 'no es posible'. "
            "Tienes la herramienta query_database que te permite ejecutar CUALQUIER consulta SQL SELECT "
            "contra toda la base de datos. Si ninguna otra herramienta sirve, usa query_database con un SQL "
            "apropiado para responder la pregunta. Tienes acceso a TODA la información del sistema.\n\n"
            "REGLA OBLIGATORIA PARA REPORTES Y GRÁFICOS:\n"
            "Cuando el usuario pida reporte, gráfico, estadística, resumen de datos, desglose, o use palabras como "
            "'muéstrame por', 'cuántos hay por', 'reporte de', 'gráfico de' → DEBES llamar a get_report_data. "
            "NUNCA respondas con solo texto cuando se pide un gráfico o reporte.\n"
            "Con los datos recibidos SIEMPRE genera TODOS los gráficos posibles que apliquen.\n"
            "Tipos de gráfico disponibles:\n"
            "- [GRAFICO:barra,Label1:Valor1,Label2:Valor2,...] → barras horizontales (ideal para comparar cantidades)\n"
            "- [GRAFICO:circular,Label1:Valor1,Label2:Valor2,...] → diagrama de torta/pie (ideal para proporciones/porcentajes)\n"
            "- [GRAFICO:linea,Label1:Valor1,Label2:Valor2,...] → línea temporal (ideal para evolución en el tiempo)\n\n"
            "REGLA: Elige automáticamente el MEJOR tipo de gráfico según los datos:\n"
            "- Datos temporales (meses, años) → linea\n"
            "- Proporciones/distribuciones (estados, tipos) → circular\n"
            "- Comparaciones de cantidades/rankings → barra\n"
            "- Si hay duda, usa barra (es el más versátil)\n"
            "- Si los datos permiten más de una visualización útil, incluye MÚLTIPLES gráficos "
            "(ej: uno circular para % y uno de barra para cantidades absolutas).\n"
            "Después de los gráficos incluye una tabla Markdown con los mismos datos.\n"
            "report_types: properties_by_state, properties_by_type, sales_by_month, visits_by_property, "
            "commissions_by_advisor, contracts_by_type, expenses_by_type, offers_by_state, "
            "leads_by_temperature, payments_by_method, days_on_market_by_type.\n\n"
            f"CONTEXTO ACTUAL:\n{context}"
        )

        def sse(payload):
            return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

        def _tool_with_cursor(tool_name, args):
            """Execute a tool using a fresh DB cursor (safe to call inside generator)."""
            from odoo.modules.registry import Registry
            from odoo import api as odoo_api
            with Registry(db_name).cursor() as new_cr:
                new_env = odoo_api.Environment(new_cr, user_id, {})
                result = ctrl._execute_tool(tool_name, args, env=new_env)
                new_cr.commit()
                return result

        def _save_history(final_text):
            """Persist chat history with a fresh DB cursor."""
            from odoo.modules.registry import Registry
            from odoo import api as odoo_api
            with Registry(db_name).cursor() as new_cr:
                new_env = odoo_api.Environment(new_cr, user_id, {})
                vals = {
                    'user_id': user_id,
                    'query': message,
                    'response': final_text,
                    'query_type': query_type,
                    'processing_time': 0,
                }
                if session_id:
                    vals['session_id'] = session_id
                new_env['estate.ai.chat.history'].sudo().create(vals)
                new_cr.commit()

        def generate():
            # All values come from closure — no ORM calls here
            if ai_active != 'True':
                yield sse({'error': '⚠️ Agente IA desactivado.'})
                yield 'data: [DONE]\n\n'
                return

            if not api_key:
                yield sse({'error': '⚠️ No hay API Key. Vaya a Configuración > Agente IA.'})
                yield 'data: [DONE]\n\n'
                return

            if not NEW_GEMINI_SDK:
                yield sse({'error': '❌ Librería google-genai no instalada.'})
                yield 'data: [DONE]\n\n'
                return

            import time as _time
            tool_labels = {
                'search_properties': '🏠 Buscando propiedades',
                'get_property_detail': '🔎 Consultando propiedad',
                'get_leads': '👥 Consultando leads CRM',
                'get_market_stats': '📊 Calculando estadísticas',
                'create_crm_activity': '📝 Creando actividad',
                'create_lead': '➕ Creando lead',
                'create_property': '🏗️ Registrando propiedad',
                'update_lead': '✏️ Actualizando lead',
                'update_property': '✏️ Actualizando propiedad',
                'delete_property': '🗑️ Eliminando propiedad',
                'duplicate_property': '📋 Duplicando propiedad',
                'schedule_visit': '🗓️ Agendando visita',
                'reserve_property': '🔒 Reservando propiedad',
                'sell_property': '🤝 Cerrando venta',
                'send_whatsapp_lead': '📱 Generando enlace WhatsApp',
                'archive_lead': '📦 Archivando lead',
                'archive_property': '📦 Archivando propiedad',
                'get_payments_contracts': '💳 Consultando pagos',
                'get_dashboard_summary': '📊 Generando resumen',
                'create_contract': '📄 Creando contrato',
                'create_payment': '💰 Registrando pago',
                'create_offer': '🤝 Creando oferta',
                'approve_payment': '✅ Aprobando pago',
                'generate_pdf_report': '📄 Generando PDF',
                'save_memory': '🧠 Guardando memoria',
                'recall_memory': '🧠 Consultando memorias',
                'analyze_lead_probability': '🤖 Analizando lead',
                'analyze_churn_risk': '⚠️ Analizando riesgo',
                'recalculate_avm_ai': '💡 Calculando valoración',
                'generate_and_apply_description': '✍️ Generando descripción',
                'send_email': '📧 Enviando email',
                'get_report_data': '📊 Cargando datos',
                'query_database': '🔍 Consultando base de datos',
            }

            last_err = None
            for _attempt in range(3):
                try:
                    client = new_genai.Client(
                        api_key=api_key,
                        http_options=new_genai.types.HttpOptions(api_version='v1beta'),
                    )

                    # Build function declarations — only relevant tools (saves tokens)
                    func_decls = []
                    for td in active_tools:
                        fn = td['function']
                        props = {}
                        for pname, pdef in fn.get('parameters', {}).get('properties', {}).items():
                            gtype = new_genai.types.Type.STRING
                            if pdef.get('type') == 'number':
                                gtype = new_genai.types.Type.NUMBER
                            elif pdef.get('type') == 'integer':
                                gtype = new_genai.types.Type.INTEGER
                            props[pname] = new_genai.types.Schema(
                                type=gtype,
                                description=pdef.get('description', ''),
                            )
                        func_decls.append(new_genai.types.FunctionDeclaration(
                            name=fn['name'],
                            description=fn.get('description', ''),
                            parameters=new_genai.types.Schema(
                                type=new_genai.types.Type.OBJECT,
                                properties=props,
                            ) if props else None,
                        ))

                    gemini_tool = new_genai.types.Tool(function_declarations=func_decls)
                    cfg = new_genai.types.GenerateContentConfig(
                        system_instruction=full_system,
                        temperature=temperature,
                        max_output_tokens=max_tokens,
                        tools=[gemini_tool],
                    )

                    # Build contents from pre-fetched history
                    contents = []
                    for h in history:
                        role = 'user' if h['role'] == 'user' else 'model'
                        contents.append(new_genai.types.Content(
                            role=role,
                            parts=[new_genai.types.Part.from_text(text=h['content'])],
                        ))
                    contents.append(new_genai.types.Content(
                        role='user',
                        parts=[new_genai.types.Part.from_text(text=message)],
                    ))

                    # Tool-calling loop (max 4 rounds)
                    final_text = ''
                    for _ in range(4):
                        response = client.models.generate_content(
                            model=model, contents=contents, config=cfg)
                        candidate = response.candidates[0] if response.candidates else None
                        if not candidate:
                            break

                        fn_calls, text_parts = [], []
                        for part in (candidate.content.parts or []):
                            if hasattr(part, 'function_call') and part.function_call:
                                fn_calls.append(part.function_call)
                            elif hasattr(part, 'text') and part.text:
                                text_parts.append(part.text)

                        if not fn_calls:
                            final_text = ''.join(text_parts) or (response.text or '')
                            break

                        # Notify which tools are running
                        names = [tool_labels.get(fc.name, fc.name) for fc in fn_calls]
                        yield sse({'status': ' · '.join(names) + '...'})

                        contents.append(candidate.content)
                        fn_responses = []
                        for fc in fn_calls:
                            fc_args = dict(fc.args) if fc.args else {}
                            result_str = _tool_with_cursor(fc.name, fc_args)
                            try:
                                result = json.loads(result_str)
                                if not isinstance(result, dict):
                                    result = {'result': result}
                            except Exception:
                                result = {'result': result_str}
                            fn_responses.append(new_genai.types.Part.from_function_response(
                                name=fc.name, response=result))
                        contents.append(new_genai.types.Content(role='user', parts=fn_responses))
                        yield sse({'status': '✍️ Redactando respuesta...'})

                    # Stream final text word by word
                    if final_text:
                        chunk = ''
                        for word in final_text.split(' '):
                            chunk += word + ' '
                            if len(chunk) >= 12:
                                yield sse({'text': chunk})
                                chunk = ''
                        if chunk:
                            yield sse({'text': chunk})
                    else:
                        yield sse({'text': '❌ No se obtuvo respuesta del modelo.'})

                    # Persist history
                    try:
                        _save_history(final_text)
                    except Exception as he:
                        _logger.warning("No se pudo guardar historial IA: %s", str(he))

                    break  # success — exit retry loop

                except Exception as e:
                    last_err = e
                    err_str = str(e)
                    etype, emsg, esecs = _parse_gemini_error(err_str)
                    if etype == '429':
                        _logger.warning("Gemini 429 cuota agotada (streaming)")
                        yield sse({'text': emsg})
                        break  # No reintentar — cuota es diaria
                    if etype == '503':
                        wait = 5 * (_attempt + 1)
                        _logger.warning("Gemini 503 intento %d/3 — esperando %ds", _attempt + 1, wait)
                        yield sse({'status': f'⏳ Servidor ocupado, reintentando en {wait}s...'})
                        _time.sleep(wait)
                        continue
                    # Otro error no reintentable
                    _logger.error("Error en streaming IA: %s", err_str)
                    yield sse({'text': f'❌ Error: {err_str}'})
                    break
            else:
                # 3 intentos 503 fallidos
                yield sse({'text': (
                    '❌ Gemini no disponible (alta demanda). '
                    'Ve a **Ajustes → Agente IA** y cambia el modelo a `gemini-2.5-flash` '
                    'o baja los tokens máximos a 500.'
                )})

            yield 'data: [DONE]\n\n'

        return request.make_response(generate(), headers=[
            ('Content-Type', 'text/event-stream; charset=utf-8'),
            ('Cache-Control', 'no-cache, no-transform'),
            ('X-Accel-Buffering', 'no'),
        ])

    @http.route('/estate_ai/history', type='jsonrpc', auth='user', methods=['POST'])
    def get_history(self, limit=20, **kwargs):
        """Get chat history for current user."""
        history = request.env['estate.ai.chat.history'].search(
            [('user_id', '=', request.env.user.id)],
            limit=limit, order='create_date desc')
        return [{'query': h.query, 'date': h.create_date.strftime('%d/%m/%Y %H:%M')}
                for h in reversed(history)]

    @http.route('/estate_ai/clear', type='jsonrpc', auth='user', methods=['POST'])
    def clear_history(self, session_id=None, **kwargs):
        """Clear chat history for current user. If session_id given, clears only that session."""
        domain = [('user_id', '=', request.env.user.id)]
        if session_id:
            domain.append(('session_id', '=', session_id))
        request.env['estate.ai.chat.history'].search(domain).unlink()
        return True

    @http.route('/estate_ai/sessions', type='jsonrpc', auth='user', methods=['POST'])
    def get_sessions(self, **kwargs):
        """Return list of distinct chat sessions for the current user."""
        env = request.env
        user_id = env.user.id
        # Get all history records ordered by date, group by session_id in Python
        records = env['estate.ai.chat.history'].sudo().search(
            [('user_id', '=', user_id)],
            order='create_date asc',
            limit=200,
        )
        sessions = {}
        for r in records:
            sid = r.session_id or 'default'
            if sid not in sessions:
                sessions[sid] = {
                    'session_id': sid,
                    'title': r.query[:60] if r.query else 'Conversación',
                    'date': r.create_date.strftime('%d/%m %H:%M'),
                    'count': 0,
                }
            sessions[sid]['count'] += 1
            sessions[sid]['date'] = r.create_date.strftime('%d/%m %H:%M')
        # Most recent first
        result = list(reversed(list(sessions.values())))
        return result[:50]

    @http.route('/estate_ai/session_messages', type='jsonrpc', auth='user', methods=['POST'])
    def get_session_messages(self, session_id=None, **kwargs):
        """Return all messages for a specific session."""
        domain = [('user_id', '=', request.env.user.id)]
        if session_id and session_id != 'default':
            domain.append(('session_id', '=', session_id))
        else:
            domain.append(('session_id', 'in', [False, '', 'default']))
        records = request.env['estate.ai.chat.history'].sudo().search(
            domain, order='create_date asc', limit=100)
        result = []
        for r in records:
            result.append({'type': 'user', 'text': r.query, 'date': r.create_date.strftime('%H:%M')})
            result.append({'type': 'bot', 'text': r.response or '', 'date': r.create_date.strftime('%H:%M')})
        return result

    @http.route('/estate_ai/suggestions', type='jsonrpc', auth='user', methods=['POST'])
    def get_suggestions(self, context=None, **kwargs):
        """Get dynamic suggested queries based on current system state."""
        from datetime import date, timedelta
        env = request.env
        suggestions = []

        try:
            # Context-aware suggestions based on system state
            today = date.today()

            # Overdue payments alert
            overdue = env['estate.payment'].sudo().search_count([
                ('state', '=', 'pending'), ('date', '<', today)])
            if overdue:
                suggestions.append(f'Muéstrame los {overdue} pagos vencidos y qué hacer')

            # Hot leads without activity
            stale_hot = env['crm.lead'].sudo().search_count([
                ('lead_temperature', 'in', ['hot', 'boiling']),
                ('write_date', '<=', str(fields.Datetime.now() - timedelta(days=5))),
                ('type', '=', 'opportunity'),
            ])
            if stale_hot:
                suggestions.append(f'Hay {stale_hot} leads calientes sin actividad — ¿qué hago?')

            # Properties available > 60 days
            stale_props = env['estate.property'].sudo().search_count([
                ('state', '=', 'available'),
                ('date_listed', '<=', today - timedelta(days=60)),
            ])
            if stale_props:
                suggestions.append(f'Analiza las {stale_props} propiedades sin vender en más de 60 días')

            # Visits today
            today_visits = env['calendar.event'].sudo().search_count([
                ('start', '>=', str(today)),
                ('start', '<', str(today + timedelta(days=1))),
            ])
            if today_visits:
                suggestions.append(f'¿Cuáles son mis {today_visits} visitas de hoy?')

        except Exception:
            pass

        # Always include these core suggestions
        suggestions += [
            'Dame el briefing del día',
            'Compara tendencias de este mes vs el mes pasado',
            'Busca clientes interesados en casa en Cuenca',
            '¿Cuáles son los leads más calientes del CRM?',
            'Genera un reporte de comisiones por asesor',
            'Analiza el riesgo de churn de mis contratos',
        ]

        return suggestions[:8]

    @http.route('/estate_ai/briefing', type='jsonrpc', auth='user', methods=['POST'])
    def get_briefing(self, **kwargs):
        """
        Briefing matutino: resumen ejecutivo + visitas del día + tendencias + alertas.
        Devuelve el texto del briefing directamente (sin pasar por el modelo de IA).
        """
        from datetime import date, timedelta
        from datetime import datetime as _dt
        env = request.env
        today = date.today()
        now = _dt.now()

        lines = [f"## 📋 Briefing del {today.strftime('%A %d de %B de %Y')}\n"]

        try:
            # 1. Inventario
            available = env['estate.property'].sudo().search_count([('state', '=', 'available')])
            reserved = env['estate.property'].sudo().search_count([('state', '=', 'reserved')])
            lines.append(f"**Inventario:** {available} disponibles · {reserved} reservadas\n")

            # 2. Visitas de hoy
            visits_today = env['calendar.event'].sudo().search([
                ('start', '>=', str(today)),
                ('start', '<', str(today + timedelta(days=1))),
            ], order='start asc', limit=5)
            if visits_today:
                lines.append(f"**Visitas hoy ({len(visits_today)}):**")
                for v in visits_today:
                    prop = getattr(v, 'property_id', None)
                    prop_name = prop.title if prop else ''
                    lines.append(f"  - {str(v.start)[11:16]} | {v.name} {('— ' + prop_name) if prop_name else ''}")
                lines.append('')
            else:
                lines.append("**Visitas hoy:** Ninguna programada\n")

            # 3. Alertas críticas
            alerts = []
            overdue = env['estate.payment'].sudo().search_count([
                ('state', '=', 'pending'), ('date', '<', today)])
            if overdue:
                alerts.append(f"⚠️ {overdue} pagos vencidos")

            hot_stale = env['crm.lead'].sudo().search_count([
                ('lead_temperature', 'in', ['hot', 'boiling']),
                ('write_date', '<=', str(fields.Datetime.now() - timedelta(days=7))),
                ('type', '=', 'opportunity'),
            ])
            if hot_stale:
                alerts.append(f"🔥 {hot_stale} leads calientes sin actividad en 7+ días")

            expiring = env['estate.contract'].sudo().search_count([
                ('state', '=', 'active'),
                ('date_end', '>=', str(today)),
                ('date_end', '<=', str(today + timedelta(days=30))),
            ])
            if expiring:
                alerts.append(f"📄 {expiring} contratos vencen en 30 días")

            if alerts:
                lines.append("**Alertas:**")
                for a in alerts:
                    lines.append(f"  - {a}")
                lines.append('')
            else:
                lines.append("**Alertas:** ✅ Sin alertas críticas\n")

            # 4. Tendencia del mes
            month_start = today.replace(day=1)
            sales_month = env['estate.property'].sudo().search_count([
                ('state', '=', 'sold'), ('date_sold', '>=', str(month_start))])
            leads_month = env['crm.lead'].sudo().search_count([
                ('create_date', '>=', str(month_start))])
            lines.append(f"**Este mes:** {sales_month} ventas · {leads_month} nuevos leads")

        except Exception as e:
            lines.append(f"(Error generando briefing: {e})")

        briefing_text = "\n".join(lines)

        # Log to history
        env['estate.ai.chat.history'].sudo().create({
            'user_id': env.user.id,
            'query': '/briefing',
            'response': briefing_text,
            'query_type': 'report',
        })

        return {'response': briefing_text}

    # -----------------------------------------------------------------------
    # OCR Endpoint (C1) — extract data from uploaded documents via Gemini Vision
    # -----------------------------------------------------------------------
    @http.route('/estate_ai/ocr', type='http', auth='user', methods=['POST'], csrf=False)
    def ocr_document(self, **kwargs):
        """
        Upload a file (image or PDF) and extract structured data using Gemini Vision.
        Returns JSON with extracted fields.
        """
        import base64
        import mimetypes

        try:
            uploaded_file = kwargs.get('file') or request.httprequest.files.get('file')
            extract_type = kwargs.get('extract_type', 'auto')  # auto, property, contract, identity

            if not uploaded_file:
                return request.make_response(
                    json.dumps({'error': 'No se recibió ningún archivo.'}),
                    headers=[('Content-Type', 'application/json')]
                )

            file_bytes = uploaded_file.read()
            filename = getattr(uploaded_file, 'filename', 'document')
            mime_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
            file_b64 = base64.b64encode(file_bytes).decode('utf-8')

            ICP = request.env['ir.config_parameter'].sudo()
            provider = ICP.get_param('estate_ai.provider', 'gemini')
            api_key = ICP.get_param('estate_ai.api_key', '')

            if not api_key:
                return request.make_response(
                    json.dumps({'error': 'No hay API Key configurada.'}),
                    headers=[('Content-Type', 'application/json')]
                )

            # Build extraction prompt based on type
            prompts = {
                'property': (
                    "Extrae los datos de esta propiedad inmobiliaria en JSON: "
                    "{titulo, direccion, ciudad, precio, area_m2, habitaciones, banos, descripcion}"
                ),
                'contract': (
                    "Extrae los datos de este contrato en JSON: "
                    "{tipo_contrato, nombre_propietario, nombre_inquilino, fecha_inicio, "
                    "fecha_fin, monto_mensual, direccion_propiedad}"
                ),
                'identity': (
                    "Extrae los datos de este documento de identidad en JSON: "
                    "{nombre_completo, numero_cedula, fecha_nacimiento, direccion}"
                ),
                'auto': (
                    "Analiza este documento y extrae TODOS los datos relevantes en formato JSON. "
                    "Identifica el tipo de documento y devuelve los campos más importantes."
                ),
            }
            ocr_prompt = prompts.get(extract_type, prompts['auto'])

            extracted = {}
            if GEMINI_AVAILABLE and (provider == 'gemini' or not OPENAI_AVAILABLE):
                client = new_genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model=_DEFAULT_GEMINI_MODEL,
                    contents=[
                        {
                            'parts': [
                                {'inline_data': {'mime_type': mime_type, 'data': file_b64}},
                                {'text': ocr_prompt},
                            ]
                        }
                    ]
                )
                raw_text = response.text or ''
                # Try to parse JSON from response
                import re
                json_match = re.search(r'\{[\s\S]*\}', raw_text)
                if json_match:
                    try:
                        extracted = json.loads(json_match.group())
                    except json.JSONDecodeError:
                        extracted = {'raw_text': raw_text}
                else:
                    extracted = {'raw_text': raw_text}

            elif OPENAI_AVAILABLE:
                import openai as _openai
                client = _openai.OpenAI(api_key=api_key)
                response = client.chat.completions.create(
                    model='gpt-4o',
                    messages=[{
                        'role': 'user',
                        'content': [
                            {'type': 'image_url',
                             'image_url': {'url': f'data:{mime_type};base64,{file_b64}'}},
                            {'type': 'text', 'text': ocr_prompt},
                        ]
                    }],
                    max_tokens=1000,
                )
                raw_text = response.choices[0].message.content or ''
                import re
                json_match = re.search(r'\{[\s\S]*\}', raw_text)
                if json_match:
                    try:
                        extracted = json.loads(json_match.group())
                    except json.JSONDecodeError:
                        extracted = {'raw_text': raw_text}
                else:
                    extracted = {'raw_text': raw_text}
            else:
                return request.make_response(
                    json.dumps({'error': 'No hay proveedor de IA disponible para OCR.'}),
                    headers=[('Content-Type', 'application/json')]
                )

            result = {
                'success': True,
                'filename': filename,
                'extract_type': extract_type,
                'extracted': extracted,
            }
            return request.make_response(
                json.dumps(result, ensure_ascii=False),
                headers=[('Content-Type', 'application/json; charset=utf-8')]
            )

        except Exception as e:
            _logger.error("OCR error: %s", str(e))
            return request.make_response(
                json.dumps({'error': str(e)}),
                headers=[('Content-Type', 'application/json')]
            )
