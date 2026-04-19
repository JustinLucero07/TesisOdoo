/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, xml, useState, useRef, onMounted, markup } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

// ─── Generate a short unique session ID ──────────────────────────────────────
function newSessionId() {
    return "sess_" + Date.now().toString(36) + "_" + Math.random().toString(36).slice(2, 7);
}

export class AIChatFloatContainer extends Component {
    setup() {
        this.state = useState({
            isOpen: false,
            sidebarOpen: true,
            messages: [],
            inputText: "",
            loading: false,
            sessions: [],           // [{session_id, title, date, count}]
            activeSessionId: null,
            isMaximized: false,
        });
        this.chatBody = useRef("chatBody");
        this._initialized = false;
    }

    // ── Toggle open/close ─────────────────────────────────────────────────────
    async toggleChat() {
        this.state.isOpen = !this.state.isOpen;
        if (this.state.isOpen && !this._initialized) {
            this._initialized = true;
            await this._loadSessions();
            // Open last session or start fresh
            if (this.state.sessions.length) {
                await this._openSession(this.state.sessions[0].session_id);
            } else {
                this._startNewSession();
            }
        }
        if (this.state.isOpen) this._scrollBottom();
    }

    toggleSidebar() {
        this.state.sidebarOpen = !this.state.sidebarOpen;
    }

    toggleMaximize() {
        this.state.isMaximized = !this.state.isMaximized;
    }

    // ── Sessions ──────────────────────────────────────────────────────────────
    async _loadSessions() {
        try {
            const sessions = await rpc("/estate_ai/sessions", {});
            this.state.sessions = sessions || [];
        } catch (e) {
            console.error("Error loading sessions:", e);
        }
    }

    async _openSession(sessionId) {
        this.state.activeSessionId = sessionId;
        this.state.messages = [];
        this.state.loading = true;
        try {
            const msgs = await rpc("/estate_ai/session_messages", { session_id: sessionId });
            this.state.messages = (msgs || []).map(m => ({ ...m, id: Math.random() }));
        } catch (e) {
            console.error("Error loading session:", e);
        }
        this.state.loading = false;
        this._scrollBottom();
    }

    _startNewSession() {
        this.state.activeSessionId = newSessionId();
        this.state.messages = [];
    }

    async newChat() {
        this._startNewSession();
        // Refresh session list after next send
    }

    async deleteSession(sessionId, ev) {
        ev.stopPropagation();
        if (!confirm("¿Eliminar esta conversación?")) return;
        try {
            await rpc("/estate_ai/clear", { session_id: sessionId });
            this.state.sessions = this.state.sessions.filter(s => s.session_id !== sessionId);
            if (this.state.activeSessionId === sessionId) {
                if (this.state.sessions.length) {
                    await this._openSession(this.state.sessions[0].session_id);
                } else {
                    this._startNewSession();
                }
            }
        } catch (e) { console.error(e); }
    }

    // ── Send message ──────────────────────────────────────────────────────────
    async sendMessage(overrideText) {
        const text = (overrideText || this.state.inputText).trim();
        if (!text || this.state.loading) return;

        // If this is the first message in a new session, push to sidebar
        const isFirstMsg = this.state.messages.length === 0;

        this.state.messages.push({ id: Math.random(), type: "user", text, date: "Ahora" });
        this.state.inputText = "";
        this.state.loading = true;
        this._scrollBottom();

        const botMsg = { id: Math.random(), type: "bot", text: "⏳ Procesando...", date: "Ahora", streaming: true };
        this.state.messages.push(botMsg);
        const botIdx = this.state.messages.length - 1;
        this._scrollBottom();

        try {
            const response = await fetch("/estate_ai/chat/stream", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": odoo.csrf_token,
                },
                body: JSON.stringify({
                    message: text,
                    session_id: this.state.activeSessionId,
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
                            this.state.messages[botIdx].text = chunk.status;
                        } else if (chunk.text) {
                            accumulated += chunk.text;
                            this.state.messages[botIdx].text = accumulated;
                            this._scrollBottom();
                        } else if (chunk.error) {
                            this.state.messages[botIdx].text = `❌ ${chunk.error}`;
                        }
                    } catch (_) {}
                }
            }

            if (!accumulated) accumulated = this.state.messages[botIdx].text;
            this.state.messages[botIdx].streaming = false;

            // Update / add session in sidebar
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
            this.state.messages[botIdx].text = `❌ Error de conexión: ${e.message}`;
            this.state.messages[botIdx].streaming = false;
        }

        this.state.loading = false;
        this._scrollBottom();
    }

    onKeydown(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.sendMessage();
        }
    }

    useSuggestion(text) {
        this.state.inputText = text;
        this.sendMessage();
    }

    // ── Helpers ───────────────────────────────────────────────────────────────
    _scrollBottom() {
        setTimeout(() => {
            const el = this.chatBody.el;
            if (el) el.scrollTop = el.scrollHeight;
        }, 60);
    }

    copyMessage(msg) {
        navigator.clipboard.writeText(msg.text);
    }

    // ── Format response (markdown + charts + tables) ──────────────────────────
    formatResponse(text) {
        if (!text) return markup("");
        let t = text;

        const PALETTE = ['#017e84','#00bfa5','#2196F3','#FF9800','#9C27B0','#E91E63','#4CAF50','#FF5722','#607D8B','#FFC107'];
        const parsePairs = s => s.split(',').map(p => {
            const i = p.indexOf(':'); if (i < 0) return null;
            const label = p.slice(0, i).trim();
            const val = parseFloat(p.slice(i+1).replace(/[^\d.]/g,'')) || 0;
            const raw = p.slice(i+1).trim();
            return { label, val, raw };
        }).filter(Boolean);

        // Bar chart
        t = t.replace(/\[GRAFICO:barra,(.*?)\]/g, (_, ds) => {
            const data = parsePairs(ds); const mx = Math.max(...data.map(d=>d.val),1);
            let h = `<div class="ai-chart">`;
            data.forEach((d,i) => { const c=PALETTE[i%PALETTE.length]; const p=Math.max((d.val/mx)*100,3);
                h += `<div style="margin-bottom:10px"><div style="display:flex;justify-content:space-between;font-size:.82em;margin-bottom:3px"><span><b>${d.label}</b></span><span style="color:${c};font-weight:700">${d.raw}</span></div><div style="background:#eee;border-radius:6px;height:12px"><div style="background:${c};width:${p}%;height:100%;border-radius:6px"></div></div></div>`;
            });
            return h + '</div>';
        });

        // Pie chart
        t = t.replace(/\[GRAFICO:circular,(.*?)\]/g, (_, ds) => {
            const data = parsePairs(ds); const total = data.reduce((s,d)=>s+d.val,0)||1;
            let h = `<div class="ai-chart" style="display:flex;flex-wrap:wrap;gap:8px">`;
            data.forEach((d,i) => { const c=PALETTE[i%PALETTE.length]; const p=((d.val/total)*100).toFixed(1);
                h += `<div style="flex:1;min-width:100px;background:#f8f9fa;border-radius:10px;padding:10px;border-left:4px solid ${c}"><div style="font-size:.78em;font-weight:600;color:#444">${d.label}</div><div style="font-size:1.4em;font-weight:800;color:${c}">${p}%</div><div style="font-size:.72em;color:#888">${d.raw}</div></div>`;
            });
            return h + '</div>';
        });

        // Line chart
        t = t.replace(/\[GRAFICO:linea,(.*?)\]/g, (_, ds) => {
            const data = parsePairs(ds); const mx = Math.max(...data.map(d=>d.val),1);
            const W=380,H=110,P=28; const sx=data.length>1?(W-P*2)/(data.length-1):W-P*2;
            const pts = data.map((d,i)=>({x:P+i*sx, y:H-P-((d.val/mx)*(H-P*2)), ...d}));
            const poly = pts.map(p=>`${p.x},${p.y}`).join(' ');
            let h = `<div class="ai-chart"><svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto">`;
            h += `<polyline points="${poly}" fill="none" stroke="#017e84" stroke-width="2.5" stroke-linejoin="round"/>`;
            pts.forEach(p=>{h+=`<circle cx="${p.x}" cy="${p.y}" r="4" fill="#017e84"/><text x="${p.x}" y="${H-5}" text-anchor="middle" font-size="8" fill="#666">${p.label}</text><text x="${p.x}" y="${p.y-8}" text-anchor="middle" font-size="8" fill="#017e84" font-weight="bold">${p.raw}</text>`;});
            return h + '</svg></div>';
        });

        // Tables
        t = t.replace(/(?:\|.+\|\n?)+/g, match => {
            const rows = match.trim().split('\n');
            let html = '<div class="table-responsive my-2"><table class="table table-sm table-bordered" style="font-size:.82em;background:white">';
            let first = true;
            rows.forEach(row => {
                if (row.includes('---')) { first = false; return; }
                const cols = row.split('|').filter((c,i,a)=>i>0&&i<a.length-1);
                html += '<tr>' + cols.map(c => first ? `<th style="background:#f0f4f8">${c.trim()}</th>` : `<td>${c.trim()}</td>`).join('') + '</tr>';
                first = false;
            });
            return html + '</table></div>';
        });

        // Bold, italic, code, newlines
        t = t
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code style="background:#f0f0f0;padding:1px 4px;border-radius:3px;font-size:.85em">$1</code>')
            .replace(/\n\n/g, '<br><br>')
            .replace(/\n/g, '<br>');

        return markup(t);
    }
}

// ─── Template ─────────────────────────────────────────────────────────────────
AIChatFloatContainer.template = xml`
<div>
  <!-- ── FLOATING BUTTON ──────────────────────────────────────── -->
  <div t-on-click="toggleChat" class="ai-float-btn" t-att-class="state.isOpen ? 'ai-float-btn-active' : ''">
    <i t-attf-class="fa fa-2x text-white {{ state.isOpen ? 'fa-times' : 'fa-magic' }}"/>
    <t t-if="state.loading and state.isOpen">
      <span class="ai-float-pulse"/>
    </t>
  </div>

  <!-- ── CHAT WINDOW ──────────────────────────────────────────── -->
  <div t-if="state.isOpen" t-att-class="'ai-window' + (state.isMaximized ? ' ai-window-max' : '')">

    <!-- HEADER -->
    <div class="ai-header">
      <div style="display:flex;align-items:center;gap:10px">
        <button class="ai-icon-btn" t-on-click="toggleSidebar" title="Historial">
          <i class="fa fa-bars"/>
        </button>
        <span style="font-weight:700;font-size:15px">🤖 Agente IA Inmobiliario</span>
        <t t-if="state.loading">
          <span style="font-size:11px;opacity:.7;margin-left:4px">
            <i class="fa fa-circle-o-notch fa-spin"/> procesando...
          </span>
        </t>
      </div>
      <div style="display:flex;gap:6px;align-items:center">
        <button class="ai-icon-btn" t-on-click="newChat" title="Nueva conversación">
          <i class="fa fa-plus"/>
        </button>
        <button class="ai-icon-btn" t-on-click="toggleMaximize" title="Expandir/Reducir">
          <i t-attf-class="fa {{ state.isMaximized ? 'fa-compress' : 'fa-expand' }}"/>
        </button>
        <button class="ai-icon-btn" t-on-click="toggleChat" title="Cerrar">
          <i class="fa fa-times"/>
        </button>
      </div>
    </div>

    <!-- BODY (sidebar + chat) -->
    <div class="ai-body-wrapper">

      <!-- ── SIDEBAR ────────────────────────────────── -->
      <div t-if="state.sidebarOpen" class="ai-sidebar">
        <div class="ai-sidebar-header">
          <i class="fa fa-history"/> Conversaciones
        </div>

        <t t-if="!state.sessions.length">
          <div class="ai-sidebar-empty">
            <i class="fa fa-comments-o fa-2x" style="opacity:.3"/><br/>
            <small>Sin historial</small>
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
          <i class="fa fa-plus-circle"/> Nueva conversación
        </button>
      </div>

      <!-- ── CHAT AREA ──────────────────────────────── -->
      <div class="ai-chat-area">

        <!-- Messages -->
        <div class="ai-messages" t-ref="chatBody">
          <t t-if="!state.messages.length and !state.loading">
            <div class="ai-welcome">
              <div style="font-size:2.5em;margin-bottom:10px">🤖</div>
              <h5>¡Hola! Soy tu agente inmobiliario IA</h5>
              <p style="font-size:.88em;color:#888;margin-bottom:16px">
                Puedo consultar, crear y gestionar propiedades, leads, contratos y más.
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
              <div class="ai-avatar">🤖</div>
              <div t-att-class="'ai-bubble ai-bubble-bot' + (msg.streaming ? ' ai-bubble-streaming' : '')">
                <!-- Confirmation warning -->
                <t t-if="msg.text and msg.text.includes('CONFIRMACIÓN REQUERIDA')">
                  <div class="ai-confirm-banner">
                    <i class="fa fa-exclamation-triangle"/> Acción destructiva — confirma antes de continuar
                  </div>
                </t>
                <t t-out="formatResponse(msg.text)"/>
                <span t-if="msg.streaming" class="ai-cursor"/>
                <div class="ai-bubble-actions" t-if="!msg.streaming">
                  <button class="ai-action-btn" t-on-click="() => this.copyMessage(msg)" title="Copiar">
                    <i class="fa fa-copy"/>
                  </button>
                </div>
                <div class="ai-msg-time" t-esc="msg.date"/>
              </div>
            </div>
          </t>
        </div>

        <!-- Suggestion chips (after responses) -->
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
            <t t-if="state.loading">
              <i class="fa fa-spinner fa-spin"/>
            </t>
            <t t-else="">
              <i class="fa fa-paper-plane"/>
            </t>
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
