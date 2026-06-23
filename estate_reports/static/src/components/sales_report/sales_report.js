/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { DashChart } from "../dashboard_action/dashboard_action";

/**
 * Reporte "Promedio de Ventas" como CLIENT ACTION (mismo diseño que el dashboard:
 * lineal, plano, sin nube/X).
 */
class SalesReportAction extends Component {
    static template = "estate_reports.SalesReportAction";
    static components = { DashChart };
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            period: "quarter",
            operation: "sale",
            city: "",
            userId: false,
            k: {},
            chart: {},
            advisors: [],
            periods: [],
            operations: [],
        });
        onWillStart(() => this.load());
    }

    vals() {
        return {
            period: this.state.period,
            operation_type: this.state.operation,
            city: this.state.city || false,
            user_id: this.state.userId || false,
        };
    }

    async load() {
        this.state.loading = true;
        const res = await this.orm.call("estate.sales.report.wizard", "get_report_payload", [this.vals()]);
        this.state.k = res.kpis || {};
        this.state.chart = res.chart || {};
        this.state.advisors = res.advisors || [];
        this.state.periods = res.periods || [];
        this.state.operations = res.operations || [];
        this.state.loading = false;
    }

    money(v) {
        return "$" + Number(v || 0).toLocaleString("es-EC", { maximumFractionDigits: 2 });
    }
    num(v) {
        return Number(v || 0).toLocaleString("es-EC", { maximumFractionDigits: 2 });
    }
    pctClass(v) {
        const n = Number(v || 0);
        return n > 0 ? "text-success" : n < 0 ? "text-danger" : "text-muted";
    }

    onPeriod(ev) { this.state.period = ev.target.value; this.load(); }
    onOperation(ev) { this.state.operation = ev.target.value; this.load(); }
    onCity(ev) { this.state.city = ev.target.value; }
    onUser(ev) { this.state.userId = ev.target.value ? parseInt(ev.target.value, 10) : false; this.load(); }
    applyFilters() { this.load(); }

    async download(kind) {
        const action = await this.orm.call("estate.sales.report.wizard", "report_download", [this.vals(), kind]);
        if (action) {
            this.action.doAction(action);
        }
    }
}

registry.category("actions").add("estate_sales_report_owl", SalesReportAction);
