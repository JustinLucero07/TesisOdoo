# -*- coding: utf-8 -*-
"""Definiciones estaticas del agente IA: esquemas de herramientas para
function-calling y helpers puros (normalizacion de modelo, redaccion de
secretos, parseo de errores). Extraido de estate_ai_controller.py para
reducir el tamano del monolito y separar datos de logica."""
import logging

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool definitions for OpenAI function calling
# ---------------------------------------------------------------------------
TOOLS_OPENAI = [
    {
        "type": "function",
        "function": {
            "name": "search_properties",
            "description": (
                "Busca propiedades inmobiliarias en la base de datos según filtros. "
                "Cuando el usuario pida 'todas las propiedades disponibles', 'la más cara', "
                "'las más baratas', 'todas las casas', etc. → usa limit=100 para traer todas. "
                "Ordena los resultados por precio descendente por defecto."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "Ciudad de la propiedad"},
                    "property_type": {"type": "string", "description": "Tipo: casa, departamento, terreno, oficina"},
                    "max_price": {"type": "number", "description": "Precio máximo"},
                    "min_price": {"type": "number", "description": "Precio mínimo"},
                    "state": {"type": "string", "description": "Estado: available, sold, rented, reserved"},
                    "limit": {"type": "integer", "description": "Máximo de resultados (default 50, usa 100 para 'todas')"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_leads",
            "description": (
                "Obtiene leads/oportunidades del CRM con sus datos y puntuación. "
                "Usa 'stage' para listar/filtrar por etapa del pipeline (ej. 'En Proceso Cierre', "
                "'Cierre', 'Recepción', 'Perdido') — es la forma correcta de responder "
                "'¿qué leads/clientes hay en [etapa]?' o '¿cuáles son?'. NUNCA uses query_database "
                "con SQL crudo para filtrar por nombre de etapa (el campo es traducible/JSON y falla)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "stage": {"type": "string", "description": "Nombre (o parte del nombre) de la etapa del CRM a filtrar, ej. 'En Proceso Cierre'"},
                    "temperature": {"type": "string", "description": "Filtrar por temperatura: cold, warm, hot, boiling"},
                    "score": {"type": "string", "description": "Filtrar por puntuación: low, medium, high"},
                    "type": {"type": "string", "description": "'lead' o 'opportunity'. Si no se indica, incluye ambos"},
                    "lost": {"type": "boolean", "description": "true para filtrar solo leads en la etapa Perdido"},
                    "limit": {"type": "integer", "description": "Máximo de resultados (default 20, usa un número mayor para 'todos')"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_market_stats",
            "description": "Obtiene estadísticas de ventas del mercado inmobiliario: comisión promedio por venta (honorarios cobrados por la agencia), comisiones totales, días en mercado y precio promedio del inmueble (volumen por ciudad/tipo).",
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
            "name": "analyze_property_improvements",
            "description": (
                "Analiza UNA propiedad y devuelve recomendaciones CONCRETAS de qué mejorar para "
                "venderla más rápido: precio vs AVM (sobrevaluada/justa), días en mercado vs promedio, "
                "nº de fotos, calidad de descripción, GPS, leads interesados (directos + por presupuesto). "
                "Úsalo SIEMPRE que el usuario pida 'qué puedo mejorar', 'cómo mejorar' o 'recomendaciones' "
                "sobre una propiedad. Acepta ID o nombre/referencia parcial."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "property_id": {"type": "integer", "description": "ID de la propiedad"},
                    "property_name": {"type": "string", "description": "Nombre/referencia parcial (si no se sabe el ID). Usa el de la conversación reciente si aplica."},
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
                    "start_datetime": {"type": "string", "description": "Fecha y hora de la visita, ej '2026-07-15 10:00' (acepta con o sin segundos; si solo das la fecha se asume 10:00)"},
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
    # ── EXCEL EXPORT ──────────────────────────────────────────────────────
    {"type": "function", "function": {
        "name": "generate_excel_report",
        "description": "Genera un archivo Excel (.xlsx) con datos de cualquier reporte y devuelve un enlace de descarga. Usa el mismo report_type que get_report_data.",
        "parameters": {"type": "object", "required": ["report_type"], "properties": {
            "report_type": {"type": "string", "description": "Mismo report_type de get_report_data"},
            "title": {"type": "string", "description": "Título personalizado para la hoja Excel (opcional)"},
            "limit": {"type": "integer", "description": "Máximo de filas (default 50)"},
        }},
    }},
    # ── NAVEGAR A VISTA ───────────────────────────────────────────────────
    {"type": "function", "function": {
        "name": "open_report_view",
        "description": "Devuelve la URL para que el usuario navegue a una vista de reporte específica en Odoo. Úsalo cuando el usuario pida abrir, ir a, o ver una sección concreta del sistema.",
        "parameters": {"type": "object", "required": ["view_name"], "properties": {
            "view_name": {"type": "string", "description": (
                "Vista destino: dashboard | ventas_mes | ranking_asesores | tipo_propiedad | "
                "dias_mercado | comisiones | kpis_ventas | analytics_propiedades | analytics_contratos | "
                "analytics_pagos | analytics_ofertas | analytics_gastos | analytics_tasaciones | "
                "analytics_mantenimiento | crm_pipeline | crm_negocios | crm_fuentes | crm_visitas | "
                "social_facebook | social_instagram | exportar_pdf | exportar_excel | agenda_visitas"
            )},
        }},
    }},
    # ── PDF DE REPORTE ANALÍTICO ──────────────────────────────────────────
    {"type": "function", "function": {
        "name": "generate_analytics_pdf",
        "description": (
            "Genera un PDF descargable de cualquier reporte analítico del sistema "
            "(ventas, leads, comisiones, propiedades, embudo, etc.) con tabla de datos y encabezado. "
            "Devuelve un enlace de descarga directo. "
            "Úsalo cuando el usuario pida 'dame el reporte en PDF', 'descargar PDF', "
            "'exportar como PDF', 'imprimir reporte'."
        ),
        "parameters": {"type": "object", "required": ["report_type"], "properties": {
            "report_type": {"type": "string", "description": "Mismo report_type de get_report_data"},
            "title": {"type": "string", "description": "Título personalizado del reporte (opcional)"},
            "limit": {"type": "integer", "description": "Máximo de filas (default 30)"},
        }},
    }},
    # ── PACK DE MARKETING COMPLETO ────────────────────────────────────────
    {"type": "function", "function": {
        "name": "generate_marketing_pack",
        "description": (
            "Genera el pack COMPLETO de contenido de marketing para una propiedad: "
            "caption Instagram, post Facebook, mensaje WhatsApp broadcast, email, "
            "Google Ads, puntos clave y slogan. "
            "Llama a esta herramienta cuando el usuario pida: 'campaña', 'marketing', "
            "'contenido para redes', 'copies', 'publicitar', 'posts para redes', "
            "'pack de marketing', 'textos para publicar', 'quiero promover', 'anuncio'."
        ),
        "parameters": {"type": "object", "required": ["property_id"], "properties": {
            "property_id": {"type": "integer", "description": "ID de la propiedad"},
            "style": {"type": "string", "description": "Estilo: emocional (default) | formal | directo | lujoso"},
            "channels": {
                "type": "array", "items": {"type": "string"},
                "description": "Canales a incluir (vacío = todos): instagram, facebook, whatsapp, email_asunto, email_cuerpo, google_ads, puntos_clave, slogan",
            },
            "save_description": {"type": "boolean", "description": "Si True, guarda la descripción como descripción de la propiedad"},
        }},
    }},
    # ── PLAN DE CAMPAÑA DE MARKETING ─────────────────────────────────────
    {"type": "function", "function": {
        "name": "plan_marketing_campaign",
        "description": (
            "Analiza una propiedad y genera un plan de campaña de marketing personalizado: "
            "canal principal recomendado, frecuencia de publicación, buyer persona, "
            "presupuesto sugerido para Facebook Ads, checklist de lo que falta para publicar "
            "(fotos, descripción, WordPress, AVM, coordenadas), keywords SEO y calendario de contenidos. "
            "Llama a esta herramienta cuando el usuario pida: 'plan de campaña', 'estrategia de marketing', "
            "'cómo promocionar esta propiedad', 'qué me falta para publicar', 'plan de publicidad', "
            "'estrategia para vender', 'cómo llegar a más clientes', 'plan de difusión', "
            "'campaña de ventas', 'qué canal usar'."
        ),
        "parameters": {"type": "object", "required": ["property_id"], "properties": {
            "property_id": {"type": "integer", "description": "ID de la propiedad a analizar"},
        }},
    }},
    # ── INFORME EJECUTIVO COMPLETO ─────────────────────────────────────────
    {"type": "function", "function": {
        "name": "generate_executive_report",
        "description": (
            "Genera un informe ejecutivo completo con KPIs de inventario, ventas/arrendamientos del mes, "
            "análisis de leads por temperatura, ranking de asesores, propiedades con más días en mercado "
            "y alertas críticas. "
            "Llama a este tool cuando el usuario pida: 'informe ejecutivo', 'reporte completo', "
            "'resumen del mes', 'informe del mes', 'reporte general', 'dashboard ejecutivo', "
            "'informe ejecutivo completo', 'generar reporte ejecutivo', 'KPIs del mes'."
        ),
        "parameters": {"type": "object", "properties": {
            "month": {"type": "integer", "description": "Mes (1-12). Por defecto: mes actual."},
            "year": {"type": "integer", "description": "Año. Por defecto: año actual."},
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
            "stage_id(FK→crm_stage.id), probability, expected_revenue, "
            "target_property_id(FK→estate_property.id = PROPIEDAD DE INTERÉS DEL LEAD; "
            "así se vincula un prospecto a una propiedad), client_budget(presupuesto del cliente), "
            "match_percentage(% de match presupuesto↔precio), lead_score(A/B/C), "
            "lead_temperature(cold/warm/hot/boiling), "
            "lead_source_id(FK→estate_crm_lead_source.id; el nombre de la fuente está en "
            "estate_crm_lead_source.name, únelo con JOIN para mostrarlo). "
            "IMPORTANTE: para 'propiedad con más prospectos' cuenta crm_lead por target_property_id: "
            "SELECT ep.title, COUNT(cl.id) AS prospectos FROM estate_property ep "
            "JOIN crm_lead cl ON cl.target_property_id = ep.id "
            "WHERE cl.type='opportunity' AND cl.active=TRUE GROUP BY ep.id, ep.title ORDER BY prospectos DESC. "
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
    {"type": "function", "function": {
        "name": "search_knowledge",
        "description": (
            "Busca en la DOCUMENTACIÓN del sistema (manuales de usuario y técnico, guías, "
            "matriz de permisos, READMEs de los módulos). Úsala para preguntas sobre CÓMO "
            "hacer algo, QUÉ es o para qué sirve un módulo/función, qué significa un error, "
            "procedimientos, configuración o ayuda de uso. NO la uses para datos en vivo "
            "(propiedades, clientes, ventas): para eso usa las otras herramientas. "
            "Responde citando lo que devuelva esta herramienta."
        ),
        "parameters": {"type": "object", "required": ["query"], "properties": {
            "query": {"type": "string", "description": "La pregunta o tema a buscar en la documentación"},
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


def _redact(text, *secrets):
    """Devuelve text con cualquier ocurrencia de secrets reemplazada por [REDACTED].
    Úsese antes de loguear strings que puedan contener API keys o tokens."""
    if not text:
        return text
    s = str(text)
    for sec in secrets:
        if sec and len(str(sec)) >= 8:
            s = s.replace(str(sec), '[REDACTED]')
    return s


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
                f'**Cuota gratuita agotada** — el plan gratuito de Gemini solo permite '
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
                f'**Límite de requests alcanzado** (429). '
                f'Espera {secs} segundos e intenta de nuevo.'
            )
        return '429', msg, secs
    if '503' in err_str or 'UNAVAILABLE' in err_str or 'high demand' in err_str:
        return '503', None, None
    return 'other', None, None
