/** @odoo-module **/

import { Component, onMounted, onWillStart, useRef, useState, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { loadJS } from "@web/core/assets";

const FB_BLUE = "#1877F2";
const FB_BLUE_LIGHT = "#42A5F5";
const FB_BLUE_DARK = "#0B5394";
const COLORS = {
    likes: "#1877F2",
    loves: "#E4405F",
    hahas: "#F7B928",
    wows: "#F7B928",
    sads: "#F7B928",
    angries: "#E94235",
};

export class FacebookInsightsDashboard extends Component {
    static template = "estate_social.FacebookInsightsDashboard";
    static props = { ...standardFieldProps };

    setup() {
        this.lineChartRef = useRef("lineChart");
        this.audienceChartRef = useRef("audienceChart");
        this.trafficChartRef = useRef("trafficChart");
        this.demoChartRef = useRef("demoChart");
        this.charts = [];

        this.state = useState({ data: this._parseData() });

        onWillStart(async () => {
            await loadJS("/web/static/lib/Chart/Chart.js");
        });

        onMounted(() => this._renderAllCharts());
        onWillUnmount(() => this._destroyCharts());
    }

    _parseData() {
        const raw = this.props.record.data[this.props.name];
        if (!raw) {
            return { summary: {}, reactions_by_type: {}, audience: {}, traffic_source: {}, demographics: {}, evolution: [] };
        }
        try {
            return JSON.parse(raw);
        } catch (e) {
            return { summary: {}, reactions_by_type: {}, audience: {}, traffic_source: {}, demographics: {}, evolution: [] };
        }
    }

    _destroyCharts() {
        this.charts.forEach((c) => c && c.destroy && c.destroy());
        this.charts = [];
    }

    _renderAllCharts() {
        this._destroyCharts();
        const Chart = window.Chart;
        if (!Chart) return;

        // Línea: evolución en el tiempo
        if (this.lineChartRef.el) {
            const ev = this.state.data.evolution || [];
            const labels = ev.map(p => p.date);
            this.charts.push(new Chart(this.lineChartRef.el, {
                type: "line",
                data: {
                    labels,
                    datasets: [
                        {
                            label: "Visualizaciones",
                            data: ev.map(p => p.impressions),
                            borderColor: FB_BLUE,
                            backgroundColor: "rgba(24,119,242,0.10)",
                            tension: 0.35,
                            fill: true,
                            pointRadius: 3,
                        },
                        {
                            label: "Espectadores",
                            data: ev.map(p => p.reach),
                            borderColor: "#999",
                            backgroundColor: "rgba(0,0,0,0)",
                            borderDash: [6, 4],
                            tension: 0.35,
                            pointRadius: 2,
                        },
                    ],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { position: "top", align: "start" } },
                    scales: {
                        y: { beginAtZero: true, ticks: { precision: 0 } },
                    },
                },
            }));
        }

        // Pie: seguidores vs no seguidores
        if (this.audienceChartRef.el) {
            const a = this.state.data.audience || {};
            const fan = a.fan || 0;
            const nonFan = a.non_fan || 0;
            const total = fan + nonFan;
            this.charts.push(new Chart(this.audienceChartRef.el, {
                type: "doughnut",
                data: {
                    labels: ["Seguidores", "No seguidores"],
                    datasets: [{
                        data: total ? [fan, nonFan] : [0, 1],
                        backgroundColor: [FB_BLUE_DARK, FB_BLUE_LIGHT],
                        borderWidth: 0,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: "55%",
                    plugins: {
                        legend: { position: "bottom" },
                        tooltip: {
                            callbacks: {
                                label: (ctx) => {
                                    if (!total) return `${ctx.label}: sin datos`;
                                    const pct = (ctx.parsed / total * 100).toFixed(1);
                                    return `${ctx.label}: ${ctx.parsed} (${pct}%)`;
                                },
                            },
                        },
                    },
                },
            }));
        }

        // Pie: tráfico (orgánico/pagado/viral)
        if (this.trafficChartRef.el) {
            const t = this.state.data.traffic_source || {};
            const total = (t.organic || 0) + (t.paid || 0) + (t.viral || 0);
            this.charts.push(new Chart(this.trafficChartRef.el, {
                type: "doughnut",
                data: {
                    labels: ["Orgánico", "Pagado", "Viral"],
                    datasets: [{
                        data: total ? [t.organic || 0, t.paid || 0, t.viral || 0] : [0, 0, 1],
                        backgroundColor: [FB_BLUE, "#E4405F", "#42B72A"],
                        borderWidth: 0,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: "55%",
                    plugins: {
                        legend: { position: "bottom" },
                        tooltip: {
                            callbacks: {
                                label: (ctx) => {
                                    if (!total) return `${ctx.label}: sin datos`;
                                    const pct = (ctx.parsed / total * 100).toFixed(1);
                                    return `${ctx.label}: ${ctx.parsed} (${pct}%)`;
                                },
                            },
                        },
                    },
                },
            }));
        }

        // Barras horizontales apiladas: demografía edad/sexo
        if (this.demoChartRef.el) {
            const demo = this.state.data.demographics || {};
            const ageOrder = ["65+", "55-64", "45-54", "35-44", "25-34", "18-24"];
            const labels = ageOrder;
            const males = ageOrder.map(a => -(demo[a]?.M || 0));
            const females = ageOrder.map(a => (demo[a]?.F || 0));

            this.charts.push(new Chart(this.demoChartRef.el, {
                type: "bar",
                data: {
                    labels,
                    datasets: [
                        { label: "Hombres", data: males,   backgroundColor: FB_BLUE,       borderWidth: 0 },
                        { label: "Mujeres", data: females, backgroundColor: FB_BLUE_LIGHT, borderWidth: 0 },
                    ],
                },
                options: {
                    indexAxis: "y",
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: "top" },
                        tooltip: {
                            callbacks: {
                                label: (ctx) => `${ctx.dataset.label}: ${Math.abs(ctx.parsed.x)}`,
                            },
                        },
                    },
                    scales: {
                        x: {
                            stacked: false,
                            ticks: { callback: (v) => Math.abs(v) },
                        },
                        y: { stacked: true },
                    },
                },
            }));
        }
    }

    formatNumber(n) {
        if (n === null || n === undefined) return "0";
        if (n >= 1000000) return (n / 1000000).toFixed(1) + "M";
        if (n >= 1000) return (n / 1000).toFixed(1) + "K";
        return String(n);
    }

    get hasAudience() {
        const a = this.state.data.audience || {};
        return (a.fan || 0) + (a.non_fan || 0) > 0;
    }

    get hasTraffic() {
        const t = this.state.data.traffic_source || {};
        return (t.organic || 0) + (t.paid || 0) + (t.viral || 0) > 0;
    }

    get hasDemographics() {
        const d = this.state.data.demographics || {};
        return Object.values(d).some(v => (v.M || 0) + (v.F || 0) + (v.U || 0) > 0);
    }

    get hasEvolution() {
        return (this.state.data.evolution || []).length > 0;
    }
}

export const fbInsightsDashboardField = {
    component: FacebookInsightsDashboard,
    supportedTypes: ["char", "text"],
};

registry.category("fields").add("fb_insights_dashboard", fbInsightsDashboardField);
