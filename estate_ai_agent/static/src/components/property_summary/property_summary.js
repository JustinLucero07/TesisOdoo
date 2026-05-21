/** @odoo-module **/

import { Component, useState, onMounted, onWillUpdateProps, xml, markup } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

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
                        <strong class="small" style="color:#1877F2;">Análisis IA</strong>
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
                    <span class="badge rounded-pill" style="background:#dbeafe;color:#1e40af;font-size:0.72rem;">
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
                         style="border:1px solid #e2e8f0;max-height:320px;overflow-y:auto;">
                        <t t-foreach="state.chatMessages" t-as="msg" t-key="msg_index">
                            <!-- Pregunta del usuario -->
                            <div t-if="msg.role === 'user'"
                                 class="px-3 py-2 d-flex align-items-start gap-2"
                                 style="background:#eff6ff;border-bottom:1px solid #e2e8f0;">
                                <i class="fa fa-user-circle text-primary mt-1" style="font-size:0.85rem;flex-shrink:0;"/>
                                <span class="small" style="font-size:0.78rem;color:#1e40af;font-weight:500;">
                                    <t t-esc="msg.text"/>
                                </span>
                            </div>
                            <!-- Respuesta IA -->
                            <div t-if="msg.role === 'assistant'"
                                 class="px-3 py-2"
                                 style="background:white;border-bottom:1px solid #f1f5f9;">
                                <div class="small" style="font-size:0.78rem;line-height:1.6;color:#1e293b;"
                                     t-out="msg.html"/>
                            </div>
                        </t>
                        <!-- Respuesta en curso -->
                        <div t-if="state.chatStreaming"
                             class="px-3 py-2" style="background:white;">
                            <div class="small" style="font-size:0.78rem;line-height:1.6;color:#1e293b;"
                                 t-out="state.streamingHtml"/>
                            <span class="text-muted" style="font-size:0.7rem;">
                                <i class="fa fa-circle-o-notch fa-spin me-1"/>escribiendo...
                            </span>
                        </div>
                    </div>

                    <!-- ── Chat input ── -->
                    <div class="px-3 pb-3 pt-1">
                        <div class="d-flex gap-2 align-items-center">
                            <i class="fa fa-comments text-primary" style="font-size:0.9rem;flex-shrink:0;" title="Preguntar al asistente"/>
                            <input type="text"
                                   class="form-control form-control-sm"
                                   style="font-size:0.8rem;border-radius:20px;border-color:#cbd5e1;"
                                   placeholder="Pregunta sobre esta propiedad..."
                                   t-model="state.chatInput"
                                   t-on-keydown="this.onChatKeydown"
                                   t-att-disabled="state.chatStreaming"/>
                            <button class="btn btn-primary btn-sm"
                                    style="border-radius:20px;padding:4px 12px;font-size:0.78rem;white-space:nowrap;"
                                    t-on-click="this.sendChat"
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

    setup() {
        this.state = useState({
            data: null,
            generating: false,
            collapsed: false,
            summaryHtml: markup(""),
            chatInput: "",
            chatStreaming: false,
            chatMessages: [],   // [{role:'user'|'assistant', text:string, html:markup}]
            streamingHtml: markup(""),
        });
        onMounted(() => this.loadData());
        onWillUpdateProps((next) => {
            if (next.recordId !== this.props.recordId) {
                this.state.chatMessages = [];
                this.state.chatInput = "";
                this.loadData(next.recordId);
            }
        });
    }

    async loadData(recordId) {
        const id = recordId ?? this.props.recordId;
        if (!id) return;
        try {
            const result = await rpc("/estate/property/chatter_summary", { property_id: id });
            this.state.data = result;
            this.state.summaryHtml = markup(result.ai_property_summary || "");
            // Auto-generar si no hay resumen
            if (!result.ai_property_summary) {
                this.regenerate();
            }
        } catch (e) {
            console.warn("[PropertySummary] load error:", e);
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
            this.state.summaryHtml = markup(result.ai_property_summary || "");
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

    async sendChat() {
        const text = this.state.chatInput.trim();
        if (!text || this.state.chatStreaming) return;

        // Agregar mensaje del usuario al historial
        this.state.chatMessages = [
            ...this.state.chatMessages,
            { role: "user", text, html: markup(text) },
        ];
        this.state.chatInput = "";
        this.state.chatStreaming = true;
        this.state.streamingHtml = markup("");

        // Historial para el contexto (últimos 6 intercambios)
        const history = this.state.chatMessages.slice(-12).map((m) => ({
            role: m.role,
            text: m.text,
        }));

        try {
            const response = await fetch("/estate/property/chat_stream", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": odoo.csrf_token,
                },
                body: JSON.stringify({
                    property_id: this.props.recordId,
                    question: text,
                    history: history.slice(0, -1), // sin el mensaje actual
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
                        if (chunk.text) {
                            accumulated += chunk.text;
                            this.state.streamingHtml = markup(this._format(accumulated));
                        }
                    } catch (_) {}
                }
            }

            // Mover respuesta al historial
            if (accumulated) {
                this.state.chatMessages = [
                    ...this.state.chatMessages,
                    { role: "assistant", text: accumulated, html: markup(this._format(accumulated)) },
                ];
            }
        } catch (e) {
            this.state.chatMessages = [
                ...this.state.chatMessages,
                {
                    role: "assistant",
                    text: "Error al conectar con el asistente.",
                    html: markup('<span style="color:#dc2626">Error al conectar con el asistente.</span>'),
                },
            ];
        } finally {
            this.state.chatStreaming = false;
            this.state.streamingHtml = markup("");
        }
    }

    _format(text) {
        return text
            .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
            .replace(/\*(.*?)\*/g, "<em>$1</em>")
            .replace(/`(.*?)`/g, "<code>$1</code>")
            .replace(/\n\n/g, "<br/><br/>")
            .replace(/\n/g, "<br/>");
    }
}
