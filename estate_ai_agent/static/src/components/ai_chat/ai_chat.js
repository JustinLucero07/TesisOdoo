/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, useRef, onMounted } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

// Contextual chips shown after first bot response
const CONTEXTUAL_CHIPS = [
    '¿Cuántas propiedades disponibles hay?',
    'Muestra leads calientes',
    'Pagos vencidos',
    'Estadísticas del mes',
    'Recordar esta preferencia',
    'Genera PDF de cotización',
];

export class EstateAIChat extends Component {
    setup() {
        this.state = useState({
            messages: [],
            inputText: "",
            loading: false,
            suggestions: [],
            showChips: false,
            ocrMode: false,
            ocrResult: null,
            statusText: "",
        });
        this.chatBody = useRef("chatBody");
        this.fileInput = useRef("fileInput");

        onMounted(async () => {
            await this.loadHistory();
            await this.loadSuggestions();
        });
    }

    async loadHistory() {
        try {
            const history = await rpc("/estate_ai/history", { limit: 20 });
            if (history && history.length) {
                for (const item of history) {
                    this.state.messages.push(
                        { type: "user", text: item.query, date: item.date },
                        { type: "bot", text: item.response, date: item.date }
                    );
                }
                this.state.showChips = true;
                this.scrollToBottom();
            }
        } catch (e) {
            console.error("Error loading history:", e);
        }
    }

    async loadSuggestions() {
        try {
            const suggestions = await rpc("/estate_ai/suggestions", {});
            this.state.suggestions = suggestions || [];
        } catch (e) {
            console.error("Error loading suggestions:", e);
        }
    }

    async sendMessage(overrideText) {
        const text = (overrideText || this.state.inputText).trim();
        if (!text || this.state.loading) return;

        this.state.messages.push({ type: "user", text, date: "Ahora" });
        this.state.inputText = "";
        this.state.loading = true;
        this.state.showChips = false;
        this.scrollToBottom();

        // Placeholder bot message
        this.state.messages.push({
            type: "bot",
            text: "",
            date: "Ahora",
            streaming: true,
            statusPhase: "searching",
        });
        const botIdx = this.state.messages.length - 1;
        this.scrollToBottom();

        try {
            const csrfToken = odoo.csrf_token;
            const response = await fetch("/estate_ai/chat/stream", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken,
                },
                body: JSON.stringify({ message: text }),
            });

            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let accumulatedText = "";
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
                        if (chunk.status && !accumulatedText) {
                            this.state.messages[botIdx].text = chunk.status;
                            this.state.messages[botIdx].statusPhase = "processing";
                        } else if (chunk.text) {
                            accumulatedText += chunk.text;
                            this.state.messages[botIdx].text = accumulatedText;
                            this.state.messages[botIdx].statusPhase = null;
                            this.scrollToBottom();
                        } else if (chunk.error) {
                            this.state.messages[botIdx].text = chunk.error;
                            this.state.messages[botIdx].isError = true;
                        }
                    } catch (_) {}
                }
            }

            if (!accumulatedText) {
                this.state.messages[botIdx].text = this.state.messages[botIdx].text || "Sin respuesta del asistente.";
            }
            this.state.messages[botIdx].streaming = false;
            this.state.messages[botIdx].statusPhase = null;
            this.state.messages[botIdx].copyable = true;
        } catch (e) {
            this.state.messages[botIdx].text = `Error de conexión con el agente IA: ${e.message}`;
            this.state.messages[botIdx].streaming = false;
            this.state.messages[botIdx].isError = true;
        }

        this.state.loading = false;
        this.state.showChips = true;
        this.scrollToBottom();
    }

    onKeydown(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.sendMessage();
        }
    }

    useSuggestion(suggestion) {
        this.state.inputText = suggestion;
        this.sendMessage();
    }

    useChip(chip) {
        this.state.inputText = chip;
        this.sendMessage();
    }

    copyMessage(msg) {
        navigator.clipboard.writeText(msg.text).then(() => {
            msg.copied = true;
            setTimeout(() => { msg.copied = false; }, 2000);
        });
    }

    clearChat() {
        this.state.messages = [];
        this.state.showChips = false;
    }

    toggleOcrMode() {
        this.state.ocrMode = !this.state.ocrMode;
        this.state.ocrResult = null;
    }

    triggerFileUpload() {
        if (this.fileInput.el) this.fileInput.el.click();
    }

    async onFileSelected(ev) {
        const file = ev.target.files[0];
        if (!file) return;

        this.state.loading = true;
        this.state.ocrResult = null;
        this.state.messages.push({
            type: "user",
            text: `Archivo subido: ${file.name}`,
            date: "Ahora",
        });
        this.state.messages.push({
            type: "bot",
            text: "",
            date: "Ahora",
            streaming: true,
            statusPhase: "processing",
        });
        const botIdx = this.state.messages.length - 1;
        this.scrollToBottom();

        try {
            const formData = new FormData();
            formData.append("file", file);
            formData.append("extract_type", "auto");

            const response = await fetch("/estate_ai/ocr", {
                method: "POST",
                headers: { "X-CSRFToken": odoo.csrf_token },
                body: formData,
            });
            const result = await response.json();

            if (result.success && result.extracted) {
                const lines = Object.entries(result.extracted)
                    .map(([k, v]) => `**${k}**: ${v}`)
                    .join("\n");
                this.state.messages[botIdx].text =
                    `**Datos extraídos de ${file.name}:**\n\n${lines}\n\n` +
                    `_¿Quieres que registre estos datos en el sistema? Dime qué hacer con ellos._`;
                this.state.ocrResult = result.extracted;
            } else {
                this.state.messages[botIdx].text = `Error OCR: ${result.error || 'No se pudo procesar el archivo.'}`;
                this.state.messages[botIdx].isError = true;
            }
            this.state.messages[botIdx].streaming = false;
            this.state.messages[botIdx].statusPhase = null;
        } catch (e) {
            this.state.messages[botIdx].text = "Error al subir el archivo.";
            this.state.messages[botIdx].streaming = false;
            this.state.messages[botIdx].isError = true;
        }

        this.state.loading = false;
        this.state.ocrMode = false;
        this.scrollToBottom();
        ev.target.value = "";
    }

    scrollToBottom() {
        setTimeout(() => {
            const el = this.chatBody.el;
            if (el) el.scrollTop = el.scrollHeight;
        }, 80);
    }

    // ── SVG Chart Helpers ──────────────────────────────────────────────

    _chartBar(entries, cid) {
        const COLORS = ['#1877F2','#004274','#00897B','#E53935','#FF9800','#7c3aed','#00ACC1','#43A047'];
        const maxVal = Math.max(...entries.map(e => e.val), 1);
        const W = 380, H = 165, padL = 12, padR = 12, padTop = 22, padBot = 48;
        const plotW = W - padL - padR;
        const plotH = H - padTop - padBot;
        const step = plotW / entries.length;
        const bw = Math.max(Math.floor(step * 0.6), 4);

        let bars = '', vals = '', labels = '';
        entries.forEach((e, i) => {
            const x = padL + i * step + (step - bw) / 2;
            const bh = Math.max((e.val / maxVal) * plotH, 2);
            const y = padTop + plotH - bh;
            const col = COLORS[i % COLORS.length];
            bars += `<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${bw}" height="${bh.toFixed(1)}" fill="${col}" rx="3" opacity=".92"/>`;
            const dv = e.val >= 1000000 ? `$${(e.val/1000000).toFixed(1)}M`
                     : e.val >= 1000 ? `$${(e.val/1000).toFixed(0)}K`
                     : e.val % 1 === 0 ? e.val : e.val.toFixed(1);
            vals += `<text x="${(x+bw/2).toFixed(1)}" y="${(y-4).toFixed(1)}" text-anchor="middle" font-size="9" fill="#333" font-family="sans-serif">${dv}</text>`;
            const lbl = e.label.length > 14 ? e.label.slice(0,13)+'…' : e.label;
            const lx = (x + bw/2).toFixed(1), ly = (padTop + plotH + 14).toFixed(1);
            labels += `<text x="${lx}" y="${ly}" text-anchor="end" font-size="8.5" fill="#555" font-family="sans-serif" transform="rotate(-30,${lx},${ly})">${lbl}</text>`;
        });

        const dl = `(function(){var s=document.getElementById('${cid}');var d='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(s.outerHTML);var a=document.createElement('a');a.href=d;a.download='grafico.svg';a.click();})()`;
        return `<div style="background:#f8faff;border-radius:12px;padding:12px 8px 6px;margin:10px 0;box-shadow:0 2px 8px rgba(0,0,0,.07);border:1px solid #dde8f5">
            <svg id="${cid}" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" style="width:100%;display:block">
                <rect width="${W}" height="${H}" fill="#f8faff" rx="8"/>
                <line x1="${padL}" y1="${padTop+plotH}" x2="${W-padR}" y2="${padTop+plotH}" stroke="#d1d5db" stroke-width="1"/>
                ${bars}${vals}${labels}
            </svg>
            <div style="text-align:right;margin-top:2px">
                <button onclick="${dl}" style="font-size:11px;color:#1877F2;border:1px solid #1877F2;background:white;border-radius:5px;padding:2px 10px;cursor:pointer;font-family:sans-serif">
                    <i class='fa fa-download'></i> Descargar SVG
                </button>
            </div>
        </div>`;
    }

    _chartPie(entries, cid) {
        const COLORS = ['#1877F2','#00897B','#E53935','#FF9800','#7c3aed','#004274','#00ACC1','#43A047'];
        const total = entries.reduce((s,e) => s + Math.max(e.val, 0), 0) || 1;
        const cx = 90, cy = 80, r = 68;
        let slices = '', legend = '';
        let angle = -Math.PI / 2;
        entries.slice(0, 8).forEach((e, i) => {
            const pct = Math.max(e.val, 0) / total;
            if (pct <= 0) return;
            const a1 = angle, a2 = angle + pct * 2 * Math.PI;
            const x1 = cx + r * Math.cos(a1), y1 = cy + r * Math.sin(a1);
            const x2 = cx + r * Math.cos(a2), y2 = cy + r * Math.sin(a2);
            const large = pct > 0.5 ? 1 : 0;
            slices += `<path d="M${cx},${cy} L${x1.toFixed(2)},${y1.toFixed(2)} A${r},${r} 0 ${large},1 ${x2.toFixed(2)},${y2.toFixed(2)} Z" fill="${COLORS[i%COLORS.length]}" stroke="white" stroke-width="1.5" opacity=".92"/>`;
            const la = angle + pct * Math.PI, lr = r * 0.62;
            const lx = cx + lr * Math.cos(la), ly = cy + lr * Math.sin(la);
            if (pct > 0.06) {
                slices += `<text x="${lx.toFixed(1)}" y="${ly.toFixed(1)}" text-anchor="middle" dominant-baseline="middle" font-size="8.5" font-weight="600" fill="white" font-family="sans-serif">${(pct*100).toFixed(0)}%</text>`;
            }
            const lbl = e.label.length > 18 ? e.label.slice(0,17)+'…' : e.label;
            legend += `<rect x="198" y="${14+i*18}" width="10" height="10" fill="${COLORS[i%COLORS.length]}" rx="2"/>
                       <text x="212" y="${23+i*18}" font-size="9.5" fill="#444" font-family="sans-serif">${lbl} (${e.val})</text>`;
            angle = a2;
        });

        const dl = `(function(){var s=document.getElementById('${cid}');var d='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(s.outerHTML);var a=document.createElement('a');a.href=d;a.download='grafico.svg';a.click();})()`;
        return `<div style="background:#f8faff;border-radius:12px;padding:12px 8px 6px;margin:10px 0;box-shadow:0 2px 8px rgba(0,0,0,.07);border:1px solid #dde8f5">
            <svg id="${cid}" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 380 165" style="width:100%;display:block">
                <rect width="380" height="165" fill="#f8faff" rx="8"/>
                ${slices}${legend}
            </svg>
            <div style="text-align:right;margin-top:2px">
                <button onclick="${dl}" style="font-size:11px;color:#1877F2;border:1px solid #1877F2;background:white;border-radius:5px;padding:2px 10px;cursor:pointer;font-family:sans-serif">
                    <i class='fa fa-download'></i> Descargar SVG
                </button>
            </div>
        </div>`;
    }

    _chartLine(entries, cid) {
        const W = 380, H = 140, padL = 40, padR = 12, padTop = 16, padBot = 40;
        const plotW = W - padL - padR;
        const plotH = H - padTop - padBot;
        const vals = entries.map(e => e.val);
        const maxV = Math.max(...vals, 1), minV = Math.min(...vals, 0);
        const range = maxV - minV || 1;

        const pts = entries.map((e, i) => {
            const x = padL + i * plotW / Math.max(entries.length - 1, 1);
            const y = padTop + plotH - ((e.val - minV) / range) * plotH;
            return { x, y, label: e.label, val: e.val };
        });

        const polyline = pts.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
        const areaBase = padTop + plotH;
        const area = `M${pts[0].x.toFixed(1)},${areaBase} ` + pts.map(p => `L${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ') + ` L${pts[pts.length-1].x.toFixed(1)},${areaBase} Z`;

        let dots = '', labels = '';
        pts.forEach((p, i) => {
            dots += `<circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="4" fill="#1877F2" stroke="white" stroke-width="1.5"/>`;
            const dv = p.val >= 1000 ? `$${(p.val/1000).toFixed(0)}K` : p.val % 1 === 0 ? p.val : p.val.toFixed(1);
            dots += `<text x="${p.x.toFixed(1)}" y="${(p.y-8).toFixed(1)}" text-anchor="middle" font-size="8.5" fill="#004274" font-family="sans-serif" font-weight="600">${dv}</text>`;
            const lbl = p.label.length > 10 ? p.label.slice(0,9)+'…' : p.label;
            labels += `<text x="${p.x.toFixed(1)}" y="${(padTop+plotH+14).toFixed(1)}" text-anchor="end" font-size="8" fill="#666" font-family="sans-serif" transform="rotate(-30,${p.x.toFixed(1)},${(padTop+plotH+14).toFixed(1)})">${lbl}</text>`;
        });

        const ySteps = 4;
        let grid = '';
        for (let s = 0; s <= ySteps; s++) {
            const y = padTop + (s / ySteps) * plotH;
            const v = maxV - (s / ySteps) * range;
            const lv = v >= 1000 ? `${(v/1000).toFixed(0)}K` : v.toFixed(0);
            grid += `<line x1="${padL}" y1="${y.toFixed(1)}" x2="${W-padR}" y2="${y.toFixed(1)}" stroke="#e5e7eb" stroke-width="0.8"/>`;
            grid += `<text x="${(padL-4).toFixed(1)}" y="${(y+3).toFixed(1)}" text-anchor="end" font-size="8" fill="#9ca3af" font-family="sans-serif">${lv}</text>`;
        }

        const dl = `(function(){var s=document.getElementById('${cid}');var d='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(s.outerHTML);var a=document.createElement('a');a.href=d;a.download='grafico.svg';a.click();})()`;
        return `<div style="background:#f8faff;border-radius:12px;padding:12px 8px 6px;margin:10px 0;box-shadow:0 2px 8px rgba(0,0,0,.07);border:1px solid #dde8f5">
            <svg id="${cid}" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" style="width:100%;display:block">
                <rect width="${W}" height="${H}" fill="#f8faff" rx="8"/>
                ${grid}
                <path d="${area}" fill="#1877F2" opacity=".08"/>
                <polyline points="${polyline}" fill="none" stroke="#1877F2" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>
                ${dots}${labels}
            </svg>
            <div style="text-align:right;margin-top:2px">
                <button onclick="${dl}" style="font-size:11px;color:#1877F2;border:1px solid #1877F2;background:white;border-radius:5px;padding:2px 10px;cursor:pointer;font-family:sans-serif">
                    <i class='fa fa-download'></i> Descargar SVG
                </button>
            </div>
        </div>`;
    }

    formatResponse(text) {
        if (!text) return "";
        let html = text;

        // 1. Parse [GRAFICO:tipo,Label:Val,...] → real SVG charts
        html = html.replace(/\[GRAFICO:(barra|circular|linea),([^\]]+)\]/g, (match, type, dataStr) => {
            try {
                const entries = [];
                dataStr.split(',').forEach(item => {
                    const idx = item.lastIndexOf(':');
                    if (idx > 0) {
                        const label = item.slice(0, idx).trim();
                        const val = parseFloat(item.slice(idx + 1));
                        if (label && !isNaN(val)) entries.push({ label, val });
                    }
                });
                if (!entries.length) return match;
                const cid = 'c' + Math.random().toString(36).slice(2, 10);
                if (type === 'barra')    return this._chartBar(entries, cid);
                if (type === 'circular') return this._chartPie(entries, cid);
                if (type === 'linea')    return this._chartLine(entries, cid);
            } catch(_) {}
            return match;
        });

        // 2. Download links  [Descargar texto](url)  → styled button
        html = html.replace(/\[Descargar ([^\]]+)\]\(([^)]+)\)/g,
            '<a href="$2" class="btn btn-sm btn-outline-primary mt-1" style="border-radius:6px;text-decoration:none" download><i class="fa fa-download"></i> $1</a>');

        // 3. Generic markdown links [text](url)
        html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g,
            '<a href="$2" target="_blank" style="color:#1877F2;text-decoration:underline;font-weight:500">$1</a>');

        // 4. Tables
        html = html.replace(/(?:\|.+\|\n?)+/g, match => {
            const rows = match.trim().split('\n');
            let table = '<div class="table-responsive my-2"><table class="table table-sm table-bordered estate-ai-table" style="background:white;border-radius:8px;overflow:hidden">';
            let isFirst = true;
            rows.forEach(row => {
                if (row.includes('---')) { isFirst = false; return; }
                const cols = row.split('|').filter((c,i,a) => i > 0 && i < a.length - 1);
                table += '<tr>' + cols.map(c => isFirst
                    ? `<th style="background:#f0f4f8;font-weight:600;color:#004274;padding:8px 10px">${c.trim()}</th>`
                    : `<td style="padding:7px 10px">${c.trim()}</td>`
                ).join('') + '</tr>';
                isFirst = false;
            });
            return table + '</table></div>';
        });

        // 5. Headers
        html = html.replace(/^####\s+(.+)$/gm, '<h6 style="color:#004274;font-weight:700;margin:10px 0 4px;font-size:.85em">$1</h6>');
        html = html.replace(/^###\s+(.+)$/gm, '<h5 style="color:#004274;font-weight:700;margin:12px 0 6px;font-size:.92em">$1</h5>');
        html = html.replace(/^##\s+(.+)$/gm, '<h4 style="color:#004274;font-weight:700;margin:14px 0 6px">$1</h4>');

        // 6. Lists
        html = html.replace(/^\* (.+)$/gm, '<li style="margin-bottom:2px">$1</li>');
        html = html.replace(/(<li.*<\/li>\n?)+/g, '<ul style="padding-left:18px;margin:6px 0">$&</ul>');

        // 7. Bold, italic, code, line breaks
        html = html
            .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
            .replace(/\*(.*?)\*/g, "<em>$1</em>")
            .replace(/`(.*?)`/g, "<code>$1</code>")
            .replace(/\n\n/g, "<br/><br/>")
            .replace(/\n/g, "<br/>");

        return html;
    }

    isConfirmationNeeded(text) {
        return text && text.includes("CONFIRMACIÓN REQUERIDA");
    }
}

EstateAIChat.template = "estate_ai_agent.AIChat";

registry.category("actions").add("estate_ai_chat", EstateAIChat);
