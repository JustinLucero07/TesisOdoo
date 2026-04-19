/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, useRef, onMounted } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

// Keywords that indicate a destructive/confirmation-required action
const DESTRUCTIVE_KEYWORDS = [
    'confirmo', 'sí confirmo', 'si confirmo', 'yes confirm', 'confirm',
];

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

        // Placeholder bot message, updated live via SSE
        this.state.messages.push({
            type: "bot",
            text: "🔍 Consultando base de datos...",
            date: "Ahora",
            streaming: true,
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
                        } else if (chunk.text) {
                            accumulatedText += chunk.text;
                            this.state.messages[botIdx].text = accumulatedText;
                            this.scrollToBottom();
                        } else if (chunk.error) {
                            this.state.messages[botIdx].text = `❌ ${chunk.error}`;
                        }
                    } catch (_) {}
                }
            }

            if (!accumulatedText) {
                this.state.messages[botIdx].text = "Sin respuesta del asistente.";
            }
            this.state.messages[botIdx].streaming = false;
            this.state.messages[botIdx].copyable = true;
        } catch (e) {
            this.state.messages[botIdx].text = "❌ Error de conexión con el agente IA.";
            this.state.messages[botIdx].streaming = false;
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
            text: `📎 Archivo subido: ${file.name}`,
            date: "Ahora",
        });
        this.state.messages.push({
            type: "bot",
            text: "🔍 Analizando documento con IA...",
            date: "Ahora",
            streaming: true,
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
                    `✅ **Datos extraídos de ${file.name}:**\n\n${lines}\n\n` +
                    `_¿Quieres que registre estos datos en el sistema? Dime qué hacer con ellos._`;
                this.state.ocrResult = result.extracted;
            } else {
                this.state.messages[botIdx].text = `❌ Error OCR: ${result.error || 'No se pudo procesar el archivo.'}`;
            }
            this.state.messages[botIdx].streaming = false;
        } catch (e) {
            this.state.messages[botIdx].text = "❌ Error al subir el archivo.";
            this.state.messages[botIdx].streaming = false;
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
        // Tables
        let html = text.replace(/\|(.+)\|/g, (match) => {
            const cells = match.split("|").filter(c => c.trim());
            const isHeader = text.indexOf(match) < text.indexOf("---");
            const tag = isHeader ? "th" : "td";
            return `<tr>${cells.map(c => `<${tag}>${c.trim()}</${tag}>`).join("")}</tr>`;
        });
        // Wrap table rows
        if (html.includes("<tr>")) {
            html = html.replace(/(<tr>.*?<\/tr>(\s*<tr>.*?<\/tr>)*)/gs,
                '<table class="table table-sm table-bordered estate-ai-table">$1</table>');
        }
        // Bold, italic, code
        html = html
            .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
            .replace(/\*(.*?)\*/g, "<em>$1</em>")
            .replace(/`(.*?)`/g, "<code>$1</code>")
            .replace(/\n/g, "<br/>");
        return html;
    }

    isConfirmationNeeded(text) {
        return text && text.includes("CONFIRMACIÓN REQUERIDA");
    }
}

EstateAIChat.template = "estate_ai_agent.AIChat";

registry.category("actions").add("estate_ai_chat", EstateAIChat);
