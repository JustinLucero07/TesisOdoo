/** @odoo-module **/
import { registry } from "@web/core/registry";

// Client action: opens the AI float chat panel
registry.category("actions").add("estate_ai_open_chat", () => {
    setTimeout(() => {
        const btn = document.querySelector(".ai-float-btn");
        if (btn) btn.click();
    }, 150);
});
