import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

// Ctrl+K: además de los comandos de Odoo, busca propiedades, oportunidades y
// contactos por nombre, referencia, teléfono o correo y los abre con Enter.
const categories = registry.category("command_categories");
categories.add("estate_props", { namespace: "default", name: _t("Propiedades") }, { sequence: 5 });
categories.add("estate_leads", { namespace: "default", name: _t("Oportunidades") }, { sequence: 6 });
categories.add("estate_contacts", { namespace: "default", name: _t("Contactos") }, { sequence: 7 });

registry.category("command_provider").add("estate_quick_search", {
    namespace: "default",
    async provide(env, options) {
        const term = (options.searchValue || "").trim();
        if (term.length < 2) {
            return [];
        }
        const rows = await env.services.orm.call("estate.my.day", "global_search", [term]);
        return rows.map((r) => ({
            category: r.category,
            name: r.sub ? `${r.name}  —  ${r.sub}` : r.name,
            action() {
                env.services.action.doAction({
                    type: "ir.actions.act_window",
                    res_model: r.model,
                    res_id: r.id,
                    views: [[false, "form"]],
                });
            },
        }));
    },
});
