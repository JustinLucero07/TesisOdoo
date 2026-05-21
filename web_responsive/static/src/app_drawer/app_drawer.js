/** @odoo-module **/

import { Component, useState, useRef, onMounted, xml } from "@odoo/owl";
import { useExternalListener } from "@web/core/utils/hooks";

export class AppDrawer extends Component {
    static template = xml`
        <t t-portal="'body'">
            <!-- Backdrop -->
            <div class="o-wr-AppDrawer-backdrop"
                 t-on-click="close"/>

            <!-- Drawer panel -->
            <div class="o-wr-AppDrawer" t-ref="drawer">
                <!-- Header -->
                <div class="o-wr-AppDrawer-header">
                    <div class="o-wr-AppDrawer-logo">
                        <i class="oi oi-apps"/>
                        <span>Aplicaciones</span>
                    </div>
                    <!-- Search -->
                    <div class="o-wr-AppDrawer-search">
                        <i class="fa fa-search"/>
                        <input type="text"
                               placeholder="Buscar aplicación..."
                               t-ref="searchInput"
                               t-model="state.search"
                               autocomplete="off"
                               spellcheck="false"/>
                        <button t-if="state.search" class="o-wr-AppDrawer-clearSearch"
                                t-on-click="clearSearch"
                                title="Limpiar">
                            <i class="fa fa-times"/>
                        </button>
                    </div>
                    <button class="o-wr-AppDrawer-close" t-on-click="close" title="Cerrar (Esc)">
                        <i class="fa fa-times"/>
                    </button>
                </div>

                <!-- App Grid -->
                <div class="o-wr-AppDrawer-grid">
                    <t t-if="filteredApps.length">
                        <a t-foreach="filteredApps"
                           t-as="app"
                           t-key="app.id"
                           class="o-wr-AppCard"
                           t-att-class="{ 'o-wr-AppCard--active': props.currentApp and props.currentApp.id === app.id }"
                           t-att-href="props.getHref(app)"
                           t-on-click.prevent="() => selectApp(app)"
                           t-att-title="app.name">
                            <!-- Icon: image -->
                            <div class="o-wr-AppCard-icon" t-if="app.webIconData"
                                 t-attf-style="background-image:url({{ app.webIconData }});background-size:cover;background-position:center;">
                            </div>
                            <!-- Icon: fa class + color -->
                            <div class="o-wr-AppCard-icon o-wr-AppCard-icon--fa"
                                 t-elif="app.webIcon and app.webIcon.iconClass"
                                 t-attf-style="background-color:{{ app.webIcon.backgroundColor or '#875a7b' }}">
                                <i t-att-class="app.webIcon.iconClass"
                                   t-attf-style="color:{{ app.webIcon.color or '#fff' }}"/>
                            </div>
                            <!-- Icon: fallback -->
                            <div class="o-wr-AppCard-icon o-wr-AppCard-icon--fallback" t-else="">
                                <span t-esc="app.name ? app.name[0].toUpperCase() : '?'"/>
                            </div>
                            <span class="o-wr-AppCard-name" t-esc="app.name"/>
                        </a>
                    </t>
                    <div t-else="" class="o-wr-AppDrawer-noResults">
                        <i class="fa fa-search-minus"/>
                        <p>Sin resultados para "<strong t-esc="state.search"/>"</p>
                    </div>
                </div>
            </div>
        </t>
    `;

    static props = {
        apps: Array,
        currentApp: { optional: true },
        getHref: Function,
        onClose: Function,
        onSelected: Function,
    };

    setup() {
        this.state = useState({ search: "" });
        this.searchInput = useRef("searchInput");

        // Close on Escape
        useExternalListener(window, "keydown", (ev) => {
            if (ev.key === "Escape") this.close();
        });

        // Focus search input when drawer opens
        onMounted(() => {
            this.searchInput.el?.focus();
        });
    }

    get filteredApps() {
        const q = this.state.search.toLowerCase().trim();
        if (!q) return this.props.apps;
        return this.props.apps.filter((a) => a.name.toLowerCase().includes(q));
    }

    clearSearch() {
        this.state.search = "";
        this.searchInput.el?.focus();
    }

    close() {
        this.props.onClose();
    }

    selectApp(app) {
        this.props.onSelected(app);
        this.close();
    }
}
