import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";

const STORAGE_KEY = "ix_color_scheme";

function isDark() {
    return document.documentElement.classList.contains("ix-dark");
}

/** Botón 🌙/☀️ en la barra superior: cambia entre modo claro y oscuro. */
export class DarkModeToggle extends Component {
    static template = "estate_theme.DarkModeToggle";
    static props = {};

    setup() {
        this.state = useState({ dark: isDark() });
    }

    toggle() {
        const dark = !isDark();
        document.documentElement.classList.toggle("ix-dark", dark);
        try {
            window.localStorage.setItem(STORAGE_KEY, dark ? "dark" : "light");
        } catch {
            // Sin almacenamiento (modo privado): el cambio dura esta sesión.
        }
        this.state.dark = dark;
    }
}

registry.category("systray").add("estate_theme.dark_mode", { Component: DarkModeToggle }, { sequence: 1 });
