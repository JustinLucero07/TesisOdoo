import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/** "Mi día": citas, recordatorios, leads calientes y pendientes del asesor. */
export class EstateMyDay extends Component {
    static template = "estate_calendar.MyDay";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ loading: true, data: {} });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        this.state.data = await this.orm.call("estate.my.day", "get_data", []);
        this.state.loading = false;
    }

    money(v) {
        return "$" + Number(v || 0).toLocaleString("es-EC", { maximumFractionDigits: 0 });
    }

    openRecord(model, id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: model,
            res_id: id,
            views: [[false, "form"]],
        });
    }

    newRecord(model, context = {}) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: model,
            views: [[false, "form"]],
            target: "current",
            context,
        });
    }

    openXml(xmlid) {
        this.action.doAction(xmlid);
    }

    stateLabel(state) {
        return { scheduled: "Programada", done: "Realizada", cancelled: "Cancelada" }[state] || "";
    }

    reminderWhen(r) {
        if (r.days_left < 0) return `Venció hace ${-r.days_left} d`;
        if (r.days_left === 0) return "Hoy";
        if (r.days_left === 1) return "Mañana";
        return `En ${r.days_left} días`;
    }
}

registry.category("actions").add("estate_my_day", EstateMyDay);
