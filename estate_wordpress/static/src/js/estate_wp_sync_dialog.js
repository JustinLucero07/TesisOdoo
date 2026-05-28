/** @odoo-module **/
import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);
        this.__wpDialogService = useService("dialog");
        this.__wpOrm = useService("orm");
    },

    async save(params) {
        const model = this.model?.config?.resModel;
        if (model !== "estate.property") {
            return super.save(params);
        }

        const record = this.model?.root;
        // Capture state BEFORE saving
        const wasPublished = record?.data?.wp_published;
        const resId = record?.resId;
        const isDirty = record?.isDirty;

        const result = await super.save(params);

        if (wasPublished && resId && isDirty) {
            await new Promise((resolve) => {
                this.__wpDialogService.add(ConfirmationDialog, {
                    title: "Actualizar en WordPress",
                    body: "Esta propiedad ya está publicada en el sitio web. ¿Deseas sincronizar los cambios ahora?",
                    confirmLabel: "Sí, sincronizar",
                    cancelLabel: "No, ahora no",
                    confirm: async () => {
                        try {
                            await this.__wpOrm.call(
                                "estate.property",
                                "action_publish_wordpress",
                                [[resId]]
                            );
                        } catch (_) {}
                        resolve();
                    },
                    cancel: () => resolve(),
                });
            });
        }

        return result;
    },
});
