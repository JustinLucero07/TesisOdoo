/** @odoo-module **/
import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { onMounted } from "@odoo/owl";

patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);
        this.__orm = useService("orm");
        onMounted(() => this._autoGeocodeOnLoad());
    },

    async _autoGeocodeOnLoad() {
        // Only for estate.property forms
        if (this.model?.config?.resModel !== "estate.property") return;

        const record = this.model?.root;
        if (!record?.resId) return;               // new unsaved record
        if (record.data?.latitude || record.data?.longitude) return;  // coords exist
        if (!record.data?.street && !record.data?.city) return;       // no address

        try {
            const geocoded = await this.__orm.call(
                "estate.property",
                "geocode_if_missing",
                [[record.resId]]
            );
            if (geocoded) {
                await record.load();
            }
        } catch {
            // Silent — geocoding optional
        }
    },
});
