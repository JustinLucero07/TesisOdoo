/** @odoo-module **/

import { Component, useState, onMounted, onWillUpdateProps, xml } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * Previsualización del PDF de un contrato en la barra lateral (chatter),
 * igual que el panel de documentos/propiedades.
 * Busca, en orden: Contrato Firmado → Contrato de Arras → primer documento
 * PDF vinculado al contrato.
 */
export class ContractPdfPreview extends Component {
    static template = xml`
        <div t-if="state.hasFile" class="o-estate-DocPreview border-bottom" style="background:#f8faff;">
            <div class="d-flex align-items-center justify-content-between px-3 pt-2 pb-1">
                <div class="d-flex align-items-center gap-2 text-truncate">
                    <i class="fa fa-file-pdf-o text-danger" style="font-size:1rem;"/>
                    <strong class="small" style="color:#C8102E;" t-esc="state.label"/>
                    <span class="text-muted text-truncate" style="font-size:0.7rem;" t-esc="state.filename"/>
                </div>
                <a class="btn btn-link btn-sm p-0 px-1 text-muted" t-att-href="state.url"
                   target="_blank" title="Abrir en pestaña nueva">
                    <i class="fa fa-external-link fa-fw"/>
                </a>
            </div>
            <div class="px-2 pb-2">
                <iframe t-att-src="state.url + '#toolbar=1&amp;navpanes=0'"
                        style="width:100%;height:72vh;border:1px solid #d8e3f0;border-radius:8px;background:#fff;"/>
            </div>
        </div>
    `;
    static props = { recordId: Number };

    setup() {
        this.orm = useService("orm");
        this.state = useState({ hasFile: false, label: "", filename: "", url: "" });
        onMounted(() => this.load(this.props.recordId));
        onWillUpdateProps((next) => this.load(next.recordId));
    }

    _isPdf(fn) {
        return !!(fn && fn.toLowerCase().endsWith(".pdf"));
    }

    async load(id) {
        if (!id) { this.state.hasFile = false; return; }
        try {
            const [c] = await this.orm.read("estate.contract", [id],
                ["signed_contract_filename", "earnest_money_filename"]);
            // 1. Contrato firmado
            if (c && this._isPdf(c.signed_contract_filename)) {
                return this._set("Contrato Firmado", c.signed_contract_filename,
                    `/web/content/estate.contract/${id}/signed_contract?download=false`);
            }
            // 2. Contrato de arras
            if (c && this._isPdf(c.earnest_money_filename)) {
                return this._set("Contrato de Arras", c.earnest_money_filename,
                    `/web/content/estate.contract/${id}/earnest_money_contract?download=false`);
            }
            // 3. Primer documento PDF vinculado al contrato
            const docs = await this.orm.searchRead("estate.document",
                [["contract_id", "=", id]], ["filename"], { limit: 20 });
            const pdf = docs.find((d) => this._isPdf(d.filename));
            if (pdf) {
                return this._set(pdf.filename, pdf.filename,
                    `/web/content/estate.document/${pdf.id}/file?download=false`);
            }
            this.state.hasFile = false;
        } catch (_) {
            this.state.hasFile = false;
        }
    }

    _set(label, filename, url) {
        this.state.label = label;
        this.state.filename = filename === label ? "" : filename;
        this.state.url = url;
        this.state.hasFile = true;
    }
}
