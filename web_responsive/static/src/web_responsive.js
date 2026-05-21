/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onMounted, xml } from "@odoo/owl";

const STORAGE_KEY = "web_responsive.sidebar_collapsed";

class SidebarToggle extends Component {
    static template = xml`
        <div class="o_responsive_sidebar_toggle o_nav_entry d-none d-lg-flex"
             title="Colapsar/Expandir menú lateral"
             t-on-click="toggle">
            <i t-if="state.collapsed" class="fa fa-chevron-right fa-fw"/>
            <i t-else="" class="fa fa-chevron-left fa-fw"/>
        </div>
    `;
    static props = {};

    setup() {
        this.state = useState({
            collapsed: localStorage.getItem(STORAGE_KEY) === "1",
        });
        onMounted(() => this._apply());
    }

    toggle() {
        this.state.collapsed = !this.state.collapsed;
        localStorage.setItem(STORAGE_KEY, this.state.collapsed ? "1" : "0");
        this._apply();
    }

    _apply() {
        document.body.classList.toggle("o_responsive_sidebar_collapsed", this.state.collapsed);
    }
}

// Sequence 2: renders right after burger_menu (seq 0) and user_menu (seq 0)
registry.category("systray").add(
    "web_responsive.sidebar_toggle",
    { Component: SidebarToggle },
    { sequence: 2 }
);
