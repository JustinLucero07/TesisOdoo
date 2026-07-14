/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, useRef, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { loadJS, loadCSS } from "@web/core/assets";

// Estado de la propiedad -> etiqueta y color del pin en el mapa.
const STATES = {
    available: { label: "Disponible", color: "#28a745" },
    reserved: { label: "Reservada", color: "#fd7e14" },
    sold: { label: "Vendida", color: "#dc3545" },
    rented: { label: "Alquilada", color: "#1877F2" },
    draft: { label: "Borrador", color: "#6c757d" },
};

// Centro por defecto si no hay ninguna propiedad geolocalizada (Cuenca, Ecuador).
const DEFAULT_CENTER = [-2.9006, -79.0045];
const DEFAULT_ZOOM = 12;

function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value == null ? "" : String(value);
    return div.innerHTML;
}

export class PropertyMap extends Component {
    static template = "estate_management.PropertyMap";
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.mapRef = useRef("map");

        this.state = useState({
            properties: [],
            // Por defecto se ocultan los borradores (aún no están en el mercado).
            visible: { available: true, reserved: true, sold: true, rented: true, draft: false },
            loading: true,
            noCoords: 0,
        });

        this._map = null;
        this._markers = [];

        onWillStart(async () => {
            await loadCSS("/estate_management/static/lib/leaflet/leaflet.css");
            await loadJS("/estate_management/static/lib/leaflet/leaflet.js");
            await this._loadProperties();
        });
        onMounted(() => this._initMap());
        onWillUnmount(() => {
            if (this._map) {
                this._map.remove();
                this._map = null;
            }
        });
    }

    async _loadProperties() {
        const fields = [
            "name", "title", "latitude", "longitude", "price", "state",
            "city", "street", "property_type_id", "user_id",
        ];
        const all = await this.orm.searchRead("estate.property", [], fields, { limit: 2000 });
        this.state.properties = all.filter((p) => p.latitude && p.longitude);
        this.state.noCoords = all.length - this.state.properties.length;
        this.state.loading = false;
    }

    get visibleProperties() {
        return this.state.properties.filter((p) => this.state.visible[p.state]);
    }

    get legend() {
        return Object.entries(STATES).map(([key, info]) => ({
            key,
            label: info.label,
            color: info.color,
            count: this.state.properties.filter((p) => p.state === key).length,
            active: this.state.visible[key],
        }));
    }

    toggleState(key) {
        this.state.visible[key] = !this.state.visible[key];
        this._renderMarkers();
    }

    _initMap() {
        const L = window.L;
        if (!L || !this.mapRef.el) {
            return;
        }
        this._map = L.map(this.mapRef.el).setView(DEFAULT_CENTER, DEFAULT_ZOOM);
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
            maxZoom: 19,
        }).addTo(this._map);

        // El botón "Abrir ficha" vive dentro del popup, que Leaflet crea al vuelo.
        this._map.on("popupopen", (ev) => {
            const btn = ev.popup.getElement().querySelector(".o_estate_map_open");
            if (btn) {
                btn.addEventListener("click", () => this._openProperty(parseInt(btn.dataset.id, 10)));
            }
        });

        this._renderMarkers();
    }

    _renderMarkers() {
        const L = window.L;
        if (!this._map || !L) {
            return;
        }
        this._markers.forEach((m) => this._map.removeLayer(m));
        this._markers = [];

        const props = this.visibleProperties;
        props.forEach((p) => {
            const info = STATES[p.state] || STATES.draft;
            const icon = L.divIcon({
                className: "o_estate_map_pin_wrapper",
                html: `<span class="o_estate_map_pin" style="background:${info.color}"></span>`,
                iconSize: [18, 18],
                iconAnchor: [9, 9],
                popupAnchor: [0, -10],
            });
            const marker = L.marker([p.latitude, p.longitude], { icon }).addTo(this._map);
            marker.bindPopup(this._popupHtml(p, info));
            this._markers.push(marker);
        });

        if (props.length) {
            const bounds = L.latLngBounds(props.map((p) => [p.latitude, p.longitude]));
            this._map.fitBounds(bounds, { padding: [40, 40], maxZoom: 16 });
        }
    }

    _popupHtml(p, info) {
        const price = p.price
            ? new Intl.NumberFormat("es-EC", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(p.price)
            : "Consultar";
        const type = p.property_type_id ? p.property_type_id[1] : "";
        const advisor = p.user_id ? p.user_id[1] : "Sin asignar";
        const address = [p.street, p.city].filter(Boolean).join(", ");
        return `
            <div class="o_estate_map_popup">
                <div class="o_estate_map_popup_title">${escapeHtml(p.title || p.name)}</div>
                <div class="o_estate_map_popup_price">${escapeHtml(price)}</div>
                <div class="o_estate_map_popup_meta">
                    <span class="badge" style="background:${info.color}">${escapeHtml(info.label)}</span>
                    ${type ? `<span class="text-muted">${escapeHtml(type)}</span>` : ""}
                </div>
                ${address ? `<div class="text-muted small">${escapeHtml(address)}</div>` : ""}
                <div class="text-muted small">Asesor: ${escapeHtml(advisor)}</div>
                <button class="btn btn-primary btn-sm w-100 mt-2 o_estate_map_open" data-id="${p.id}">
                    Abrir ficha
                </button>
            </div>`;
    }

    _openProperty(id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "estate.property",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("estate_property_map", PropertyMap);
