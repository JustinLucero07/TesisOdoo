import json
from odoo import http
from odoo.http import request


class SalesReportController(http.Controller):

    @http.route('/estate_reports/map/embed', type='http', auth='user', csrf=False)
    def map_embed(self, **kwargs):
        """Standalone map page loaded inside an iframe in the dashboard."""
        props = request.env['estate.property'].sudo().search([
            ('latitude', '!=', 0),
            ('longitude', '!=', 0),
        ])

        state_colors = {'sold': '#dc2626', 'reserved': '#d97706', 'available': '#2563eb'}
        markers = []
        for p in props:
            markers.append({
                'lat': float(p.latitude),
                'lng': float(p.longitude),
                'title': p.title or p.name or '',
                'city': p.city or '',
                'price': p.price,
                'state': p.state,
                'color': state_colors.get(p.state, '#2563eb'),
            })

        markers_json = json.dumps(markers)
        base = '/estate_reports/static/lib/leaflet'

        html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <link rel="stylesheet" href="{base}/leaflet.css"/>
  <script src="{base}/leaflet.js"></script>
  <style>
    html, body {{ margin:0; padding:0; height:100%; }}
    #map {{ height:100vh; width:100%; }}
    .prop-popup b {{ font-size:13px; color:#1e3a5f; }}
    .prop-popup .price {{ color:#16a34a; font-weight:700; }}
    .legend {{ background:#fff; padding:8px 12px; border-radius:6px;
               box-shadow:0 1px 4px rgba(0,0,0,.25); line-height:22px; font-size:12px; }}
    .legend-dot {{ display:inline-block; width:10px; height:10px;
                   border-radius:50%; margin-right:5px; }}
  </style>
</head>
<body>
<div id="map"></div>
<script>
  var markers = {markers_json};

  // Fix default icon paths
  delete L.Icon.Default.prototype._getIconUrl;
  L.Icon.Default.mergeOptions({{
    iconUrl: '{base}/images/marker-icon.png',
    iconRetinaUrl: '{base}/images/marker-icon-2x.png',
    shadowUrl: '{base}/images/marker-shadow.png',
  }});

  var map = L.map('map').setView([-2.897, -79.004], 13);
  L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    attribution: '&copy; OpenStreetMap contributors',
    maxZoom: 18
  }}).addTo(map);

  function makeIcon(color) {{
    return L.divIcon({{
      className: '',
      html: '<div style="background:' + color + ';width:14px;height:14px;border-radius:50%;'
          + 'border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.4);"></div>',
      iconSize: [14, 14],
      iconAnchor: [7, 7],
      popupAnchor: [0, -10],
    }});
  }}

  var group = [];
  markers.forEach(function(m) {{
    var icon = makeIcon(m.color);
    var popup = '<div class="prop-popup"><b>' + m.title + '</b>'
              + (m.city ? '<br/>' + m.city : '')
              + '<br/><span class="price">$' + m.price.toLocaleString('es-EC', {{minimumFractionDigits:0}}) + '</span>'
              + '</div>';
    var marker = L.marker([m.lat, m.lng], {{icon: icon}}).bindPopup(popup).addTo(map);
    group.push(marker);
  }});

  if (group.length > 0) {{
    var bounds = L.featureGroup(group).getBounds();
    map.fitBounds(bounds, {{padding: [30, 30], maxZoom: 15}});
  }}

  // Legend
  var legend = L.control({{position: 'bottomright'}});
  legend.onAdd = function() {{
    var div = L.DomUtil.create('div', 'legend');
    div.innerHTML = '<strong>Estado</strong><br/>'
      + '<span class="legend-dot" style="background:#2563eb"></span>Disponible<br/>'
      + '<span class="legend-dot" style="background:#d97706"></span>Reservado<br/>'
      + '<span class="legend-dot" style="background:#dc2626"></span>Vendido';
    return div;
  }};
  legend.addTo(map);
</script>
</body>
</html>"""

        return request.make_response(html, headers=[
            ('Content-Type', 'text/html; charset=utf-8'),
            ('X-Frame-Options', 'SAMEORIGIN'),
        ])

    @http.route('/estate_reports/sales_report_xlsx/<int:wizard_id>',
                type='http', auth='user')
    def download_sales_report_xlsx(self, wizard_id, **kwargs):
        """Descarga el Excel del reporte de promedio de ventas."""
        wizard = request.env['estate.sales.report.wizard'].browse(wizard_id)
        if not wizard.exists():
            return request.not_found()
        wizard.check_access('read')
        content = wizard.generate_xlsx_bytes()
        d_from, d_to = wizard._get_period_range()
        filename = f'reporte_ventas_{d_from}_a_{d_to}.xlsx'
        return request.make_response(
            content,
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f'attachment; filename="{filename}"'),
                ('Content-Length', len(content)),
            ],
        )
