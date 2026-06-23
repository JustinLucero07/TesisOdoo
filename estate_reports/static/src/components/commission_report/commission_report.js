/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component, useState, onWillStart, markup } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * Liquidación de Comisiones como CLIENT ACTION OWL
 * Mismo diseño limpio que Dashboard General y Promedio de Ventas.
 */
class CommissionReportAction extends Component {
    static template = "estate_reports.CommissionReportAction";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            userId: false,
            dateFrom: "",
            dateTo: "",
            includeAll: false,
            k: {},
            tableHtml: "",
            advisors: [],
        });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        const res = await this.orm.call("estate.commission.wizard", "get_commission_payload", [
            {
                user_id: this.state.userId || false,
                date_from: this.state.dateFrom || false,
                date_to: this.state.dateTo || false,
                include_all: this.state.includeAll,
            },
        ]);
        this.state.k = res.kpis || {};
        this.state.tableHtml = res.table_html || "";
        this.state.advisors = res.advisors || [];
        if (!this.state.dateFrom && res.kpis) {
            this.state.dateFrom = res.kpis.date_from || "";
            this.state.dateTo = res.kpis.date_to || "";
        }
        this.state.loading = false;
    }

    raw(html) {
        return markup(html || "");
    }

    money(v) {
        return "$" + Number(v || 0).toLocaleString("es-EC", { maximumFractionDigits: 2 });
    }

    onUser(ev) { this.state.userId = ev.target.value ? parseInt(ev.target.value, 10) : false; this.load(); }
    onDateFrom(ev) { this.state.dateFrom = ev.target.value; this.load(); }
    onDateTo(ev) { this.state.dateTo = ev.target.value; this.load(); }
    onIncludeAll(ev) { this.state.includeAll = ev.target.checked; this.load(); }

    async downloadPdf() {
        const action = await this.orm.call("estate.commission.wizard", "owl_print_pdf", [
            {
                user_id: this.state.userId || false,
                date_from: this.state.dateFrom || false,
                date_to: this.state.dateTo || false,
                include_all: this.state.includeAll,
            },
        ]);
        if (action) {
            this.action.doAction(action);
        }
    }
}

registry.category("actions").add("estate_commission_report_owl", CommissionReportAction);
