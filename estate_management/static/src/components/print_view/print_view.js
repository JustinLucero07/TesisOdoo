import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { STATIC_ACTIONS_GROUP_NUMBER } from "@web/search/action_menus/action_menus";
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
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

/**
 * Lee una tabla de la vista como filas de celdas de texto.
 *
 * En las listas se trabaja por columnas: cada celda ocupa una o varias
 * columnas (colspan) y se descartan las columnas que son controles de Odoo
 * (casillas, menú de columnas) o que quedaron vacías. Así el encabezado, las
 * filas de grupo y los totales quedan siempre alineados.
 */
function readTable(table, { onlySelected, isList }) {
    const sections = { thead: [], tbody: [], tfoot: [] };
    for (const section of Object.keys(sections)) {
        for (const tr of table.querySelectorAll(`:scope > ${section} > tr`)) {
            const isData = tr.classList.contains("o_data_row");
            if (onlySelected && isData && !tr.querySelector(".o_list_record_selector input:checked")) {
                continue;
            }
            const cells = [...tr.children]
                .filter((cell) => isList || !cell.matches(SKIP_CELLS))
                .map((cell) => ({
                    text: cellText(cell),
                    colspan: Number(cell.getAttribute("colspan") || 1),
                    rowspan: Number(cell.getAttribute("rowspan") || 1),
                    control: cell.matches(SKIP_CELLS) || cell.matches(".w-print-0"),
                    numeric: cell.matches(
                        ".o_list_number, .o_pivot_cell_value, .o_list_number_th, .o_pivot_measure_row"
                    ),
                    header: cell.matches("th"),
                }));
            if (section === "tbody" && !cells.some((c) => c.text)) {
                continue; // filas vacías de relleno
            }
            sections[section].push({ cells, group: tr.classList.contains("o_group_header"), isData });
        }
    }
    return isList ? alignListColumns(sections) : sections;
}

function alignListColumns(sections) {
    const rows = [...sections.thead, ...sections.tbody, ...sections.tfoot];
    // Cada fila expandida a "ranuras" de columna.
    for (const row of rows) {
        let slot = 0;
        for (const cell of row.cells) {
            cell.start = slot;
            slot += cell.colspan;
        }
        row.width = slot;
    }
    const width = Math.max(0, ...rows.map((r) => r.width));
    const keep = new Array(width).fill(false);
    for (let i = 0; i < width; i++) {
        let control = false;
        let hasText = false;
        for (const row of rows) {
            const cell = row.cells.find((c) => c.start <= i && i < c.start + c.colspan);
            if (!cell) {
                continue;
            }
            if (cell.colspan === 1 && cell.control) {
                control = true;
            }
            if (cell.colspan === 1 && cell.text) {
                hasText = true;
            }
        }
        keep[i] = !control && hasText;
    }
    for (const row of rows) {
        row.cells = row.cells
            .map((cell) => {
                let span = 0;
                for (let i = cell.start; i < cell.start + cell.colspan; i++) {
                    span += keep[i] ? 1 : 0;
                }
                return { ...cell, colspan: span };
            })
            .filter((cell) => cell.colspan > 0);
    }
    return sections;
}

function renderCell(cell, tag) {
    const attrs = [];
    if (cell.colspan > 1) {
        attrs.push(`colspan="${cell.colspan}"`);
    }
    if (cell.rowspan > 1) {
        attrs.push(`rowspan="${cell.rowspan}"`);
    }
    const classes = [];
    if (cell.numeric) {
        classes.push("num");
    }
    if (cell.text.length <= 22) {
        classes.push("nowrap");
    } else if (cell.text.length > 38) {
        classes.push("long");
    }
    if (classes.length) {
        attrs.push(`class="${classes.join(" ")}"`);
    }
    return `<${tag}${attrs.length ? " " + attrs.join(" ") : ""}>${escapeHtml(cell.text)}</${tag}>`;
}

function tableToHtml(table, { onlySelected, isList }) {
    const sections = readTable(table, { onlySelected, isList });
    const head = sections.thead
        .map((row) => `<tr>${row.cells.map((c) => renderCell(c, "th")).join("")}</tr>`)
        .join("");
    let zebra = 0;
    const body = sections.tbody
        .map((row) => {
            const cls = row.group ? "group" : zebra++ % 2 ? "odd" : "";
            const html = row.cells
                .map((c) => renderCell(c, row.group || (!isList && c.header) ? "th" : "td"))
                .join("");
            return `<tr class="${cls}">${html}</tr>`;
        })
        .join("");
    const foot = sections.tfoot
        .map((row) => `<tr>${row.cells.map((c) => renderCell(c, "td")).join("")}</tr>`)
        .join("");
    const count = sections.tbody.filter((row) => row.isData).length;
    return {
        html: `<table><thead>${head}</thead><tbody>${body}</tbody>${foot ? `<tfoot>${foot}</tfoot>` : ""}</table>`,
        count,
    };
}

const PRINT_STYLE = `
    * { box-sizing: border-box; }
    body { font-family: "Segoe UI", Roboto, Arial, sans-serif; font-size: 10.5px; color: #1f2937; margin: 0; }
    .head { display: flex; justify-content: space-between; align-items: flex-end;
            border-bottom: 3px solid #0b3c66; padding-bottom: 8px; margin-bottom: 10px; }
    .brand { font-size: 11px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: #1877f2; }
    h1 { font-size: 18px; margin: 2px 0 0; color: #0b3c66; }
    .stamp { text-align: right; color: #6b7280; font-size: 10px; line-height: 1.5; }
    .stamp b { color: #0b3c66; font-size: 12px; }
    .chips { margin: 0 0 10px; }
    .chip { display: inline-block; background: #eef4ff; color: #0b3c66; border: 1px solid #c9dcff;
            border-radius: 999px; padding: 2px 9px; margin: 0 6px 4px 0; font-size: 10px; }
    table { border-collapse: separate; border-spacing: 0; width: 100%; }
    th, td { padding: 5px 7px; text-align: left; vertical-align: top; border-bottom: 1px solid #e5e7eb; }
    thead th { background: #0b3c66; color: #fff; font-weight: 600; font-size: 10px;
               text-transform: uppercase; letter-spacing: .03em; border-bottom: none; }
    thead th:first-child { border-top-left-radius: 6px; }
    thead th:last-child { border-top-right-radius: 6px; }
    tbody tr.odd td { background: #f8fafc; }
    tbody tr.group th, tbody tr.group td { background: #e8eef7; color: #0b3c66; font-weight: 700;
               border-top: 1px solid #c7d4e8; }
    tbody th { background: #f3f6fa; font-weight: 600; }
    tfoot td { background: #0b3c66; color: #fff; font-weight: 700; }
    .num { text-align: right; }
    .nowrap { white-space: nowrap; }
    td.long { min-width: 150px; }
    thead { display: table-header-group; }
    tfoot { display: table-row-group; }
    tr { page-break-inside: avoid; }
    img.chart { display: block; max-width: 100%; margin: 10px auto; }
    .foot { margin-top: 12px; color: #9ca3af; font-size: 9.5px; text-align: center; }
    @page { size: landscape; margin: 11mm 10mm; }
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
        return { html: canvas ? `<img class="chart" src="${canvas.toDataURL("image/png")}"/>` : "" };
    }
    const selector = viewType === "pivot" ? ".o_pivot table" : "table.o_list_table";
    const table = root?.querySelector(selector);
    if (!table) {
        return { html: "" };
    }
    const isList = viewType === "list";
    const onlySelected = isList && Boolean(env.model?.root?.selection?.length);
    return tableToHtml(table, { onlySelected, isList });
}

/** Imprime la vista actual (lista, pivote o gráfico) tal como se ve. */
export function printCurrentView(env) {
    const title = viewTitle(env);
    const { html, count } = buildContent(env);
    const content = html || "<p>No hay datos para imprimir.</p>";
    const now = new Date().toLocaleString();
    const company = user.activeCompany?.name || "Inmobi";
    const chips = viewFilters(env)
        .map((f) => `<span class="chip">${escapeHtml(f)}</span>`)
        .join("");
    const total = count ? `<b>${count}</b> registro${count === 1 ? "" : "s"}<br/>` : "";
    const page = `<!DOCTYPE html><html><head><meta charset="utf-8"/>
        <title>${escapeHtml(title)}</title><style>${PRINT_STYLE}</style></head>
        <body>
            <div class="head">
                <div><div class="brand">${escapeHtml(company)}</div><h1>${escapeHtml(title)}</h1></div>
                <div class="stamp">${total}Impreso: ${escapeHtml(now)}</div>
            </div>
            ${chips ? `<div class="chips">${chips}</div>` : ""}
            ${content}
            <div class="foot">${escapeHtml(company)} · ${escapeHtml(title)}</div>
        </body></html>`;

    // Se imprime desde un iframe oculto para no depender de ventanas emergentes.
    const iframe = document.createElement("iframe");
    iframe.style.cssText = "position:fixed;right:0;bottom:0;width:0;height:0;border:0;";
    document.body.appendChild(iframe);
    const doc = iframe.contentWindow.document;
    doc.open();
    doc.write(page);
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
