/** @odoo-module **/

import { Component, useState, onMounted, onWillUpdateProps, xml } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * Previsualización del PDF de un documento, inyectada en la barra lateral
 * (chatter), igual que el panel "Análisis IA" de las propiedades.
 */
export class DocumentPdfPreview extends Component {
    static template = xml`
        <div t-if="state.hasFile" class="o-estate-DocPreview border-bottom" style="background:#f8faff;">
            <!-- Header -->
            <div class="d-flex align-items-center justify-content-between px-3 pt-2 pb-1">
                <div class="d-flex align-items-center gap-2 text-truncate">
                    <i class="fa fa-file-pdf-o text-danger" style="font-size:1rem;"/>
                    <strong class="small" style="color:#C8102E;">Previsualización</strong>
                    <span class="text-muted text-truncate" style="font-size:0.7rem;" t-esc="state.filename"/>
                </div>
                <a class="btn btn-link btn-sm p-0 px-1 text-muted" t-att-href="state.url"
                   target="_blank" title="Abrir en pestaña nueva">
                    <i class="fa fa-external-link fa-fw"/>
                </a>
            </div>
            <!-- Visor -->
            <div class="px-2 pb-2">
                <t t-if="state.isPdf">
                    <iframe t-att-src="state.url + '#toolbar=1&amp;navpanes=0'"
                            style="width:100%;height:72vh;border:1px solid #d8e3f0;border-radius:8px;background:#fff;"/>
                </t>
                <t t-else="">
                    <div class="text-center text-muted py-4 border rounded" style="background:#fff;">
                        <i class="fa fa-file-o fa-2x mb-2 d-block"/>
                        <small>Este archivo no es PDF.<br/>
                            <a t-att-href="state.url" target="_blank">Descargar / abrir</a>
                        </small>
                    </div>
                </t>
            </div>
        </div>
    `;
    static props = { recordId: Number };

    setup() {
        this.orm = useService("orm");
        this.state = useState({ hasFile: false, isPdf: false, filename: "", url: "" });
        onMounted(() => this.load(this.props.recordId));
        onWillUpdateProps((next) => this.load(next.recordId));
    }

    async load(id) {
        if (!id) { this.state.hasFile = false; return; }
        try {
            // Solo metadatos (no el binario) para no cargar el PDF dos veces.
            const [rec] = await this.orm.read("estate.document", [id], ["filename", "file_size"]);
            const fn = (rec && rec.filename) || "";
            this.state.hasFile = !!(rec && (rec.file_size > 0 || fn));
            this.state.filename = fn;
            this.state.isPdf = fn.toLowerCase().endsWith(".pdf");
            this.state.url = `/web/content/estate.document/${id}/file?download=false`;
        } catch (_) {
            this.state.hasFile = false;
        }
    }
}
