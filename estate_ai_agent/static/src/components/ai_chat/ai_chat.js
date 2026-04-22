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

    formatResponse(text) {
        if (!text) return "";
        let html = text;

        // Tables
        html = html.replace(/(?:\|.+\|\n?)+/g, match => {
            const rows = match.trim().split('\n');
            let table = '<div class="table-responsive my-2"><table class="table table-sm table-bordered estate-ai-table" style="background:white;border-radius:8px;overflow:hidden">';
            let isFirst = true;
            rows.forEach(row => {
                if (row.includes('---')) { isFirst = false; return; }
                const cols = row.split('|').filter((c,i,a)=>i>0&&i<a.length-1);
                table += '<tr>' + cols.map(c => isFirst
                    ? `<th style="background:#f0f4f8;font-weight:600;color:#004274;padding:8px 10px">${c.trim()}</th>`
                    : `<td style="padding:7px 10px">${c.trim()}</td>`
                ).join('') + '</tr>';
                isFirst = false;
            });
            return table + '</table></div>';
        });

        // Headers
        html = html.replace(/^####\s+(.+)$/gm, '<h6 style="color:#004274;font-weight:700;margin:10px 0 4px;font-size:.85em">$1</h6>');
        html = html.replace(/^###\s+(.+)$/gm, '<h5 style="color:#004274;font-weight:700;margin:12px 0 6px;font-size:.92em">$1</h5>');
        html = html.replace(/^##\s+(.+)$/gm, '<h4 style="color:#004274;font-weight:700;margin:14px 0 6px">$1</h4>');

        // Lists
        html = html.replace(/^\* (.+)$/gm, '<li style="margin-bottom:2px">$1</li>');
        html = html.replace(/(<li.*<\/li>\n?)+/g, '<ul style="padding-left:18px;margin:6px 0">$&</ul>');

        // Bold, italic, code
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
