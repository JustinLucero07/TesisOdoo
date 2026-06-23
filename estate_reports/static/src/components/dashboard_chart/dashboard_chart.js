/** @odoo-module **/
import { Component, useRef, onMounted, onWillUnmount, useEffect } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { loadJS } from "@web/core/assets";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/**
 * A2: widget de gráfico Chart.js para el dashboard.
 * Lee un campo Char con JSON {type, labels, values, color/colors, horizontal}
 * y renderiza un canvas con Chart.js (incluido en Odoo).
 */
class DashboardChart extends Component {
    static template = "estate_reports.DashboardChart";
    static props = { ...standardFieldProps };

    setup() {
        this.canvasRef = useRef("canvas");
        this._chart = null;

        onMounted(() => this._renderChart());
        // Re-renderiza cuando cambia el valor (al aplicar filtros)
        useEffect(
            () => {
                this._renderChart();
            },
            () => [this.props.record.data[this.props.name]]
        );
        onWillUnmount(() => this._destroy());
    }

    get data() {
        const raw = this.props.record.data[this.props.name];
        if (!raw) return null;
        try {
            return typeof raw === "string" ? JSON.parse(raw) : raw;
        } catch (_) {
            return null;
        }
    }

    _destroy() {
        if (this._chart) {
            this._chart.destroy();
            this._chart = null;
        }
    }

    async _renderChart() {
        const data = this.data;
        const canvas = this.canvasRef.el;
        if (!canvas) return;
        await loadJS("/web/static/lib/Chart/Chart.js");
        this._destroy();

        if (!data || !data.values || !data.values.length) {
            return; // el template muestra el placeholder
        }

        const horizontal = !!data.horizontal;
        const bg = data.colors
            ? data.colors
            : (data.color || "#004274");

        // eslint-disable-next-line no-undef
        this._chart = new Chart(canvas.getContext("2d"), {
            type: "bar",
            data: {
                labels: data.labels,
                datasets: [{
                    label: data.label || "",
                    data: data.values,
                    backgroundColor: bg,
                    borderRadius: 0,
                    maxBarThickness: 46,
                }],
            },
            options: {
                indexAxis: horizontal ? "y" : "x",
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => {
                                let txt = ` ${ctx.parsed[horizontal ? "x" : "y"]}`;
                                if (data.revenues && data.revenues[ctx.dataIndex] != null) {
                                    const rev = data.revenues[ctx.dataIndex];
                                    txt += `  ·  $${rev.toLocaleString("es-EC")}`;
                                }
                                return txt;
                            },
                        },
                    },
                },
                scales: {
                    x: { grid: { display: !horizontal }, ticks: { precision: 0 } },
                    y: { grid: { display: horizontal }, ticks: { precision: 0 }, beginAtZero: true },
                },
            },
        });
    }
}

export const dashboardChart = {
    component: DashboardChart,
    supportedTypes: ["char", "text"],
};
registry.category("fields").add("dashboard_chart", dashboardChart);
