/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, xml, useState, useRef, onMounted, markup } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { formatResponse as richFormat } from "../ai_format/ai_format";

// ─── SVG Icons ───────────────────────────────────────────────────────────────
const SVG = {
    robot: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M12 2a1 1 0 011 1v1.07A7.002 7.002 0 0119 11v1h1a2 2 0 012 2v2a2 2 0 01-2 2h-1v1a3 3 0 01-3 3H8a3 3 0 01-3-3v-1H4a2 2 0 01-2-2v-2a2 2 0 012-2h1v-1a7.002 7.002 0 016-6.93V3a1 1 0 011-1zm0 4a5 5 0 00-5 5v8a1 1 0 001 1h8a1 1 0 001-1v-8a5 5 0 00-5-5zm-2.5 6a1.5 1.5 0 110 3 1.5 1.5 0 010-3zm5 0a1.5 1.5 0 110 3 1.5 1.5 0 010-3z"/></svg>`,
    close: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M18.3 5.71a1 1 0 00-1.42 0L12 10.59 7.12 5.71a1 1 0 00-1.42 1.42L10.59 12l-4.89 4.88a1 1 0 001.42 1.42L12 13.41l4.88 4.89a1 1 0 001.42-1.42L13.41 12l4.89-4.88a1 1 0 000-1.41z"/></svg>`,
    send: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>`,
    stop: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>`,
    user: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>`,
    plus: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>`,
    history: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M13 3a9 9 0 00-9 9H1l3.89 3.89.07.14L9 12H6c0-3.87 3.13-7 7-7s7 3.13 7 7-3.13 7-7 7c-1.93 0-3.68-.79-4.94-2.06l-1.42 1.42A8.95 8.95 0 0013 21a9 9 0 000-18zm-1 5v5l4.28 2.54.72-1.21-3.5-2.08V8H12z"/></svg>`,
    expand: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/></svg>`,
    compress: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M5 16h3v3h2v-5H5v2zm3-8H5v2h5V5H8v3zm6 11h2v-3h3v-2h-5v5zm2-11V5h-2v5h5V8h-3z"/></svg>`,
    sidebar: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z"/></svg>`,
    copy: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/></svg>`,
    trash: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>`,
    warning: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z"/></svg>`,
    spinner: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46A7.93 7.93 0 0020 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74A7.93 7.93 0 004 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/></svg>`,
    check: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>`,
    context: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/></svg>`,
};

// ─── Session ID ──────────────────────────────────────────────────────────────
function newSessionId() {
    return "sess_" + Date.now().toString(36) + "_" + Math.random().toString(36).slice(2, 9);
}

// ─── Timestamp helpers ────────────────────────────────────────────────────────
function nowTime() {
    return new Date().toLocaleTimeString('es-EC', { hour: '2-digit', minute: '2-digit' });
}

// ─── Page Context ─────────────────────────────────────────────────────────────
function getPageContext() {
    const ctx = {};
    try {
        // Odoo web client stores current model/id in URL hash or router state
        const hash = window.location.hash;
        // Pattern: #model=estate.property&id=123 or /web#action=...&model=...&id=...
        const modelMatch = hash.match(/model=([^&]+)/);
        const idMatch = hash.match(/[^a-z]id=(\d+)/i);
        if (modelMatch) ctx.current_model = decodeURIComponent(modelMatch[1]);
        if (idMatch) ctx.current_record_id = parseInt(idMatch[1]);

        // Also try odoo router if available
        if (window.__owl__ && window.__owl__.router) {
            const state = window.__owl__.router.currentRoute;
            if (state && state.params) {
                ctx.current_model = ctx.current_model || state.params.model;
                ctx.current_record_id = ctx.current_record_id || parseInt(state.params.id || 0);
            }
        }

        // Derive friendly context label
        if (ctx.current_model === 'estate.property') {
            ctx.context_label = `Viendo propiedad ID ${ctx.current_record_id}`;
            ctx.property_id = ctx.current_record_id;
        } else if (ctx.current_model === 'crm.lead') {
            ctx.context_label = `Viendo lead/oportunidad ID ${ctx.current_record_id}`;
            ctx.lead_id = ctx.current_record_id;
        } else if (ctx.current_model === 'estate.contract') {
            ctx.context_label = `Viendo contrato ID ${ctx.current_record_id}`;
        } else if (ctx.current_model) {
            ctx.context_label = `Módulo: ${ctx.current_model}`;
        }
    } catch (_) {}
    return ctx;
}

// ─── Dynamic chips based on context/last message ─────────────────────────────
function getDynamicChips(messages, pageCtx, alertChips) {
    const lastBot = [...messages].reverse().find(m => m.type === 'bot' && !m.streaming && !m.isError);
    const text = lastBot ? lastBot.text.toLowerCase() : '';

    // Property page chips (state-aware labels)
    if (pageCtx.current_model === 'estate.property' && pageCtx.current_record_id) {
        return [
            'Análisis completo de esta propiedad',
            'Plan de campaña de marketing',
            '¿Cuánto vale según el AVM?',
            'Leads interesados en esta propiedad',
            'Propiedades similares disponibles',
            'Generar descripción comercial',
        ];
    }
    if (pageCtx.current_model === 'crm.lead' && pageCtx.current_record_id) {
        return [
            'Resumir este lead',
            'Propiedades que coinciden con su presupuesto',
            'Agendar visita',
            'Tips de negociación',
            'Analizar probabilidad de cierre',
        ];
    }

    // Reports module — use server alert chips if available, then standard
    const url = window.location.href || '';
    if (url.includes('estate_reports') || url.includes('estate_intel') || url.includes('action-estate_reports')) {
        const base = [
            'Informe ejecutivo completo del mes',
            'KPIs generales del mes',
            'Reporte de ventas por mes',
            'Leads por temperatura',
            'Ranking de asesores',
        ];
        // Prepend alert chips (with real counts) if available
        if (alertChips && alertChips.length) {
            const alerts = alertChips.filter(c =>
                c.includes('sin vender') || c.includes('fríos') || c.includes('vencidos'));
            return [...alerts, ...base].slice(0, 6);
        }
        return base;
    }

    // Content-aware chips
    if (text.includes('propiedad') || text.includes('inmueble')) {
        return ['Ver más propiedades', 'Plan de marketing para la propiedad', 'Calcular AVM', 'Ver estadísticas'];
    }
    if (text.includes('lead') || text.includes('oportunidad')) {
        return ['Leads más calientes', 'Crear nuevo lead', 'Agendar visita', 'Ver pipeline'];
    }
    if (text.includes('pago') || text.includes('contrato') || text.includes('comisión')) {
        return ['Pagos vencidos', 'Resumen financiero', 'Ver contratos activos', 'Generar reporte'];
    }
    if (text.includes('informe') || text.includes('reporte') || text.includes('kpi')) {
        return ['Informe ejecutivo completo del mes', 'Descargar PDF del reporte', 'Exportar a Excel', 'Comparar con mes anterior'];
    }

    return ['Propiedades disponibles', 'Leads calientes', 'Informe ejecutivo del mes', 'Crear propiedad', 'Ver estadísticas'];
}

// ─── localStorage helpers ─────────────────────────────────────────────────────
const LS_SESSION_KEY = 'inmobot_last_session';
function lsSaveSession(id) { try { localStorage.setItem(LS_SESSION_KEY, id || ''); } catch(_) {} }
function lsLoadSession() { try { return localStorage.getItem(LS_SESSION_KEY) || null; } catch(_) { return null; } }

export class AIChatFloatContainer extends Component {
    setup() {
        this.state = useState({
            isOpen: false,
            sidebarOpen: true,
            messages: [],
            inputText: "",
            loading: false,
            sessions: [],
            activeSessionId: null,
            isMaximized: false,
            copiedMsgId: null,
            pageContext: {},
            msgFeedback: {},  // {msgId: 'up'|'down'}
            alertChips: [],   // chips con conteos reales del servidor
        });
        this.chatBody = useRef("chatBody");
        this.textareaRef = useRef("textarea");
        this.fileInputRef = useRef("fileInput");
        this._initialized = false;
        this._abortController = null;

        onMounted(() => {
            this.state.pageContext = getPageContext();
            setInterval(() => {
                const newCtx = getPageContext();
                if (JSON.stringify(newCtx) !== JSON.stringify(this.state.pageContext)) {
                    this.state.pageContext = newCtx;
                }
            }, 2000);
            // Pre-fetch alert chips (contextual counts from server)
            this._fetchAlertChips();
        });
    }

    async _fetchAlertChips() {
        try {
            const chips = await rpc('/estate_ai/alert_chips', {});
            if (Array.isArray(chips) && chips.length) {
                this.state.alertChips = chips;
            }
        } catch(_) {}
    }

    async toggleChat() {
        this.state.isOpen = !this.state.isOpen;
        if (this.state.isOpen && !this._initialized) {
            this._initialized = true;
            this.state.pageContext = getPageContext();
            await this._loadSessions();
            const savedId = lsLoadSession();
            if (savedId && this.state.sessions.find(s => s.session_id === savedId)) {
                await this._openSession(savedId);
            } else if (this.state.sessions.length) {
                await this._openSession(this.state.sessions[0].session_id);
            } else {
                this._startNewSession();
                // Auto-send monthly summary when on reports module with a fresh chat
                const url = window.location.href || '';
                if (url.includes('estate_reports') || url.includes('estate_intel')) {
                    setTimeout(() => {
                        this.sendMessage('Dame el informe ejecutivo completo del mes: KPIs de inventario, ventas, leads activos por temperatura, ranking de asesores y alertas críticas.');
                    }, 700);
                } else {
                    // Briefing proactivo del día al abrir un chat nuevo
                    setTimeout(() => this._showBriefing(), 500);
                }
            }
        }
        if (this.state.isOpen) this._scrollBottom();
    }

    // ── Adjuntar documento/imagen → OCR ───────────────────────────────────────
    onAttachClick() {
        if (this.fileInputRef && this.fileInputRef.el) this.fileInputRef.el.click();
    }

    async onAttachFile(ev) {
        const file = ev.target.files && ev.target.files[0];
        if (!file) return;
        ev.target.value = "";
        this.state.messages.push({ id: Math.random(), type: "user", text: `[Documento] ${file.name}`, date: nowTime() });
        const botMsg = { id: Math.random(), type: "bot", text: "Leyendo documento...", date: nowTime(), streaming: true, statusPhase: "processing" };
        this.state.messages.push(botMsg);
        const botIdx = this.state.messages.length - 1;
        this._scrollBottom();
        try {
            const fd = new FormData();
            fd.append("file", file);
            fd.append("csrf_token", odoo.csrf_token || "");
            const resp = await fetch("/estate_ai/ocr", { method: "POST", body: fd });
            const data = await resp.json();
            let txt;
            if (data && data.extracted) {
                if (data.extracted.raw_text) {
                    txt = data.extracted.raw_text;
                } else {
                    txt = "**Datos extraídos del documento:**\n" +
                        Object.entries(data.extracted)
                            .map(([k, v]) => `- **${k}:** ${typeof v === "object" ? JSON.stringify(v) : v}`)
                            .join("\n");
                }
            } else {
                txt = (data && data.error) ? data.error : "No pude extraer datos del documento.";
            }
            if (data && data.extracted) {
                // Guarda los datos para adjuntarlos a la próxima instrucción del usuario
                this._pendingDoc = txt;
                this.state.messages[botIdx].text = txt +
                    "\n\n*Dime qué quieres hacer con este documento* (ej: registrar la factura, " +
                    "crear un contrato con estos datos, buscar la propiedad o el cliente).";
            } else {
                this.state.messages[botIdx].text = txt;
            }
        } catch (e) {
            this.state.messages[botIdx].text = "Error al procesar el documento.";
            this.state.messages[botIdx].isError = true;
        } finally {
            this.state.messages[botIdx].streaming = false;
            this.state.messages[botIdx].statusPhase = null;
            this._scrollBottom();
        }
    }

    // ── Confirmación de acciones (botones Sí/No) ──────────────────────────────
    confirmAction(yes) {
        this.state.messages.forEach((m) => { if (m.requiresConfirmation) m.requiresConfirmation = false; });
        this.sendMessage(yes ? "Sí, confirmo. Procede con la acción." : "No, cancela la acción.");
    }

    // ── Briefing proactivo del día ────────────────────────────────────────────
    async _showBriefing() {
        try {
            // Memoria visible: lo que la IA recuerda del usuario
            let memText = "";
            try {
                const mems = await rpc("/estate_ai/memories", {});
                if (Array.isArray(mems) && mems.length) {
                    memText = "**Lo que recuerdo de ti:**\n" +
                        mems.slice(0, 5).map((m) => `- ${m.title}${m.content ? ": " + m.content : ""}`).join("\n") +
                        "\n\n";
                }
            } catch (_) { /* sin memorias */ }
            const data = await rpc("/estate_ai/briefing", {});
            const txt = (memText + (data && data.response ? data.response : "")).trim();
            if (txt) {
                this.state.messages.push({ id: Math.random(), type: "bot", text: txt, date: nowTime() });
                this._scrollBottom();
            }
        } catch (_) { /* silencioso */ }
    }

    toggleSidebar() { this.state.sidebarOpen = !this.state.sidebarOpen; }
    toggleMaximize() { this.state.isMaximized = !this.state.isMaximized; }

    async _loadSessions() {
        try {
            const sessions = await rpc("/estate_ai/sessions", {});
            this.state.sessions = sessions || [];
        } catch (e) { console.error("Error loading sessions:", e); }
    }

    async _openSession(sessionId) {
        if (this.state.loading) return;
        this.state.activeSessionId = sessionId;
        lsSaveSession(sessionId);
        this.state.messages = [];
        this.state.loading = true;
        try {
            const msgs = await rpc("/estate_ai/session_messages", { session_id: sessionId });
            this.state.messages = (msgs || []).map(m => ({
                ...m,
                id: Math.random(),
                date: m.date || nowTime(),
            }));
        } catch (e) { console.error("Error loading session:", e); }
        this.state.loading = false;
        this._scrollBottom();
    }

    _startNewSession() {
        if (this._abortController) {
            this._abortController.abort();
            this._abortController = null;
        }
        this.state.activeSessionId = newSessionId();
        this.state.messages = [];
        this.state.loading = false;
    }

    async newChat() { this._startNewSession(); }

    async deleteSession(sessionId, ev) {
        ev.stopPropagation();
        if (!confirm("¿Eliminar esta conversación? Esta acción no se puede deshacer.")) return;
        try {
            await rpc("/estate_ai/clear", { session_id: sessionId });
            this.state.sessions = this.state.sessions.filter(s => s.session_id !== sessionId);
            if (this.state.activeSessionId === sessionId) {
                if (this.state.sessions.length) {
                    await this._openSession(this.state.sessions[0].session_id);
                } else { this._startNewSession(); }
            }
        } catch (e) { console.error(e); }
    }

    cancelStreaming() {
        if (this._abortController) {
            this._abortController.abort();
            this._abortController = null;
        }
        this.state.loading = false;
        // Mark last streaming message as cancelled
        const lastBot = [...this.state.messages].reverse().find(m => m.type === 'bot' && m.streaming);
        if (lastBot) {
            if (!lastBot.text || lastBot.text.length < 5) {
                // Remove empty bot placeholder
                this.state.messages = this.state.messages.filter(m => m.id !== lastBot.id);
            } else {
                lastBot.streaming = false;
                lastBot.statusPhase = null;
                lastBot.text += ' *(respuesta interrumpida)*';
            }
        }
    }

    async sendMessage(overrideText) {
        const text = (overrideText || this.state.inputText).trim();
        if (!text || this.state.loading) return;

        const isFirstMsg = this.state.messages.length === 0;
        const timestamp = nowTime();
        this.state.messages.push({ id: Math.random(), type: "user", text, date: timestamp });
        this.state.inputText = "";
        this.state.loading = true;
        this._scrollBottom();
        this._resetTextareaHeight();

        const botMsg = {
            id: Math.random(),
            type: "bot",
            text: "",
            date: nowTime(),
            streaming: true,
            statusPhase: "searching",
            requiresConfirmation: false,
        };
        this.state.messages.push(botMsg);
        const botIdx = this.state.messages.length - 1;
        this._scrollBottom();

        // Abort controller for cancel support + timeout
        this._abortController = new AbortController();
        const timeoutId = setTimeout(() => {
            if (this._abortController) this._abortController.abort();
        }, 90000); // 90 second timeout

        try {
            // Build payload with page context
            const pageCtx = getPageContext();
            // Si hay un documento adjunto recién leído, va como contexto de la instrucción
            let outMessage = text;
            if (this._pendingDoc) {
                outMessage = `[Documento adjunto recién leído]\n${this._pendingDoc}\n\n` +
                    `[Instrucción del usuario sobre ese documento]\n${text}`;
                this._pendingDoc = null;
            }
            const payload = {
                message: outMessage,
                session_id: this.state.activeSessionId,
            };
            if (pageCtx.property_id) payload.property_id = pageCtx.property_id;
            if (pageCtx.lead_id) payload.lead_id = pageCtx.lead_id;
            if (pageCtx.current_model) payload.current_model = pageCtx.current_model;
            if (pageCtx.current_record_id) payload.current_record_id = pageCtx.current_record_id;
            payload.page_url = window.location.href;

            const response = await fetch("/estate_ai/chat/stream", {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-CSRFToken": odoo.csrf_token || "" },
                body: JSON.stringify(payload),
                signal: this._abortController.signal,
            });

            clearTimeout(timeoutId);

            if (!response.ok) throw new Error(`Error del servidor: HTTP ${response.status}`);

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let accumulated = "";
            let buffer = "";

            while (true) {
                let readResult;
                try {
                    readResult = await reader.read();
                } catch (readErr) {
                    if (readErr.name === 'AbortError') break;
                    throw readErr;
                }
                const { done, value } = readResult;
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n");
                buffer = lines.pop();
                for (const line of lines) {
                    if (!line.startsWith("data: ")) continue;
                    const payload_str = line.slice(6).trim();
                    if (payload_str === "[DONE]") break;
                    try {
                        const chunk = JSON.parse(payload_str);
                        if (chunk.status && !accumulated) {
                            this.state.messages[botIdx].text = chunk.status;
                            this.state.messages[botIdx].statusPhase = "processing";
                        } else if (chunk.text) {
                            accumulated += chunk.text;
                            this.state.messages[botIdx].text = accumulated;
                            this.state.messages[botIdx].statusPhase = null;
                            // Detect confirmation requirement via JSON flag or text pattern
                            if (chunk.requires_confirmation ||
                                accumulated.includes('CONFIRMACIÓN REQUERIDA')) {
                                this.state.messages[botIdx].requiresConfirmation = true;
                            }
                            this._scrollBottom();
                        } else if (chunk.error) {
                            this.state.messages[botIdx].text = chunk.error;
                            this.state.messages[botIdx].isError = true;
                        }
                    } catch (_) {}
                }
            }

            if (!accumulated && this.state.messages[botIdx].text) {
                accumulated = this.state.messages[botIdx].text;
            }
            this.state.messages[botIdx].streaming = false;
            this.state.messages[botIdx].statusPhase = null;
            this.state.messages[botIdx].date = nowTime();

            if (isFirstMsg) {
                const newSession = {
                    session_id: this.state.activeSessionId,
                    title: text.slice(0, 55),
                    date: nowTime(),
                    count: 1,
                };
                this.state.sessions = [newSession, ...this.state.sessions.slice(0, 49)];
            } else {
                const idx = this.state.sessions.findIndex(s => s.session_id === this.state.activeSessionId);
                if (idx >= 0) this.state.sessions[idx].count = (this.state.sessions[idx].count || 0) + 1;
            }
        } catch (e) {
            clearTimeout(timeoutId);
            if (e.name === 'AbortError') {
                // Cancelled by user or timeout — already handled in cancelStreaming or timeout
                const lastBot = this.state.messages[botIdx];
                if (lastBot && lastBot.streaming) {
                    if (!lastBot.text || lastBot.text.length < 5) {
                        this.state.messages = this.state.messages.filter((_, i) => i !== botIdx);
                    } else {
                        lastBot.streaming = false;
                        lastBot.statusPhase = null;
                        lastBot.text += ' *(tiempo de espera agotado)*';
                    }
                }
            } else {
                const lastBot = this.state.messages[botIdx];
                if (lastBot) {
                    lastBot.text = `Error de conexión: ${e.message}`;
                    lastBot.streaming = false;
                    lastBot.isError = true;
                    lastBot.statusPhase = null;
                }
            }
        }

        this._abortController = null;
        this.state.loading = false;
        this._scrollBottom();
    }

    onKeydown(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.sendMessage();
        }
    }

    onTextareaInput(ev) {
        // Auto-resize textarea
        const el = ev.target;
        el.style.height = 'auto';
        el.style.height = Math.min(el.scrollHeight, 120) + 'px';
    }

    _resetTextareaHeight() {
        const el = this.textareaRef && this.textareaRef.el;
        if (el) el.style.height = '';
    }

    useSuggestion(text) {
        this.state.inputText = text;
        this.sendMessage(text);
    }

    async copyMessage(msg) {
        try {
            await navigator.clipboard.writeText(msg.text);
            this.state.copiedMsgId = msg.id;
            setTimeout(() => { this.state.copiedMsgId = null; }, 1800);
        } catch (_) {}
    }

    _scrollBottom() {
        setTimeout(() => {
            const el = this.chatBody.el;
            if (el) el.scrollTop = el.scrollHeight;
        }, 60);
    }

    get dynamicChips() {
        return getDynamicChips(this.state.messages, this.state.pageContext, this.state.alertChips);
    }

    feedbackMsg(msg, vote) {
        const current = this.state.msgFeedback[msg.id];
        if (current === vote) {
            delete this.state.msgFeedback[msg.id];
            return; // un-vote: no persistir
        }
        this.state.msgFeedback[msg.id] = vote;

        // Persistir el voto en el backend (B5). Buscamos la pregunta = último
        // mensaje de usuario antes de esta respuesta del bot.
        const idx = this.state.messages.findIndex(m => m.id === msg.id);
        let question = "";
        for (let i = idx - 1; i >= 0; i--) {
            if (this.state.messages[i].type === "user") {
                question = this.state.messages[i].text || "";
                break;
            }
        }
        rpc("/estate_ai/feedback", {
            vote,
            session_id: this.state.activeSessionId,
            question,
            answer: msg.text || "",
            page_context: (this.state.pageContext && this.state.pageContext.context_label) || "",
        }).catch(() => {});
    }

    // ── Format response (markdown → HTML + charts) ───────────────────────────
    formatResponse(text) {
        return richFormat(text);
    }
}

// ─── Template ─────────────────────────────────────────────────────────────────
AIChatFloatContainer.template = xml`
<div>
  <!-- FLOATING BUTTON -->
  <div t-on-click="toggleChat" class="ai-float-btn" t-att-class="state.isOpen ? 'ai-float-btn-active' : ''">
    <t t-if="state.isOpen">${SVG.close}</t>
    <t t-else="">${SVG.robot}</t>
    <t t-if="state.loading and state.isOpen">
      <span class="ai-float-pulse"/>
    </t>
  </div>

  <!-- CHAT WINDOW -->
  <div t-if="state.isOpen" t-att-class="'ai-window' + (state.isMaximized ? ' ai-window-max' : '')">

    <!-- HEADER -->
    <div class="ai-header">
      <div class="ai-header-brand">
        <button class="ai-icon-btn" t-on-click="toggleSidebar" title="Historial">${SVG.sidebar}</button>
        ${SVG.robot}
        <span>InmoBot</span>
        <t t-if="state.loading">
          <span class="ai-header-status">
            <span class="ai-typing-dot"/><span class="ai-typing-dot"/><span class="ai-typing-dot"/>
            procesando
          </span>
        </t>
      </div>
      <div style="display:flex;gap:6px;align-items:center">
        <!-- Page context badge -->
        <t t-if="state.pageContext.context_label">
          <span class="ai-context-badge" t-att-title="state.pageContext.context_label">
            ${SVG.context}
            <span t-esc="state.pageContext.context_label"/>
          </span>
        </t>
        <button class="ai-icon-btn" t-on-click="newChat" title="Nueva conversación">${SVG.plus}</button>
        <button class="ai-icon-btn" t-on-click="toggleMaximize" title="Expandir/Reducir">
          <t t-if="state.isMaximized">${SVG.compress}</t>
          <t t-else="">${SVG.expand}</t>
        </button>
        <button class="ai-icon-btn" t-on-click="toggleChat" title="Cerrar">${SVG.close}</button>
      </div>
    </div>

    <!-- BODY -->
    <div class="ai-body-wrapper">

      <!-- SIDEBAR -->
      <div t-if="state.sidebarOpen" class="ai-sidebar">
        <div class="ai-sidebar-header">${SVG.history} Conversaciones</div>

        <t t-if="!state.sessions.length">
          <div class="ai-sidebar-empty">
            ${SVG.history}
            <br/><small>Sin historial</small>
          </div>
        </t>

        <div class="ai-sidebar-list">
          <t t-foreach="state.sessions" t-as="sess" t-key="sess.session_id">
            <div t-on-click="() => this._openSession(sess.session_id)"
                 t-att-class="'ai-session-item' + (state.activeSessionId === sess.session_id ? ' ai-session-active' : '')">
              <div class="ai-session-title" t-esc="sess.title"/>
              <div class="ai-session-meta">
                <span t-esc="sess.date"/>
                <span class="ai-session-count" t-esc="(sess.count || 0) + ' msgs'"/>
              </div>
              <button class="ai-session-del" t-on-click="(ev) => this.deleteSession(sess.session_id, ev)" title="Eliminar conversación">
                <i class="fa fa-trash"/>
              </button>
            </div>
          </t>
        </div>

        <button class="ai-new-chat-btn" t-on-click="newChat">
          ${SVG.plus} Nueva conversación
        </button>
      </div>

      <!-- CHAT AREA -->
      <div class="ai-chat-area">
        <div class="ai-messages" t-ref="chatBody">
          <t t-if="!state.messages.length and !state.loading">
            <div class="ai-welcome">
              <div class="ai-welcome-avatar">${SVG.robot}</div>
              <h5>¡Hola! Soy InmoBot</h5>
              <p style="font-size:.88em;color:#888;margin-bottom:16px">
                Tu asistente inmobiliario con IA. Consulta, crea y gestiona propiedades, leads, contratos y más.
              </p>
              <t t-if="state.pageContext.context_label">
                <div class="ai-context-hint">
                  ${SVG.context} <span t-esc="state.pageContext.context_label"/>
                </div>
              </t>
              <div class="ai-chips-grid">
                <t t-foreach="dynamicChips" t-as="chip" t-key="chip_index">
                  <button class="ai-chip" t-on-click="() => this.useSuggestion(chip)" t-esc="chip"/>
                </t>
              </div>
            </div>
          </t>

          <t t-foreach="state.messages" t-as="msg" t-key="msg.id or msg_index">
            <!-- User bubble -->
            <div t-if="msg.type === 'user'" class="ai-msg-row ai-msg-user">
              <div class="ai-bubble ai-bubble-user">
                <t t-esc="msg.text"/>
                <div class="ai-msg-time" t-esc="msg.date"/>
              </div>
            </div>

            <!-- Bot bubble -->
            <div t-if="msg.type === 'bot'" class="ai-msg-row ai-msg-bot">
              <div class="ai-avatar-icon ai-avatar-bot">${SVG.robot}</div>
              <div t-att-class="'ai-bubble ai-bubble-bot' + (msg.streaming ? ' ai-bubble-streaming' : '') + (msg.isError ? ' ai-bubble-error' : '')">
                <!-- Confirmation warning -->
                <t t-if="msg.requiresConfirmation and !msg.streaming">
                  <div class="ai-confirm-banner">
                    ${SVG.warning} Acción que requiere confirmación — revisa antes de continuar
                  </div>
                  <div class="ai-confirm-actions" style="display:flex;gap:8px;margin-top:6px">
                    <button t-on-click="() => this.confirmAction(true)"
                            style="background:#00897B;color:#fff;border:none;border-radius:6px;padding:5px 14px;font-size:.85em;font-weight:600;cursor:pointer">
                      Sí, confirmar
                    </button>
                    <button t-on-click="() => this.confirmAction(false)"
                            style="background:#eef1f5;color:#444;border:none;border-radius:6px;padding:5px 14px;font-size:.85em;cursor:pointer">
                      Cancelar
                    </button>
                  </div>
                </t>

                <!-- Status phase (streaming, no text yet) -->
                <t t-if="msg.streaming and msg.statusPhase and !msg.isError">
                  <div class="ai-status-indicator">
                    <span class="ai-typing-dot"/><span class="ai-typing-dot"/><span class="ai-typing-dot"/>
                    <span t-if="msg.text" t-esc="msg.text"/>
                    <span t-else="">Procesando consulta...</span>
                  </div>
                </t>
                <t t-else="">
                  <t t-if="msg.isError">
                    <div style="color:#E53935;display:flex;align-items:center;gap:6px;font-size:.88em">
                      ${SVG.warning}
                      <span t-esc="msg.text"/>
                    </div>
                  </t>
                  <t t-else="">
                    <t t-out="formatResponse(msg.text)"/>
                  </t>
                </t>

                <span t-if="msg.streaming and !msg.statusPhase" class="ai-cursor"/>
                <div class="ai-bubble-actions" t-if="!msg.streaming and !msg.isError">
                  <button class="ai-feedback-btn"
                          t-att-class="state.msgFeedback[msg.id] === 'up' ? 'ai-feedback-up' : ''"
                          t-on-click="() => this.feedbackMsg(msg, 'up')"
                          title="Buena respuesta">&#128077;</button>
                  <button class="ai-feedback-btn"
                          t-att-class="state.msgFeedback[msg.id] === 'down' ? 'ai-feedback-down' : ''"
                          t-on-click="() => this.feedbackMsg(msg, 'down')"
                          title="Mala respuesta">&#128078;</button>
                  <button class="ai-action-btn" t-att-class="state.copiedMsgId === msg.id ? 'ai-action-btn-copied' : ''"
                          t-on-click="() => this.copyMessage(msg)"
                          t-att-title="state.copiedMsgId === msg.id ? 'Copiado' : 'Copiar'">
                    <t t-if="state.copiedMsgId === msg.id">${SVG.check}</t>
                    <t t-else="">${SVG.copy}</t>
                  </button>
                </div>
                <div class="ai-msg-time" t-esc="msg.date"/>
              </div>
            </div>
          </t>
        </div>

        <!-- Dynamic Chips -->
        <t t-if="state.messages.length and !state.loading">
          <div class="ai-chips-bar">
            <t t-foreach="dynamicChips" t-as="chip" t-key="chip_index">
              <button class="ai-chip-sm" t-on-click="() => this.useSuggestion(chip)" t-esc="chip"/>
            </t>
          </div>
        </t>

        <!-- Input -->
        <div class="ai-input-bar">
          <textarea
            class="ai-input"
            placeholder="Escribe tu consulta... (Enter para enviar, Shift+Enter para salto de línea)"
            t-model="state.inputText"
            t-on-keydown="onKeydown"
            t-on-input="onTextareaInput"
            t-ref="textarea"
            rows="1"
          />
          <!-- Adjuntar documento/imagen (OCR) -->
          <input type="file" t-ref="fileInput" accept="image/*,application/pdf"
                 style="display:none" t-on-change="onAttachFile"/>
          <button class="ai-icon-btn" t-on-click="onAttachClick"
                  title="Adjuntar documento o imagen"
                  style="background:none;border:none;cursor:pointer;color:#6b7280;padding:0 5px;display:flex;align-items:center">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"/></svg>
          </button>
          <!-- Cancel button (shown while loading) -->
          <t t-if="state.loading">
            <button class="ai-cancel-btn" t-on-click="cancelStreaming" title="Cancelar respuesta">
              ${SVG.stop}
            </button>
          </t>
          <t t-else="">
            <button class="ai-send-btn"
                    t-on-click="() => this.sendMessage()"
                    t-att-disabled="!state.inputText.trim()">
              ${SVG.send}
            </button>
          </t>
        </div>
      </div>
    </div>
  </div>
</div>
`;

registry.category("main_components").add("estate_ai_chat_float_container", {
    Component: AIChatFloatContainer,
});
