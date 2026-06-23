/** @odoo-module **/

import { Component, useState, onMounted, onWillUpdateProps, xml, markup } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { formatResponse } from "../ai_format/ai_format";

export class PropertySummary extends Component {
    static template = xml`
        <div class="o-estate-PropertySummary">

            <!-- Loading inicial -->
            <div t-if="state.loading and !state.data"
                 class="d-flex align-items-center gap-2 px-3 py-3 text-muted small border-bottom"
                 style="background:#f8f9fa;">
                <i class="fa fa-circle-o-notch fa-spin text-primary"/>
                <span>Cargando datos de la propiedad...</span>
            </div>

            <div t-if="state.data" class="border-bottom" style="background:#f8faff;">

                <!-- ── Header ── -->
                <div class="d-flex align-items-center justify-content-between px-3 pt-2 pb-1">
                    <div class="d-flex align-items-center gap-2">
                        <i class="fa fa-robot text-primary" style="font-size:1rem;"/>
                        <strong class="small" style="color:#004274;">Análisis IA</strong>
                        <span t-if="state.data.ai_summary_date"
                              class="badge text-bg-light" style="font-size:0.65rem;font-weight:400;">
                            <t t-esc="state.data.ai_summary_date"/>
                        </span>
                        <span t-if="state.generating"
                              class="badge text-bg-warning" style="font-size:0.65rem;">
                            <i class="fa fa-circle-o-notch fa-spin me-1"/>generando...
                        </span>
                    </div>
                    <div class="d-flex gap-1 align-items-center">
                        <button class="btn btn-link btn-sm p-0 px-1 text-muted"
                                t-on-click="this.regenerate"
                                t-att-disabled="state.generating"
                                title="Regenerar análisis completo">
                            <i class="fa fa-refresh fa-fw"/>
                        </button>
                        <button class="btn btn-link btn-sm p-0 px-1 text-muted"
                                t-on-click="this.toggleCollapsed"
                                t-att-title="state.collapsed ? 'Expandir' : 'Colapsar'">
                            <i t-attf-class="fa fa-fw {{ state.collapsed ? 'fa-chevron-down' : 'fa-chevron-up' }}"/>
                        </button>
                    </div>
                </div>

                <!-- ── Stats pills ── -->
                <div class="d-flex flex-wrap gap-1 px-3 pb-2">
                    <span class="badge rounded-pill" style="background:#dbeafe;color:#004274;font-size:0.72rem;">
                        <i class="fa fa-calendar-o me-1"/><t t-esc="state.data.meeting_count"/> Citas
                    </span>
                    <span class="badge rounded-pill" style="background:#dcfce7;color:#166534;font-size:0.72rem;">
                        <i class="fa fa-users me-1"/><t t-esc="state.data.lead_count"/> Leads
                    </span>
                    <span class="badge rounded-pill" style="background:#fef9c3;color:#854d0e;font-size:0.72rem;">
                        <i class="fa fa-file-text-o me-1"/><t t-esc="state.data.property_invoice_count"/> Facturas
                    </span>
                    <span t-if="state.data.price_history_count > 0"
                          class="badge rounded-pill" style="background:#fce7f3;color:#9d174d;font-size:0.72rem;">
                        <i class="fa fa-line-chart me-1"/><t t-esc="state.data.price_history_count"/> Cambios precio
                    </span>
                    <span t-if="state.data.days_on_market > 0"
                          class="badge rounded-pill" style="background:#e0f2fe;color:#075985;font-size:0.72rem;">
                        <i class="fa fa-clock-o me-1"/><t t-esc="state.data.days_on_market"/> días en mercado
                    </span>
                </div>

                <div t-if="!state.collapsed">

                    <!-- ── Resumen IA generando ── -->
                    <div t-if="state.generating and !state.data.ai_property_summary"
                         class="mx-3 mb-2 p-3 rounded text-center small text-muted"
                         style="background:#eff6ff;border:1px dashed #93c5fd;">
                        <i class="fa fa-magic me-1 text-primary"/>
                        <span>Generando análisis completo con IA...</span><br/>
                        <small class="text-muted">Esto puede tomar unos segundos</small>
                    </div>

                    <!-- ── Resumen IA ── -->
                    <div t-if="state.summaryHtml"
                         class="px-3 pb-2 small"
                         style="font-size:0.79rem;line-height:1.65;color:#1e293b;"
                         t-out="state.summaryHtml"/>

                    <!-- ── Sin resumen ── -->
                    <div t-if="!state.generating and !state.data.ai_property_summary"
                         class="mx-3 mb-2 p-3 rounded text-center small text-muted"
                         style="border:1px dashed #cbd5e1;border-radius:8px;">
                        <i class="fa fa-magic me-1"/>
                        Sin análisis —
                        <button class="btn btn-link btn-sm p-0 ms-1" style="font-size:0.8rem;"
                                t-on-click="this.regenerate">
                            Generar ahora
                        </button>
                    </div>

                    <!-- ── Chat historial ── -->
                    <div t-if="state.chatMessages.length"
                         class="mx-3 mb-2 rounded overflow-hidden"
                         style="border:1px solid #e2e8f0;max-height:340px;overflow-y:auto;">
                        <t t-foreach="state.chatMessages" t-as="msg" t-key="msg_index">
                            <!-- Pregunta del usuario -->
                            <div t-if="msg.role === 'user'"
                                 class="px-3 py-2 d-flex align-items-start gap-2"
                                 style="background:#eff6ff;border-bottom:1px solid #e2e8f0;">
                                <i class="fa fa-user-circle text-primary mt-1" style="font-size:0.85rem;flex-shrink:0;"/>
                                <span class="small" style="font-size:0.78rem;color:#004274;font-weight:500;">
                                    <t t-esc="msg.text"/>
                                </span>
                            </div>
                            <!-- Respuesta IA -->
                            <div t-if="msg.role === 'assistant'"
                                 class="px-3 py-2 position-relative"
                                 style="background:white;border-bottom:1px solid #f1f5f9;">
                                <div class="small" style="font-size:0.78rem;line-height:1.6;color:#1e293b;"
                                     t-out="msg.html"/>
                                <div t-if="!msg.error" class="d-flex gap-2 mt-1">
                                    <button class="btn btn-link btn-sm p-0 text-muted" style="font-size:0.68rem;"
                                            t-on-click="() => this.copyMsg(msg)">
                                        <i t-attf-class="fa {{ msg.copied ? 'fa-check text-success' : 'fa-clone' }} me-1"/>
                                        <t t-esc="msg.copied ? 'Copiado' : 'Copiar'"/>
                                    </button>
                                </div>
                                <div t-if="msg.error" class="mt-1">
                                    <button class="btn btn-link btn-sm p-0 text-danger" style="font-size:0.7rem;"
                                            t-on-click="this.retry">
                                        <i class="fa fa-refresh me-1"/>Reintentar
                                    </button>
                                </div>
                            </div>
                        </t>
                        <!-- Respuesta en curso -->
                        <div t-if="state.chatStreaming"
                             class="px-3 py-2" style="background:white;">
                            <div t-if="state.streamingStatus" class="small text-muted mb-1" style="font-size:0.72rem;">
                                <i class="fa fa-circle-o-notch fa-spin me-1"/><t t-esc="state.streamingStatus"/>
                            </div>
                            <div class="small" style="font-size:0.78rem;line-height:1.6;color:#1e293b;"
                                 t-out="state.streamingHtml"/>
                            <span t-if="!state.streamingStatus" class="text-muted" style="font-size:0.7rem;">
                                <i class="fa fa-circle-o-notch fa-spin me-1"/>escribiendo...
                            </span>
                        </div>
                    </div>

                    <!-- ── Preguntas sugeridas ── -->
                    <div t-if="!state.chatMessages.length and !state.chatStreaming"
                         class="px-3 pb-1 d-flex flex-wrap gap-1">
                        <t t-foreach="suggestions" t-as="sug" t-key="sug_index">
                            <button class="btn btn-sm py-0 px-2"
                                    style="font-size:0.7rem;border:1px solid #cbd5e1;border-radius:14px;color:#004274;background:#fff;"
                                    t-on-click="() => this.sendChat(sug)">
                                <t t-esc="sug"/>
                            </button>
                        </t>
                    </div>

                    <!-- ── Chat input ── -->
                    <div class="px-3 pb-3 pt-1">
                        <div class="d-flex gap-2 align-items-center">
                            <i class="fa fa-comments text-primary" style="font-size:0.9rem;flex-shrink:0;" title="Preguntar al asistente"/>
                            <input type="text"
                                   class="form-control form-control-sm"
                                   style="font-size:0.8rem;border-radius:20px;border-color:#cbd5e1;"
                                   placeholder="Pregunta o pide una acción sobre esta propiedad..."
                                   t-model="state.chatInput"
                                   t-on-keydown="this.onChatKeydown"
                                   t-att-disabled="state.chatStreaming"/>
                            <button class="btn btn-primary btn-sm"
                                    style="border-radius:20px;padding:4px 12px;font-size:0.78rem;white-space:nowrap;"
                                    t-on-click="() => this.sendChat()"
                                    t-att-disabled="state.chatStreaming or !state.chatInput.trim()">
                                <i t-attf-class="fa {{ state.chatStreaming ? 'fa-circle-o-notch fa-spin' : 'fa-paper-plane' }}"/>
                            </button>
                        </div>
                        <div t-if="state.chatMessages.length" class="text-end mt-1">
                            <button class="btn btn-link btn-sm p-0 text-muted" style="font-size:0.7rem;"
                                    t-on-click="this.clearChat">
                                <i class="fa fa-trash-o me-1"/>Limpiar conversación
                            </button>
                        </div>
                    </div>

                </div>
            </div>
        </div>
    `;

    static props = { recordId: { type: Number } };

    // Preguntas sugeridas (acciones reales: el chat ahora tiene herramientas)
    suggestions = [
        "¿Por qué no se ha vendido?",
        "¿Cuál sería el precio ideal de venta?",
        "Genera una descripción para Facebook",
        "¿A qué leads interesados debería contactar?",
    ];

    setup() {
        this.state = useState({
            data: null,
            generating: false,
            collapsed: false,
            summaryHtml: markup(""),
            chatInput: "",
            chatStreaming: false,
            chatMessages: [],   // [{role:'user'|'assistant', text, html, copied, error}]
            streamingHtml: markup(""),
            streamingStatus: "",
        });
        this._lastQuestion = "";
        onMounted(() => this.loadData());
        onWillUpdateProps((next) => {
            if (next.recordId !== this.props.recordId) {
                this.state.chatMessages = [];
                this.state.chatInput = "";
                this.loadData(next.recordId);
            }
        });
    }

    get sessionId() {
        return "prop_" + this.props.recordId;
    }

    async loadData(recordId) {
        const id = recordId ?? this.props.recordId;
        if (!id) return;
        try {
            const result = await rpc("/estate/property/chatter_summary", { property_id: id });
            this.state.data = result;
            this.state.summaryHtml = markup(this._processSummary(result.ai_property_summary || ""));
            // Restaurar conversacion previa de esta propiedad (persistida en chat.history)
            this._restoreConversation(id);
            // NO autogenerar: evita gastar una llamada a Gemini en cada apertura.
            // El usuario usa el boton "Generar ahora" o el icono de refrescar.
        } catch (e) {
            console.warn("[PropertySummary] load error:", e);
        }
    }

    async _restoreConversation(id) {
        try {
            const msgs = await rpc("/estate_ai/session_messages", { session_id: "prop_" + id });
            if (Array.isArray(msgs) && msgs.length) {
                const restored = [];
                for (const m of msgs) {
                    if (m.type === "user") {
                        restored.push({ role: "user", text: m.text, html: markup(m.text) });
                    } else if (m.type === "bot" && m.text) {
                        restored.push({ role: "assistant", text: m.text, html: formatResponse(m.text) });
                    }
                }
                this.state.chatMessages = restored;
            }
        } catch (e) {
            // sin historial previo: no es error
        }
    }

    toggleCollapsed() {
        this.state.collapsed = !this.state.collapsed;
    }

    async regenerate() {
        if (this.state.generating) return;
        this.state.generating = true;
        this.state.summaryHtml = markup("");
        if (this.state.data) this.state.data.ai_property_summary = "";
        try {
            await rpc("/estate/property/regenerate_summary", { property_id: this.props.recordId });
            const result = await rpc("/estate/property/chatter_summary", { property_id: this.props.recordId });
            this.state.data = result;
            this.state.summaryHtml = markup(this._processSummary(result.ai_property_summary || ""));
        } catch (e) {
            console.warn("[PropertySummary] regenerate error:", e);
        } finally {
            this.state.generating = false;
        }
    }

    clearChat() {
        this.state.chatMessages = [];
        this.state.chatInput = "";
    }

    onChatKeydown(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.sendChat();
        }
    }

    async copyMsg(msg) {
        try {
            await navigator.clipboard.writeText(msg.text || "");
            msg.copied = true;
            setTimeout(() => { msg.copied = false; }, 2000);
        } catch (_) { /* ignore */ }
    }

    retry() {
        // Quita el ultimo mensaje de error y reenvia la ultima pregunta
        const msgs = this.state.chatMessages;
        if (msgs.length && msgs[msgs.length - 1].error) {
            msgs.pop();
        }
        if (this._lastQuestion) {
            this.sendChat(this._lastQuestion);
        }
    }

    async sendChat(overrideText) {
        const text = (overrideText || this.state.chatInput).trim();
        if (!text || this.state.chatStreaming) return;

        this._lastQuestion = text;
        this.state.chatMessages = [
            ...this.state.chatMessages,
            { role: "user", text, html: markup(text) },
        ];
        this.state.chatInput = "";
        this.state.chatStreaming = true;
        this.state.streamingHtml = markup("");
        this.state.streamingStatus = "";

        try {
            // Endpoint POTENTE: con herramientas (puede actuar) y persistencia por sesion.
            const response = await fetch("/estate_ai/chat/stream", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": odoo.csrf_token,
                },
                body: JSON.stringify({
                    message: text,
                    property_id: this.props.recordId,
                    current_model: "estate.property",
                    current_record_id: this.props.recordId,
                    session_id: this.sessionId,
                }),
            });

            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let accumulated = "";
            let buffer = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n");
                buffer = lines.pop();

                for (const line of lines) {
                    if (!line.startsWith("data: ")) continue;
                    const payload = line.slice(6).trim();
                    if (payload === "[DONE]") break;
                    try {
                        const chunk = JSON.parse(payload);
                        if (chunk.status && !accumulated) {
                            this.state.streamingStatus = chunk.status;
                        } else if (chunk.text) {
                            accumulated += chunk.text;
                            this.state.streamingStatus = "";
                            this.state.streamingHtml = formatResponse(accumulated);
                        } else if (chunk.error) {
                            throw new Error(chunk.error);
                        }
                    } catch (e) {
                        if (e.message && !e.message.startsWith("Unexpected")) throw e;
                    }
                }
            }

            if (accumulated) {
                this.state.chatMessages = [
                    ...this.state.chatMessages,
                    { role: "assistant", text: accumulated, html: formatResponse(accumulated) },
                ];
            }
        } catch (e) {
            this.state.chatMessages = [
                ...this.state.chatMessages,
                {
                    role: "assistant",
                    text: "Error al conectar con el asistente.",
                    html: markup('<span style="color:#dc2626">No pude responder en este momento.</span>'),
                    error: true,
                },
            ];
        } finally {
            this.state.chatStreaming = false;
            this.state.streamingHtml = markup("");
            this.state.streamingStatus = "";
        }
    }

    // SVG icon map for AI summary section headers
    static SECTION_ICONS = {
        "Ficha": `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9.5L12 3l9 6.5V20a1 1 0 01-1 1H4a1 1 0 01-1-1V9.5z"/><path d="M9 21V12h6v9"/></svg>`,
        "Precio": `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/></svg>`,
        "Interesados": `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>`,
        "Visitas": `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>`,
        "Alertas": `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
        "Acción": `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 8 16 12 12 16"/><line x1="8" y1="12" x2="16" y2="12"/></svg>`,
        "Historial": `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>`,
    };

    _processSummary(raw) {
        if (!raw) return "";
        let html = raw
            .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
            .replace(/\*(.*?)\*/g, "<em>$1</em>")
            .replace(/`(.*?)`/g, "<code>$1</code>");
        const icons = PropertySummary.SECTION_ICONS;
        html = html.replace(
            /(<(?:p|h[1-6])[^>]*>)\s*(?:<strong>)?\s*([\w\sáéíóúüñÁÉÍÓÚÜÑ]+?)(?:<\/strong>)?\s*(<\/(?:p|h[1-6])>)/gi,
            (match, open, text, close) => {
                const key = Object.keys(icons).find(k => text.trim().startsWith(k));
                const svg = key ? icons[key] : "";
                const label = text.trim();
                return `${open}<strong style="display:flex;align-items:center;gap:5px;color:#004274;">${svg}${label}</strong>${close}`;
            }
        );
        for (const [key, svg] of Object.entries(icons)) {
            html = html.replace(
                new RegExp(`(<strong[^>]*>)(${key}[^<]*)(<\/strong>)`, "g"),
                (match, open, text, close) => {
                    if (open.includes("color:#004274")) return match;
                    return `<strong style="display:flex;align-items:center;gap:5px;color:#004274;">${svg}${text}</strong>`;
                }
            );
        }
        return html;
    }
}
