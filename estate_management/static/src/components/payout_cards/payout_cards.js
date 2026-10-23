/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { deserializeDate, serializeDate } from "@web/core/l10n/dates";
import { formatMonetary } from "@web/views/fields/formatters";
import { x2ManyField } from "@web/views/fields/x2many/x2many_field";

/**
 * Asesores a pagar: un recuadro por asesor con su forma de pago, fecha,
 * referencia y factura. Si un solo asesor hizo todo, sale un solo recuadro.
 */
export class PayoutCardsField extends Component {
    static template = "estate_management.PayoutCardsField";
    static props = ["*"];

    get records() {
        return this.props.record.data[this.props.name].records;
    }

    get readonly() {
        return this.props.readonly;
    }

    options(rec, fieldName) {
        return rec.fields[fieldName].selection || [];
    }

    money(rec, value) {
        const currency = rec.data.company_currency;
        const currencyId = Array.isArray(currency) ? currency[0] : currency?.id;
        return formatMonetary(value || 0, { currencyId });
    }

    dateValue(rec) {
        return rec.data.payment_date ? serializeDate(rec.data.payment_date) : "";
    }

    userName(rec) {
        const user = rec.data.user_id;
        return (Array.isArray(user) ? user[1] : user?.display_name) || "";
    }

    userId(rec) {
        const user = rec.data.user_id;
        return Array.isArray(user) ? user[0] : user?.id;
    }

    async set(rec, fieldName, value) {
        await rec.update({ [fieldName]: value });
    }

    onDate(rec, ev) {
        this.set(rec, "payment_date", ev.target.value ? deserializeDate(ev.target.value) : false);
    }
}

export const payoutCardsField = {
    ...x2ManyField,
    component: PayoutCardsField,
    supportedTypes: ["one2many"],
};

registry.category("fields").add("estate_payout_cards", payoutCardsField);
