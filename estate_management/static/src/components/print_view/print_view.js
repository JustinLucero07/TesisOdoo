import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { STATIC_ACTIONS_GROUP_NUMBER } from "@web/search/action_menus/action_menus";
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";

const PRINTABLE_VIEWS = ["list", "pivot", "graph"];

// Celdas que son controles de la vista, no datos.
const SKIP_CELLS = [
    ".o_list_record_selector",
    ".o_list_actions_header",
    ".o_list_record_remove",
    ".o_list_controller",
].join(",");

function escapeHtml(text) {
    return String(text ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

function cellText(cell) {
    const tags = cell.querySelectorAll(".o_tag, .badge");
    if (tags.length > 1) {
        return [...tags].map((tag) => tag.innerText.trim()).filter(Boolean).join(", ");
    }
    const checkbox = cell.querySelector("input[type='checkbox']");
    if (checkbox && !cell.innerText.trim()) {
        return checkbox.checked ? "✔" : "";
    }
    return cell.innerText.replace(/\s+/g, " ").trim();
}

/** Copia una tabla de la vista (lista o pivote) como tabla limpia. */
function tableToHtml(table, { onlySelected }) {
    const rows = [];
    for (const section of ["thead", "tbody", "tfoot"]) {
        for (const tr of table.querySelectorAll(`:scope > ${section} > tr`)) {
            const isData = tr.classList.contains("o_data_row");
            if (onlySelected && isData && !tr.querySelector(".o_list_record_selector input:checked")) {
                continue;
            }
            const cells = [...tr.children].filter((cell) => !cell.matches(SKIP_CELLS));
            const texts = cells.map(cellText);
            if (section === "tbody" && !texts.some(Boolean)) {
                continue; // filas vacías de relleno
            }
            let cls = section === "tbody" ? "" : section;
            if (tr.classList.contains("o_group_header")) {
                cls = "group";
            }
            const html = cells
                .map((cell, index) => {
                    const tag = section === "tbody" && !cell.matches("th") ? "td" : "th";
                    const span = ["colspan", "rowspan"]
                        .filter((attr) => cell.getAttribute(attr) && cell.getAttribute(attr) !== "1")
                        .map((attr) => ` ${attr}="${cell.getAttribute(attr)}"`)
                        .join("");
                    const numeric = cell.matches(".o_list_number, .o_pivot_cell_value, .o_list_number_th")
                        ? ' class="num"'
                        : "";
                    return `<${tag}${span}${numeric}>${escapeHtml(texts[index])}</${tag}>`;
                })
                .join("");
            rows.push(`<tr class="${cls}">${html}</tr>`);
        }
    }
    return `<table>${rows.join("")}</table>`;
}

const PRINT_STYLE = `
    body { font-family: Arial, Helvetica, sans-serif; font-size: 11px; color: #1f2937; margin: 18px; }
    h1 { font-size: 17px; margin: 0 0 4px; color: #0b3c66; }
    .meta { color: #6b7280; margin-bottom: 12px; }
    .meta span { display: inline-block; margin-right: 14px; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #d1d5db; padding: 4px 6px; text-align: left; vertical-align: top; }
    tr.thead th { background: #0b3c66; color: #fff; }
    tr.group th, tr.group td { background: #eef2f7; font-weight: bold; }
    tr.tfoot th, tr.tfoot td { background: #f3f4f6; font-weight: bold; }
    .num { text-align: right; white-space: nowrap; }
    img.chart { max-width: 100%; }
    thead, tr.thead { display: table-header-group; }
    tr { page-break-inside: avoid; }
    @page { size: landscape; margin: 12mm; }
`;

function viewTitle(env) {
    const breadcrumbs = env.config.breadcrumbs || [];
    return breadcrumbs.map((b) => b.name).filter(Boolean).join(" / ") || document.title;
}

function viewFilters(env) {
    return (env.searchModel?.facets || []).map((facet) =>
        facet.values.join(` ${facet.separator || "o"} `)
    );
}

function findViewRoot() {
    const actions = document.querySelectorAll(".o_action_manager > .o_action");
    return actions[actions.length - 1] || document.querySelector(".o_action_manager");
}

function buildContent(env) {
    const root = findViewRoot();
    const viewType = env.config.viewType;
    if (viewType === "graph") {
        const canvas = root?.querySelector(".o_graph_canvas_container canvas, canvas");
        return canvas ? `<img class="chart" src="${canvas.toDataURL("image/png")}"/>` : "";
    }
    const selector = viewType === "pivot" ? ".o_pivot table" : "table.o_list_table";
    const table = root?.querySelector(selector);
    if (!table) {
        return "";
    }
    const onlySelected = viewType === "list" && Boolean(env.model?.root?.selection?.length);
    return tableToHtml(table, { onlySelected });
}

/** Imprime la vista actual (lista, pivote o gráfico) tal como se ve. */
export function printCurrentView(env) {
    const title = viewTitle(env);
    const content = buildContent(env) || "<p>No hay datos para imprimir.</p>";
    const now = new Date().toLocaleString();
    const meta = [`<span>Impreso: ${escapeHtml(now)}</span>`]
        .concat(viewFilters(env).map((f) => `<span>Filtro: ${escapeHtml(f)}</span>`))
        .join("");
    const html = `<!DOCTYPE html><html><head><meta charset="utf-8"/>
        <title>${escapeHtml(title)}</title><style>${PRINT_STYLE}</style></head>
        <body><h1>${escapeHtml(title)}</h1><div class="meta">${meta}</div>${content}</body></html>`;

    // Se imprime desde un iframe oculto para no depender de ventanas emergentes.
    const iframe = document.createElement("iframe");
    iframe.style.cssText = "position:fixed;right:0;bottom:0;width:0;height:0;border:0;";
    document.body.appendChild(iframe);
    const doc = iframe.contentWindow.document;
    doc.open();
    doc.write(html);
    doc.close();
    iframe.contentWindow.addEventListener("afterprint", () => iframe.remove());
    setTimeout(() => {
        iframe.contentWindow.focus();
        iframe.contentWindow.print();
        setTimeout(() => iframe.isConnected && iframe.remove(), 60000);
    }, 300);
}

export class PrintViewItem extends Component {
    static template = "estate_management.PrintViewItem";
    static components = { DropdownItem };
    static props = {};

    onPrint() {
        printCurrentView(this.env);
    }
}

// Con filas seleccionadas Odoo cambia el engranaje por el menú "Acciones":
// ahí también va "Imprimir" (imprime solo las filas marcadas).
patch(ListController.prototype, {
    getStaticActionMenuItems() {
        const items = super.getStaticActionMenuItems(...arguments);
        items.estate_print = {
            sequence: 15,
            icon: "fa fa-print",
            description: _t("Imprimir"),
            callback: () => printCurrentView(this.env),
        };
        return items;
    },
});

registry.category("cogMenu").add(
    "estate-print-view",
    {
        Component: PrintViewItem,
        groupNumber: STATIC_ACTIONS_GROUP_NUMBER,
        isDisplayed: (env) => PRINTABLE_VIEWS.includes(env.config.viewType),
    },
    { sequence: 5 }
);
