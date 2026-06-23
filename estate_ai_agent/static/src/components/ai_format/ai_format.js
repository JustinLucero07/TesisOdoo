/** @odoo-module **/
// Formateador de respuestas IA compartido entre el chat flotante y el chat
// de propiedad: markdown, tablas, listas, graficos SVG y packs de marketing.

import { markup } from "@odoo/owl";

const PALETTE = ['#004274','#E53935','#00897B','#FF9800','#7B1FA2','#0288D1','#43A047','#F4511E','#546E7A','#FDD835'];

const PACK_META = {
    instagram:    { icon: 'fa-instagram',      label: 'Instagram Caption + Hashtags', color: '#E4405F' },
    facebook:     { icon: 'fa-facebook',       label: 'Facebook Post',                color: '#004274' },
    whatsapp:     { icon: 'fa-whatsapp',       label: 'WhatsApp Broadcast',           color: '#25D366' },
    email_asunto: { icon: 'fa-envelope-o',     label: 'Email — Asunto',               color: '#FF9800' },
    email_cuerpo: { icon: 'fa-envelope',       label: 'Email — Cuerpo',               color: '#FF9800' },
    google_ads:   { icon: 'fa-google',         label: 'Google Ads',                   color: '#4285F4' },
    puntos_clave: { icon: 'fa-check-circle',   label: 'Puntos Clave de Venta',        color: '#00897B' },
    slogan:       { icon: 'fa-lightbulb-o',    label: 'Slogan',                       color: '#7B1FA2' },
};


window._inmoCopyPack = function(packId) {
    const el = document.getElementById(packId);
    if (!el) return;
    const text = el.innerText || el.textContent;
    navigator.clipboard.writeText(text).then(() => {
        const btn = document.querySelector(`[data-pack-id="${packId}"]`);
        if (btn) { btn.textContent = 'Copiado'; btn.style.background = '#00897B'; btn.style.color = 'white';
            setTimeout(() => { btn.textContent = 'Copiar'; btn.style.background = ''; btn.style.color = ''; }, 2200); }
    }).catch(() => {
        const range = document.createRange();
        range.selectNodeContents(el);
        window.getSelection().removeAllRanges();
        window.getSelection().addRange(range);
    });
};

window._inmoToggleChart = function(uid, mode, btn) {
    const card = document.getElementById(uid);
    if (!card) return;
    const line = card.querySelector('.rc-line'), bar = card.querySelector('.rc-bar');
    if (line) line.style.display = mode === 'line' ? '' : 'none';
    if (bar) bar.style.display = mode === 'bar' ? '' : 'none';
    card.querySelectorAll('.ai-tog-btn').forEach(b => b.classList.remove('ai-tog-on'));
    btn.classList.add('ai-tog-on');
};

window._inmoDownloadChart = function(btn) {
    const chart = btn.closest('.ai-chart');
    if (!chart) return;
    const nameEl = chart.querySelector('.ai-chart-name, .ai-rc-title');
    const title = nameEl ? nameEl.textContent.trim() : 'Gráfico';
    // Remove the action/toggle controls from the printed version
    const cloned = chart.cloneNode(true);
    cloned.querySelectorAll('.ai-chart-act, .ai-toggle').forEach(b => b.remove());
    // En el PDF mostramos ambas vistas (línea y barras)
    cloned.querySelectorAll('.ai-rc-view').forEach(v => { v.style.display = ''; });
    const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>${title}</title>
<style>
  body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;padding:32px;background:#fff;margin:0}
  h2{color:#004274;font-size:15px;font-weight:700;margin:0 0 18px;text-transform:uppercase;letter-spacing:.6px}
  .ai-chart{padding:0} svg{max-width:100%;height:auto}
  @page{margin:20mm} @media print{body{padding:0}}
</style></head><body>
<h2>${title}</h2>
${cloned.innerHTML}
<script>window.onload=function(){window.print();}<\/script>
</body></html>`;
    const w = window.open('', '_blank', 'width=760,height=560');
    if (w) { w.document.write(html); w.document.close(); }
};



export function formatResponse(text) {
        if (!text) return markup("");
        let t = text;

        // ── Marketing Pack Cards ─────────────────────────────────────────────
        t = t.replace(/\[PACK:([^\]]+)\]([\s\S]*?)\[\/PACK\]/g, (_, canal, contenido) => {
            const meta = PACK_META[canal.trim()] || { icon: 'fa-file-text-o', label: canal, color: '#004274' };
            const packId = 'pack_' + canal.replace(/[^a-z0-9]/g, '') + '_' + Math.random().toString(36).slice(2, 8);
            // Escape HTML but preserve line breaks
            const safe = contenido.trim()
                .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            return `<div class="ai-pack-card" style="border-left:4px solid ${meta.color}">
  <div class="ai-pack-header">
    <span class="ai-pack-icon" style="background:${meta.color}18;color:${meta.color}"><i class="fa ${meta.icon}"/></span>
    <span class="ai-pack-label" style="color:${meta.color}">${meta.label}</span>
    <button class="ai-pack-copy" data-pack-id="${packId}" onclick="window._inmoCopyPack('${packId}')" title="Copiar al portapapeles">Copiar</button>
  </div>
  <pre class="ai-pack-body" id="${packId}">${safe}</pre>
</div>`;
        });

        // ── Chart data parser ────────────────────────────────────────────────
        const parsePairs = s => s.split(',').map(p => {
            const i = p.indexOf(':'); if (i < 0) return null;
            const label = p.slice(0, i).trim();
            const val = parseFloat(p.slice(i+1).replace(/[^\d.\-]/g,'')) || 0;
            const raw = p.slice(i+1).trim();
            return { label, val, raw };
        }).filter(Boolean);

        // Acción única, discreta: descargar el gráfico como PDF.
        // SVG inline (no FontAwesome, etiqueta bien cerrada) para evitar
        // glifos sueltos por <i .../> auto-cerrado o fuente no cargada.
        const DL_SVG = `<svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" aria-hidden="true"><path d="M12 16l-5-5h3V4h4v7h3l-5 5zm-7 2h14v2H5v-2z"></path></svg>`;
        const dlBtn = `<button class="ai-chart-act" onclick="window._inmoDownloadChart(this)" title="Descargar como PDF">${DL_SVG}</button>`;
        const chartHead = (title) => `<div class="ai-chart-title"><span class="ai-chart-name">${title}</span>${dlBtn}</div>`;

        // ════ REPORT CARD (barra + línea con toggle, KPIs, pico resaltado) ════
        const BLUE = '#004274', RED = '#E53935';
        // Parsea "Título::periodo=...;KPI=val;..." → {title, period, kpis[]}
        const parseMeta = (raw) => {
            let title = raw || 'Reporte', period = '', kpis = [];
            if (title.includes('::')) {
                const parts = title.split('::');
                title = parts[0].trim();
                parts[1].split(';').forEach(kv => {
                    const i = kv.indexOf('=');
                    if (i < 0) return;
                    const k = kv.slice(0, i).trim(), v = kv.slice(i + 1).trim();
                    if (k.toLowerCase() === 'periodo') period = v;
                    else if (k && v) kpis.push({ label: k, val: v });
                });
            }
            return { title, period, kpis };
        };
        const buildBars = (data) => {
            const mx = Math.max(...data.map(d => d.val), 1);
            return '<div class="ai-rc-bars">' + data.map(d => {
                const c = d.val === mx ? RED : BLUE;
                const pct = Math.max((d.val / mx) * 100, 2);
                return `<div class="ai-hbar" title="${d.label}: ${d.raw}">
                    <div class="ai-hbar-label">${d.label}</div>
                    <div class="ai-hbar-track"><div class="ai-hbar-fill" style="width:${pct}%;background:${c}"></div></div>
                    <div class="ai-hbar-val" style="color:${c}">${d.raw}</div>
                </div>`;
            }).join('') + '</div>';
        };
        const buildLine = (data) => {
            const mn = Math.min(...data.map(d => d.val));
            const mx = Math.max(...data.map(d => d.val), 1);
            const W = 460, H = 180, PX = 28, PY = 32;
            const sx = data.length > 1 ? (W - PX * 2) / (data.length - 1) : 0;
            const toY = v => H - PY - ((v - mn) / (mx - mn || 1)) * (H - PY * 2);
            const pts = data.map((d, i) => ({ x: PX + i * sx, y: toY(d.val), ...d }));
            const smooth = (p) => {
                if (p.length < 2) return p.length ? `M${p[0].x},${p[0].y}` : '';
                let d = `M${p[0].x},${p[0].y}`;
                for (let i = 0; i < p.length - 1; i++) {
                    const p0 = p[i - 1] || p[i], p1 = p[i], p2 = p[i + 1], p3 = p[i + 2] || p[i + 1], tt = 0.18;
                    d += ` C${p1.x + (p2.x - p0.x) * tt},${p1.y + (p2.y - p0.y) * tt} ${p2.x - (p3.x - p1.x) * tt},${p2.y - (p3.y - p1.y) * tt} ${p2.x},${p2.y}`;
                }
                return d;
            };
            const lp = smooth(pts), fp = `${lp} L${pts[pts.length - 1].x},${H - PY} L${pts[0].x},${H - PY} Z`;
            const gid = `g${Math.random().toString(36).slice(2, 6)}`;
            let s = `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto">`;
            s += `<defs><linearGradient id="${gid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="${BLUE}" stop-opacity=".20"/><stop offset="100%" stop-color="${BLUE}" stop-opacity="0"/></linearGradient></defs>`;
            [0, 0.5, 1].forEach(f => { const gy = PY + f * (H - PY * 2); s += `<line x1="${PX}" y1="${gy}" x2="${W - PX}" y2="${gy}" stroke="#eef1f5" stroke-width="1"/>`; });
            s += `<path d="${fp}" fill="url(#${gid})"/><path d="${lp}" fill="none" stroke="${BLUE}" stroke-width="2.6" stroke-linejoin="round" stroke-linecap="round"/>`;
            pts.forEach(p => {
                const isMax = p.val === mx, c = isMax ? RED : BLUE;
                s += `<circle cx="${p.x}" cy="${p.y}" r="${isMax ? 6 : 4.5}" fill="${isMax ? RED : 'white'}" stroke="${c}" stroke-width="2.4"><title>${p.label}: ${p.raw}</title></circle>`;
                s += `<text x="${p.x}" y="${H - 9}" text-anchor="middle" font-size="10" fill="#9aa7b8" font-weight="500">${p.label}</text>`;
                const above = p.y > PY + 16;
                s += `<text x="${p.x}" y="${above ? p.y - 11 : p.y + 18}" text-anchor="middle" font-size="10.5" fill="${c}" font-weight="800">${p.raw}</text>`;
            });
            return s + '</svg>';
        };
        const renderReportCard = (defaultView, rawTitle, ds) => {
            const data = parsePairs(ds);
            if (!data.length) return '';
            const { title, period, kpis: metaKpis } = parseMeta(rawTitle);
            let kpis = metaKpis;
            if (!kpis.length) {
                const total = data.reduce((s, d) => s + d.val, 0);
                const avg = data.length ? total / data.length : 0;
                const peak = data.reduce((m, d) => d.val > m.val ? d : m, data[0]);
                kpis = [
                    { label: 'Total', val: total },
                    { label: 'Promedio', val: avg.toFixed(1) },
                    { label: 'Máximo', val: `${peak.label} (${peak.raw})` },
                ];
            }
            const uid = 'rc' + Math.random().toString(36).slice(2, 7);
            const kpiHtml = kpis.slice(0, 4).map(k =>
                `<div class="ai-kpi"><div class="ai-kpi-label">${k.label}</div><div class="ai-kpi-val">${k.val}</div></div>`).join('');
            const lineActive = defaultView === 'line';
            return `<div class="ai-chart ai-rc" id="${uid}">
                <div class="ai-rc-head">
                    <div class="ai-rc-titlewrap">
                        <span class="ai-rc-accent"></span>
                        <div>
                            <div class="ai-rc-title">${title}</div>
                            ${period ? `<div class="ai-rc-sub">${period}</div>` : ''}
                        </div>
                    </div>
                    <div class="ai-rc-tools">
                        <div class="ai-toggle">
                            <button class="ai-tog-btn ${lineActive ? 'ai-tog-on' : ''}" onclick="window._inmoToggleChart('${uid}','line',this)">Línea</button>
                            <button class="ai-tog-btn ${lineActive ? '' : 'ai-tog-on'}" onclick="window._inmoToggleChart('${uid}','bar',this)">Barras</button>
                        </div>
                        ${dlBtn}
                    </div>
                </div>
                ${kpiHtml ? `<div class="ai-kpis">${kpiHtml}</div>` : ''}
                <div class="ai-rc-view rc-line" style="${lineActive ? '' : 'display:none'}">${buildLine(data)}</div>
                <div class="ai-rc-view rc-bar" style="${lineActive ? 'display:none' : ''}">${buildBars(data)}</div>
            </div>`;
        };

        // bar y línea → mismo card rico, distinto vista por defecto
        t = t.replace(/\[GRAFICO:barra(?:\|([^\],]*))?,(.*?)\]/g, (_, ct, ds) => renderReportCard('bar', ct || 'Gráfico', ds));

        // ── PIE / CIRCULAR CHART ─────────────────────────────────────────────
        t = t.replace(/\[GRAFICO:circular(?:\|([^\],]*))?,(.*?)\]/g, (_, chartTitle, ds) => {
            const data = parsePairs(ds);
            const total = data.reduce((s,d)=>s+d.val,0) || 1;
            const R = 62, HOLE = 38, CX = 80, CY = 80;
            const C = 2 * Math.PI * R;
            let offset = 0;
            // Donut ring
            let svg = `<svg viewBox="0 0 160 160" style="width:130px;height:130px;flex-shrink:0">`;
            // Background ring
            svg += `<circle cx="${CX}" cy="${CY}" r="${R}" fill="none" stroke="#f0f2f5" stroke-width="20"/>`;
            data.forEach((d, i) => {
                const pct = (d.val / total);
                const pctStr = (pct * 100).toFixed(1);
                const dash = C * pct;
                const gap = C - dash;
                svg += `<circle cx="${CX}" cy="${CY}" r="${R}" fill="none" stroke="${PALETTE[i%PALETTE.length]}" stroke-width="20" stroke-linecap="round" stroke-dasharray="${dash > 0 ? dash - 1 : 0} ${gap > 0 ? gap + 1 : C}" stroke-dashoffset="${-offset}" transform="rotate(-90 ${CX} ${CY})"><title>${d.label}: ${d.raw} (${pctStr}%)</title></circle>`;
                offset += dash;
            });
            // Center: total value
            svg += `<text x="${CX}" y="${CY - 3}" text-anchor="middle" font-size="17" font-weight="800" fill="#1a2e44">${total}</text>`;
            svg += `<text x="${CX}" y="${CY + 12}" text-anchor="middle" font-size="8" fill="#9aa7b8" font-weight="600" letter-spacing="1">TOTAL</text>`;
            svg += `</svg>`;
            // Leyenda en 2 columnas: punto · etiqueta · cantidad · %
            let legend = `<div class="ai-donut-legend">`;
            data.forEach((d, i) => {
                const pct = ((d.val / total) * 100).toFixed(1);
                const c = PALETTE[i%PALETTE.length];
                legend += `<div class="ai-leg-item" title="${d.label}: ${d.raw} (${pct}%)">
                    <span class="ai-leg-dot" style="background:${c}"></span>
                    <span class="ai-leg-label">${d.label}</span>
                    <span class="ai-leg-count">${d.raw}</span>
                    <span class="ai-leg-pct" style="color:${c}">${pct}%</span>
                </div>`;
            });
            legend += `</div>`;
            return `<div class="ai-chart">${chartHead(chartTitle || 'Distribución')}<div class="ai-chart-body ai-donut-body">${svg}${legend}</div></div>`;
        });

        // línea → mismo card rico con vista por defecto = línea
        t = t.replace(/\[GRAFICO:linea(?:\|([^\],]*))?,(.*?)\]/g, (_, ct, ds) => renderReportCard('line', ct || 'Tendencia', ds));

        // ── HISTOGRAM ────────────────────────────────────────────────────────
        t = t.replace(/\[GRAFICO:histograma(?:\|([^\],]*))?,(.*?)\]/g, (_, chartTitle, ds) => {
            const data = parsePairs(ds);
            const mx = Math.max(...data.map(d=>d.val), 1);
            const W = 400, H = 130, PY = 22;
            const barW = (W - 20) / data.length;
            let svg = `<div class="ai-chart">${chartHead(chartTitle || 'Histograma')}<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto">`;
            data.forEach((d, i) => {
                const bh = (d.val / mx) * (H - PY * 2);
                const x = 10 + i * barW;
                const y = H - PY - bh;
                svg += `<rect x="${x}" y="${y}" width="${barW - 1}" height="${bh}" rx="2" fill="${PALETTE[i%PALETTE.length]}" opacity=".85"><title>${d.label}: ${d.raw}</title></rect>`;
                svg += `<text x="${x + barW/2}" y="${H-5}" text-anchor="middle" font-size="7.5" fill="#888">${d.label}</text>`;
                svg += `<text x="${x + barW/2}" y="${y-4}" text-anchor="middle" font-size="7.5" fill="#333" font-weight="600">${d.raw}</text>`;
            });
            return svg + '</svg></div>';
        });

        // ── SCATTER ──────────────────────────────────────────────────────────
        t = t.replace(/\[GRAFICO:dispersion(?:\|([^\],]*))?,(.*?)\]/g, (_, chartTitle, ds) => {
            const data = parsePairs(ds);
            const mxV = Math.max(...data.map(d=>d.val), 1);
            const W = 400, H = 140, PX = 30, PY = 22;
            let svg = `<div class="ai-chart">${chartHead(chartTitle || 'Dispersión')}<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto">`;
            svg += `<line x1="${PX}" y1="${H-PY}" x2="${W-10}" y2="${H-PY}" stroke="#ddd" stroke-width="1"/>`;
            svg += `<line x1="${PX}" y1="10" x2="${PX}" y2="${H-PY}" stroke="#ddd" stroke-width="1"/>`;
            data.forEach((d, i) => {
                const x = PX + (i / Math.max(data.length-1, 1)) * (W - PX - 10);
                const y = H - PY - (d.val / mxV) * (H - PY - 14);
                svg += `<circle cx="${x}" cy="${y}" r="6" fill="${PALETTE[i%PALETTE.length]}" opacity=".75" stroke="white" stroke-width="1.5"><title>${d.label}: ${d.raw}</title></circle>`;
                svg += `<text x="${x}" y="${H-6}" text-anchor="middle" font-size="7.5" fill="#888">${d.label}</text>`;
                svg += `<text x="${x}" y="${y-10}" text-anchor="middle" font-size="7.5" fill="#333" font-weight="600">${d.raw}</text>`;
            });
            return svg + '</svg></div>';
        });

        // ── GANTT ────────────────────────────────────────────────────────────
        t = t.replace(/\[GRAFICO:gantt(?:\|([^\],]*))?,(.*?)\]/g, (_, chartTitle, ds) => {
            const data = parsePairs(ds);
            const mx = Math.max(...data.map(d => d.val), 1);
            let h = `<div class="ai-chart">${chartHead(chartTitle || 'Cronograma')}`;
            data.forEach((d, i) => {
                const c = PALETTE[i % PALETTE.length];
                const w = Math.max((d.val / mx) * 100, 4);
                h += `<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px" title="${d.label}: ${d.raw}">
                    <div style="width:100px;font-size:11px;font-weight:600;color:#444;text-align:right;flex-shrink:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;padding-right:4px">${d.label}</div>
                    <div style="flex:1;background:#e8edf3;border-radius:6px;height:24px;overflow:hidden">
                        <div style="background:${c};width:${w}%;height:100%;border-radius:6px;display:flex;align-items:center;padding-left:8px;transition:width .8s cubic-bezier(.4,0,.2,1)">
                            <span style="font-size:11px;color:rgba(255,255,255,.95);font-weight:700;white-space:nowrap">${d.raw}</span>
                        </div>
                    </div>
                </div>`;
            });
            return h + '</div>';
        });

        // ── HEATMAP ──────────────────────────────────────────────────────────
        t = t.replace(/\[GRAFICO:calor(?:\|([^\],]*))?,(.*?)\]/g, (_, chartTitle, ds) => {
            const data = parsePairs(ds);
            const mx = Math.max(...data.map(d=>d.val), 1);
            const mn = Math.min(...data.map(d=>d.val));
            let h = `<div class="ai-chart">${chartHead(chartTitle || 'Mapa de calor')}<div style="display:flex;flex-wrap:wrap;gap:4px">`;
            data.forEach(d => {
                const intensity = (d.val - mn) / (mx - mn || 1);
                const r = Math.round(0 + intensity * 229);
                const g = Math.round(66 - intensity * 9);
                const b = Math.round(116 - intensity * 63);
                const txt = intensity > 0.5 ? 'white' : '#333';
                h += `<div style="flex:1;min-width:70px;background:rgb(${r},${g},${b});color:${txt};border-radius:8px;padding:10px;text-align:center" title="${d.label}: ${d.raw}">
                    <div style="font-size:.72em;font-weight:500;opacity:.8">${d.label}</div>
                    <div style="font-size:1.1em;font-weight:700">${d.raw}</div>
                </div>`;
            });
            return h + '</div></div>';
        });

        // ── Tables — estilo profesional, fila Total resaltada ────────────────
        t = t.replace(/(?:\|.+\|\n?)+/g, match => {
            const rows = match.trim().split('\n');
            let html = '<div class="ai-table-wrap"><table class="ai-table">';
            let isFirstRow = true;
            rows.forEach(row => {
                if (row.includes('---')) { isFirstRow = false; return; }
                const cols = row.split('|').filter((_c, i, a) => i > 0 && i < a.length - 1).map(c => c.trim());
                const isTotal = !isFirstRow && /^(total|totales)\b/i.test(cols[0] || '');
                if (isFirstRow) {
                    html += '<tr class="ai-tr-head">' + cols.map(c => `<th>${c}</th>`).join('') + '</tr>';
                } else {
                    html += `<tr class="${isTotal ? 'ai-tr-total' : ''}">` + cols.map(c => `<td>${c}</td>`).join('') + '</tr>';
                }
                isFirstRow = false;
            });
            return html + '</table></div>';
        });

        // ── Markdown formatting ──────────────────────────────────────────────
        // Encabezados al MISMO tamaño que el cuerpo (1em): se distinguen por peso
        // y color, no por tamaño → tipografía uniforme en todo el chat.
        t = t.replace(/^####\s+(.+)$/gm, '<div class="ai-md-h">$1</div>');
        t = t.replace(/^###\s+(.+)$/gm, '<div class="ai-md-h">$1</div>');
        t = t.replace(/^##\s+(.+)$/gm, '<div class="ai-md-h">$1</div>');
        t = t.replace(/^#\s+(.+)$/gm, '<div class="ai-md-h">$1</div>');
        t = t.replace(/^\* (.+)$/gm, '<li>$1</li>');
        t = t.replace(/(<li.*<\/li>\n?)+/g, '<ul class="ai-md-ul">$&</ul>');
        t = t
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n\n/g, '<br><br>')
            .replace(/\n/g, '<br>');

        return markup(t);
}
