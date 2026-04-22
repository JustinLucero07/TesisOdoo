/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, xml, useState, useRef, onMounted, markup } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

// ─── SVG Icons ───────────────────────────────────────────────────────────────
const SVG = {
    robot: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M12 2a1 1 0 011 1v1.07A7.002 7.002 0 0119 11v1h1a2 2 0 012 2v2a2 2 0 01-2 2h-1v1a3 3 0 01-3 3H8a3 3 0 01-3-3v-1H4a2 2 0 01-2-2v-2a2 2 0 012-2h1v-1a7.002 7.002 0 016-6.93V3a1 1 0 011-1zm0 4a5 5 0 00-5 5v8a1 1 0 001 1h8a1 1 0 001-1v-8a5 5 0 00-5-5zm-2.5 6a1.5 1.5 0 110 3 1.5 1.5 0 010-3zm5 0a1.5 1.5 0 110 3 1.5 1.5 0 010-3z"/></svg>`,
    close: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M18.3 5.71a1 1 0 00-1.42 0L12 10.59 7.12 5.71a1 1 0 00-1.42 1.42L10.59 12l-4.89 4.88a1 1 0 001.42 1.42L12 13.41l4.88 4.89a1 1 0 001.42-1.42L13.41 12l4.89-4.88a1 1 0 000-1.41z"/></svg>`,
    send: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>`,
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
    search: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><circle cx="10.5" cy="10.5" r="6.5" fill="none" stroke="currentColor" stroke-width="2"/><path d="M15 15l5 5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>`,
};

// ─── Session ID ──────────────────────────────────────────────────────────────
function newSessionId() {
    return "sess_" + Date.now().toString(36) + "_" + Math.random().toString(36).slice(2, 7);
}

// ─── Chart palette ───────────────────────────────────────────────────────────
const PALETTE = ['#004274','#E53935','#00897B','#FF9800','#7B1FA2','#0288D1','#43A047','#F4511E','#546E7A','#FDD835'];

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
        });
        this.chatBody = useRef("chatBody");
        this._initialized = false;
    }

    async toggleChat() {
        this.state.isOpen = !this.state.isOpen;
        if (this.state.isOpen && !this._initialized) {
            this._initialized = true;
            await this._loadSessions();
            if (this.state.sessions.length) {
                await this._openSession(this.state.sessions[0].session_id);
            } else {
                this._startNewSession();
            }
        }
        if (this.state.isOpen) this._scrollBottom();
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
        this.state.activeSessionId = sessionId;
        this.state.messages = [];
        this.state.loading = true;
        try {
            const msgs = await rpc("/estate_ai/session_messages", { session_id: sessionId });
            this.state.messages = (msgs || []).map(m => ({ ...m, id: Math.random() }));
        } catch (e) { console.error("Error loading session:", e); }
        this.state.loading = false;
        this._scrollBottom();
    }

    _startNewSession() {
        this.state.activeSessionId = newSessionId();
        this.state.messages = [];
    }

    async newChat() { this._startNewSession(); }

    async deleteSession(sessionId, ev) {
        ev.stopPropagation();
        if (!confirm("¿Eliminar esta conversación?")) return;
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

    async sendMessage(overrideText) {
        const text = (overrideText || this.state.inputText).trim();
        if (!text || this.state.loading) return;

        const isFirstMsg = this.state.messages.length === 0;
        this.state.messages.push({ id: Math.random(), type: "user", text, date: "Ahora" });
        this.state.inputText = "";
        this.state.loading = true;
        this._scrollBottom();

        const botMsg = { id: Math.random(), type: "bot", text: "", date: "Ahora", streaming: true, statusPhase: "searching" };
        this.state.messages.push(botMsg);
        const botIdx = this.state.messages.length - 1;
        this._scrollBottom();

        try {
            const response = await fetch("/estate_ai/chat/stream", {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-CSRFToken": odoo.csrf_token },
                body: JSON.stringify({ message: text, session_id: this.state.activeSessionId }),
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
                            this.state.messages[botIdx].text = chunk.status;
                            this.state.messages[botIdx].statusPhase = "processing";
                        } else if (chunk.text) {
                            accumulated += chunk.text;
                            this.state.messages[botIdx].text = accumulated;
                            this.state.messages[botIdx].statusPhase = null;
                            this._scrollBottom();
                        } else if (chunk.error) {
                            this.state.messages[botIdx].text = chunk.error;
                            this.state.messages[botIdx].isError = true;
                        }
                    } catch (_) {}
                }
            }

            if (!accumulated) accumulated = this.state.messages[botIdx].text;
            this.state.messages[botIdx].streaming = false;
            this.state.messages[botIdx].statusPhase = null;

            if (isFirstMsg) {
                const newSession = {
                    session_id: this.state.activeSessionId,
                    title: text.slice(0, 55),
                    date: new Date().toLocaleTimeString('es-EC', { hour: '2-digit', minute: '2-digit' }),
                    count: 1,
                };
                this.state.sessions = [newSession, ...this.state.sessions.slice(0, 49)];
            } else {
                const idx = this.state.sessions.findIndex(s => s.session_id === this.state.activeSessionId);
                if (idx >= 0) this.state.sessions[idx].count += 1;
            }
        } catch (e) {
            this.state.messages[botIdx].text = `Error de conexión: ${e.message}`;
            this.state.messages[botIdx].streaming = false;
            this.state.messages[botIdx].isError = true;
        }

        this.state.loading = false;
        this._scrollBottom();
    }

    onKeydown(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) { ev.preventDefault(); this.sendMessage(); }
    }
    useSuggestion(text) { this.state.inputText = text; this.sendMessage(); }
    copyMessage(msg) { navigator.clipboard.writeText(msg.text); }

    _scrollBottom() {
        setTimeout(() => {
            const el = this.chatBody.el;
            if (el) el.scrollTop = el.scrollHeight;
        }, 60);
    }

    // ── Format response (markdown → HTML + charts) ───────────────────────────
    formatResponse(text) {
        if (!text) return markup("");
        let t = text;

        // ── Chart data parser ────────────────────────────────────────────────
        const parsePairs = s => s.split(',').map(p => {
            const i = p.indexOf(':'); if (i < 0) return null;
            const label = p.slice(0, i).trim();
            const val = parseFloat(p.slice(i+1).replace(/[^\d.\-]/g,'')) || 0;
            const raw = p.slice(i+1).trim();
            return { label, val, raw };
        }).filter(Boolean);

        // ── BAR CHART (horizontal) ───────────────────────────────────────────
        t = t.replace(/\[GRAFICO:barra,(.*?)\]/g, (_, ds) => {
            const data = parsePairs(ds);
            const mx = Math.max(...data.map(d=>d.val), 1);
            let h = `<div class="ai-chart"><div class="ai-chart-title">Gráfico de barras</div>`;
            data.forEach((d, i) => {
                const c = PALETTE[i % PALETTE.length];
                const p = Math.max((d.val / mx) * 100, 4);
                h += `<div style="margin-bottom:8px">
                    <div style="display:flex;justify-content:space-between;font-size:.82em;margin-bottom:3px">
                        <span style="font-weight:600;color:#333">${d.label}</span>
                        <span style="color:${c};font-weight:700">${d.raw}</span>
                    </div>
                    <div style="background:#f0f2f5;border-radius:8px;height:10px;overflow:hidden">
                        <div style="background:${c};width:${p}%;height:100%;border-radius:8px;transition:width .6s ease"></div>
                    </div>
                </div>`;
            });
            return h + '</div>';
        });

        // ── PIE / CIRCULAR CHART ─────────────────────────────────────────────
        t = t.replace(/\[GRAFICO:circular,(.*?)\]/g, (_, ds) => {
            const data = parsePairs(ds);
            const total = data.reduce((s,d)=>s+d.val,0) || 1;
            // Build SVG donut
            const R = 70, CX = 80, CY = 80, C = 2 * Math.PI * R;
            let offset = 0;
            let svg = `<svg viewBox="0 0 160 160" style="width:120px;height:120px;flex-shrink:0">`;
            data.forEach((d, i) => {
                const pct = d.val / total;
                const dash = C * pct;
                const gap = C - dash;
                svg += `<circle cx="${CX}" cy="${CY}" r="${R}" fill="none" stroke="${PALETTE[i%PALETTE.length]}" stroke-width="18" stroke-dasharray="${dash} ${gap}" stroke-dashoffset="${-offset}" transform="rotate(-90 ${CX} ${CY})"/>`;
                offset += dash;
            });
            svg += `<text x="${CX}" y="${CY+4}" text-anchor="middle" font-size="14" font-weight="700" fill="#333">${data.length}</text>`;
            svg += `</svg>`;
            let legend = `<div style="flex:1;min-width:140px">`;
            data.forEach((d, i) => {
                const pct = ((d.val / total) * 100).toFixed(1);
                legend += `<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;font-size:.82em">
                    <div style="width:10px;height:10px;border-radius:3px;background:${PALETTE[i%PALETTE.length]};flex-shrink:0"></div>
                    <span style="flex:1;color:#555">${d.label}</span>
                    <span style="font-weight:700;color:#333">${pct}%</span>
                </div>`;
            });
            legend += `</div>`;
            return `<div class="ai-chart"><div class="ai-chart-title">Distribución</div><div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap">${svg}${legend}</div></div>`;
        });

        // ── LINE CHART ───────────────────────────────────────────────────────
        t = t.replace(/\[GRAFICO:linea,(.*?)\]/g, (_, ds) => {
            const data = parsePairs(ds);
            const mx = Math.max(...data.map(d=>d.val), 1);
            const W = 400, H = 130, PX = 10, PY = 20;
            const sx = data.length > 1 ? (W - PX*2) / (data.length-1) : 0;
            const pts = data.map((d, i) => ({
                x: PX + i*sx,
                y: H - PY - ((d.val/mx) * (H - PY*2)),
                ...d
            }));
            const poly = pts.map(p => `${p.x},${p.y}`).join(' ');
            // Gradient fill
            const fillPts = [...pts.map(p=>`${p.x},${p.y}`), `${pts[pts.length-1].x},${H-PY}`, `${pts[0].x},${H-PY}`].join(' ');
            let svg = `<div class="ai-chart"><div class="ai-chart-title">Tendencia</div><svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto">`;
            svg += `<defs><linearGradient id="lg" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#004274" stop-opacity=".15"/><stop offset="100%" stop-color="#004274" stop-opacity="0"/></linearGradient></defs>`;
            svg += `<polygon points="${fillPts}" fill="url(#lg)"/>`;
            svg += `<polyline points="${poly}" fill="none" stroke="#004274" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>`;
            pts.forEach(p => {
                svg += `<circle cx="${p.x}" cy="${p.y}" r="4" fill="#004274" stroke="white" stroke-width="2"/>`;
                svg += `<text x="${p.x}" y="${H-4}" text-anchor="middle" font-size="8" fill="#888">${p.label}</text>`;
                svg += `<text x="${p.x}" y="${p.y-10}" text-anchor="middle" font-size="8" fill="#004274" font-weight="bold">${p.raw}</text>`;
            });
            return svg + '</svg></div>';
        });

        // ── HISTOGRAM ────────────────────────────────────────────────────────
        t = t.replace(/\[GRAFICO:histograma,(.*?)\]/g, (_, ds) => {
            const data = parsePairs(ds);
            const mx = Math.max(...data.map(d=>d.val), 1);
            const W = 400, H = 130, PY = 22;
            const barW = (W - 20) / data.length;
            let svg = `<div class="ai-chart"><div class="ai-chart-title">Histograma</div><svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto">`;
            data.forEach((d, i) => {
                const bh = (d.val / mx) * (H - PY * 2);
                const x = 10 + i * barW;
                const y = H - PY - bh;
                svg += `<rect x="${x}" y="${y}" width="${barW - 1}" height="${bh}" rx="2" fill="${PALETTE[i%PALETTE.length]}" opacity=".85"/>`;
                svg += `<text x="${x + barW/2}" y="${H-5}" text-anchor="middle" font-size="7.5" fill="#888">${d.label}</text>`;
                svg += `<text x="${x + barW/2}" y="${y-4}" text-anchor="middle" font-size="7.5" fill="#333" font-weight="600">${d.raw}</text>`;
            });
            return svg + '</svg></div>';
        });

        // ── SCATTER / DISPERSIÓN ─────────────────────────────────────────────
        t = t.replace(/\[GRAFICO:dispersion,(.*?)\]/g, (_, ds) => {
            const data = parsePairs(ds);
            const mxV = Math.max(...data.map(d=>d.val), 1);
            const W = 400, H = 140, PX = 30, PY = 22;
            let svg = `<div class="ai-chart"><div class="ai-chart-title">Dispersión</div><svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto">`;
            // Axes
            svg += `<line x1="${PX}" y1="${H-PY}" x2="${W-10}" y2="${H-PY}" stroke="#ddd" stroke-width="1"/>`;
            svg += `<line x1="${PX}" y1="10" x2="${PX}" y2="${H-PY}" stroke="#ddd" stroke-width="1"/>`;
            data.forEach((d, i) => {
                const x = PX + (i / Math.max(data.length-1, 1)) * (W - PX - 10);
                const y = H - PY - (d.val / mxV) * (H - PY - 14);
                svg += `<circle cx="${x}" cy="${y}" r="6" fill="${PALETTE[i%PALETTE.length]}" opacity=".75" stroke="white" stroke-width="1.5"/>`;
                svg += `<text x="${x}" y="${H-6}" text-anchor="middle" font-size="7.5" fill="#888">${d.label}</text>`;
                svg += `<text x="${x}" y="${y-10}" text-anchor="middle" font-size="7.5" fill="#333" font-weight="600">${d.raw}</text>`;
            });
            return svg + '</svg></div>';
        });

        // ── GANTT ────────────────────────────────────────────────────────────
        t = t.replace(/\[GRAFICO:gantt,(.*?)\]/g, (_, ds) => {
            const data = parsePairs(ds);
            const mx = Math.max(...data.map(d=>d.val), 1);
            let h = `<div class="ai-chart"><div class="ai-chart-title">Cronograma</div>`;
            data.forEach((d, i) => {
                const c = PALETTE[i % PALETTE.length];
                const w = Math.max((d.val / mx) * 100, 8);
                h += `<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px">
                    <div style="width:90px;font-size:.78em;font-weight:600;color:#555;text-align:right;flex-shrink:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${d.label}</div>
                    <div style="flex:1;background:#f0f2f5;border-radius:6px;height:18px;position:relative">
                        <div style="background:${c};width:${w}%;height:100%;border-radius:6px;display:flex;align-items:center;padding-left:6px">
                            <span style="font-size:.7em;color:white;font-weight:600">${d.raw}</span>
                        </div>
                    </div>
                </div>`;
            });
            return h + '</div>';
        });

        // ── HEATMAP / MAPA DE CALOR ──────────────────────────────────────────
        t = t.replace(/\[GRAFICO:calor,(.*?)\]/g, (_, ds) => {
            const data = parsePairs(ds);
            const mx = Math.max(...data.map(d=>d.val), 1);
            const mn = Math.min(...data.map(d=>d.val));
            let h = `<div class="ai-chart"><div class="ai-chart-title">Mapa de calor</div><div style="display:flex;flex-wrap:wrap;gap:4px">`;
            data.forEach(d => {
                const intensity = (d.val - mn) / (mx - mn || 1);
                const r = Math.round(0 + intensity * 229);
                const g = Math.round(66 - intensity * 9);
                const b = Math.round(116 - intensity * 63);
                const bg = `rgb(${r},${g},${b})`;
                const txt = intensity > 0.5 ? 'white' : '#333';
                h += `<div style="flex:1;min-width:70px;background:${bg};color:${txt};border-radius:8px;padding:10px;text-align:center">
                    <div style="font-size:.72em;font-weight:500;opacity:.8">${d.label}</div>
                    <div style="font-size:1.1em;font-weight:700">${d.raw}</div>
                </div>`;
            });
            return h + '</div></div>';
        });

        // ── Tables ───────────────────────────────────────────────────────────
        t = t.replace(/(?:\|.+\|\n?)+/g, match => {
            const rows = match.trim().split('\n');
            let html = '<div class="table-responsive my-2"><table class="table table-sm table-bordered" style="font-size:.82em;background:white;border-radius:8px;overflow:hidden">';
            let isFirstRow = true;
            rows.forEach(row => {
                if (row.includes('---')) { isFirstRow = false; return; }
                const cols = row.split('|').filter((c,i,a)=>i>0&&i<a.length-1);
                html += '<tr>' + cols.map(c => isFirstRow
                    ? `<th style="background:#f0f4f8;font-weight:600;color:#004274;padding:8px 10px">${c.trim()}</th>`
                    : `<td style="padding:7px 10px">${c.trim()}</td>`
                ).join('') + '</tr>';
                isFirstRow = false;
            });
            return html + '</table></div>';
        });

        // ── Markdown formatting ──────────────────────────────────────────────
        // Headers
        t = t.replace(/^####\s+(.+)$/gm, '<h6 style="color:#004274;font-weight:700;margin:10px 0 4px;font-size:.85em">$1</h6>');
        t = t.replace(/^###\s+(.+)$/gm, '<h5 style="color:#004274;font-weight:700;margin:12px 0 6px;font-size:.92em">$1</h5>');
        t = t.replace(/^##\s+(.+)$/gm, '<h4 style="color:#004274;font-weight:700;margin:14px 0 6px">$1</h4>');

        // Lists
        t = t.replace(/^\* (.+)$/gm, '<li style="margin-bottom:2px">$1</li>');
        t = t.replace(/(<li.*<\/li>\n?)+/g, '<ul style="padding-left:18px;margin:6px 0">$&</ul>');

        // Bold, italic, code, newlines
        t = t
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n\n/g, '<br><br>')
            .replace(/\n/g, '<br>');

        return markup(t);
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
            <span class="ai-spinner"/>
            procesando
          </span>
        </t>
      </div>
      <div style="display:flex;gap:6px;align-items:center">
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
                <span class="ai-session-count" t-esc="sess.count + ' msgs'"/>
              </div>
              <button class="ai-session-del" t-on-click="(ev) => this.deleteSession(sess.session_id, ev)" title="Eliminar">
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
              <div class="ai-chips-grid">
                <t t-foreach="['¿Cuántas propiedades disponibles?','Leads más calientes','Pagos vencidos','Estadísticas del mes','Crea un lead nuevo','Resumen ejecutivo']" t-as="chip" t-key="chip_index">
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
              <div t-att-class="'ai-bubble ai-bubble-bot' + (msg.streaming ? ' ai-bubble-streaming' : '')">
                <!-- Confirmation warning -->
                <t t-if="msg.text and msg.text.includes('CONFIRMACIÓN REQUERIDA')">
                  <div class="ai-confirm-banner">
                    ${SVG.warning} Acción destructiva — confirma antes de continuar
                  </div>
                </t>

                <!-- Status phase (streaming, no text yet) -->
                <t t-if="msg.streaming and msg.statusPhase and !msg.isError">
                  <div class="ai-status-indicator">
                    ${SVG.spinner}
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
                <div class="ai-bubble-actions" t-if="!msg.streaming">
                  <button class="ai-action-btn" t-on-click="() => this.copyMessage(msg)" title="Copiar">${SVG.copy}</button>
                </div>
                <div class="ai-msg-time" t-esc="msg.date"/>
              </div>
            </div>
          </t>
        </div>

        <!-- Chips -->
        <t t-if="state.messages.length and !state.loading">
          <div class="ai-chips-bar">
            <t t-foreach="['Propiedades disponibles','Leads calientes','Pagos vencidos','Crear propiedad','Ver estadísticas']" t-as="chip" t-key="chip_index">
              <button class="ai-chip-sm" t-on-click="() => this.useSuggestion(chip)" t-esc="chip"/>
            </t>
          </div>
        </t>

        <!-- Input -->
        <div class="ai-input-bar">
          <textarea
            class="ai-input"
            placeholder="Escribe tu consulta o pídeme que haga algo..."
            t-model="state.inputText"
            t-on-keydown="onKeydown"
            rows="2"
          />
          <button class="ai-send-btn"
                  t-on-click="() => this.sendMessage()"
                  t-att-disabled="state.loading or !state.inputText.trim()">
            <t t-if="state.loading">${SVG.spinner}</t>
            <t t-else="">${SVG.send}</t>
          </button>
        </div>
      </div>
    </div>
  </div>
</div>
`;

registry.category("main_components").add("estate_ai_chat_float_container", {
    Component: AIChatFloatContainer,
});
