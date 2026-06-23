/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * "Exportar Datos" como CLIENT ACTION (mismo diseño lineal/plano que el
 * dashboard, sin la nube de guardar ni la X).
 */
class ReportExportAction extends Component {
    static template = "estate_reports.ReportExportAction";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            reportType: "available_properties",
            dateFrom: "",
            dateTo: "",
            reportTypes: [],
            downloading: false,
        });
        onWillStart(() => this.load());
    }

    async load() {
        const res = await this.orm.call("estate.report.wizard", "report_options", []);
        this.state.reportTypes = res.report_types || [];
        this.state.loading = false;
    }

    vals() {
        return {
            report_type: this.state.reportType,
            date_from: this.state.dateFrom || false,
            date_to: this.state.dateTo || false,
        };
    }

    onType(value) { this.state.reportType = value; }
    onFrom(ev) { this.state.dateFrom = ev.target.value; }
    onTo(ev) { this.state.dateTo = ev.target.value; }

    async download(fmt) {
        if (this.state.downloading) {
            return;
        }
        this.state.downloading = true;
        try {
            const action = await this.orm.call(
                "estate.report.wizard", "report_download", [this.vals(), fmt]
            );
            if (action) {
                this.action.doAction(action);
            }
        } finally {
            this.state.downloading = false;
        }
    }
}

registry.category("actions").add("estate_report_export_owl", ReportExportAction);
