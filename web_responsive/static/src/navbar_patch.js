/** @odoo-module **/

import { NavBar } from "@web/webclient/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { useExternalListener } from "@odoo/owl";

patch(NavBar.prototype, {
    setup() {
        super.setup();
        Object.assign(this.state, {
            appDrawerOpen: false,
            appSearch: "",
        });

        useExternalListener(window, "keydown", (ev) => {
            if (ev.key === "Escape" && this.state.appDrawerOpen) {
                this.closeAppDrawer();
            }
        });
    },

    toggleAppDrawer() {
        this.state.appDrawerOpen = !this.state.appDrawerOpen;
        if (this.state.appDrawerOpen) {
            this.state.appSearch = "";
            requestAnimationFrame(() => {
                document.querySelector(".o-wr-AppDrawer-search input")?.focus();
            });
        }
    },

    closeAppDrawer() {
        this.state.appDrawerOpen = false;
        this.state.appSearch = "";
    },

    get appDrawerApps() {
        const all = this.menuService.getApps();
        const q = (this.state.appSearch || "").toLowerCase().trim();
        if (!q) return all;
        return all.filter((a) => (a.name || "").toLowerCase().includes(q));
    },

    onAppSelected(app) {
        if (app) {
            this.menuService.selectMenu(app);
        }
        this.closeAppDrawer();
    },

    getAppIconSrc(app) {
        const raw = app.webIconData;
        if (!raw) return "";
        if (raw.startsWith("data:image") || raw.startsWith("/")) return raw;
        const prefix = raw.charAt(0) === "P"
            ? "data:image/svg+xml;base64,"
            : "data:image/png;base64,";
        return prefix + raw.replace(/\s/g, "");
    },
});
