/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component, useState, useRef, onWillStart, onMounted, onWillUnmount, useEffect, markup } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";

/**
 * Gráfico Chart.js nativo (mismas animaciones/estilo que Odoo).
 * Recibe los datos como prop: { labels, values, label, color, horizontal }.
 */
export class DashChart extends Component {
    static template = "estate_reports.DashChart";
    static props = { data: { type: Object, optional: true } };

    setup() {
        this.canvasRef = useRef("canvas");
        this._chart = null;
        onMounted(() => this._render());
        useEffect(
            () => { this._render(); },
            () => [this.props.data]
        );
        onWillUnmount(() => this._destroy());
    }

    _destroy() {
        if (this._chart) {
            this._chart.destroy();
            this._chart = null;
        }
    }

    get hasData() {
        const d = this.props.data;
        return d && d.values && d.values.length;
    }

    async _render() {
        const canvas = this.canvasRef.el;
        if (!canvas) return;
        await loadJS("/web/static/lib/Chart/Chart.js");
        this._destroy();
        const d = this.props.data;
        if (!d || !d.values || !d.values.length) return;
        // eslint-disable-next-line no-undef
        this._chart = new Chart(canvas.getContext("2d"), {
            type: "bar",
            data: {
                labels: d.labels,
                datasets: [{
                    label: d.label || "",
                    data: d.values,
                    backgroundColor: d.color || "#004274",
                    borderRadius: 0,
                    maxBarThickness: 42,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 700 },
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: "#f1f5f9" } },
                    x: { grid: { display: false } },
                },
            },
        });
    }
}

class EstateDashboardAction extends Component {
    static template = "estate_reports.DashboardAction";
    static components = { DashChart };
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            userId: false,
            period: "month",
            k: {},
            salesChart: {},
            leadsChart: {},
            ranking: [],
            advisors: [],
            periods: [],
            aiQuery: "",
            aiResponse: "",
            aiLoading: false,
        });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        const res = await this.orm.call("estate.dashboard", "get_dashboard_data", [
            this.state.userId,
            this.state.period,
        ]);
        this.state.k = res.kpis || {};
        this.state.salesChart = res.salesChart || {};
        this.state.leadsChart = res.leadsChart || {};
        this.state.ranking = res.ranking || [];
        this.state.advisors = res.advisors || [];
        this.state.periods = res.periods || [];
        this.state.loading = false;
    }

    raw(html) {
        return markup(html || "");
    }

    money(v) {
        const n = Number(v || 0);
        return "$" + n.toLocaleString("es-EC", { maximumFractionDigits: 0 });
    }

    num(v) {
        return (Number(v || 0)).toLocaleString("es-EC", { maximumFractionDigits: 2 });
    }

    pctClass(v) {
        const n = Number(v || 0);
        return n > 0 ? "text-success" : n < 0 ? "text-danger" : "text-muted";
    }

    pctArrow(v) {
        const n = Number(v || 0);
        return n > 0 ? "▲" : n < 0 ? "▼" : "—";
    }

    onUser(ev) {
        this.state.userId = ev.target.value ? parseInt(ev.target.value, 10) : false;
        this.load();
    }

    onPeriod(ev) {
        this.state.period = ev.target.value;
        this.load();
    }

    refresh() {
        this.load();
    }

    openList(model, name, domain) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: name,
            res_model: model,
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: domain || [],
        });
    }

    async askAi() {
        const q = (this.state.aiQuery || "").trim();
        if (!q) return;
        this.state.aiLoading = true;
        this.state.aiResponse = "";
        try {
            const html = await this.orm.call("estate.dashboard", "dashboard_ask_ai", [
                q, this.state.userId, this.state.period,
            ]);
            this.state.aiResponse = html || "";
        } finally {
            this.state.aiLoading = false;
        }
    }
}

registry.category("actions").add("estate_dashboard_owl", EstateDashboardAction);
