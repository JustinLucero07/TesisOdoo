import logging
import qrcode
import base64
import requests
from io import BytesIO
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class EstateProperty(models.Model):
    _name = 'estate.property'
    _description = 'Propiedad Inmobiliaria'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'estate.phone.mixin']
    _order = 'create_date desc'
    _rec_name = 'title'

    name = fields.Char(
        string='Referencia', readonly=True, copy=False,
        default='Nuevo')
    title = fields.Char(string='Título', required=True, tracking=True)
    description = fields.Html(string='Descripción')

    @api.depends('title', 'name')
    def _compute_display_name(self):
        for rec in self:
            if rec.name and rec.name != 'Nuevo':
                rec.display_name = f"{rec.title} [{rec.name}]" if rec.title else rec.name
            else:
                rec.display_name = rec.title or 'Nuevo'

    @api.model
    def _name_search(self, name='', domain=None, operator='ilike', limit=100, order=None):
        """Permite buscar por título o por referencia (PROP-0039)."""
        domain = domain or []
        if name:
            domain = ['|', ('title', operator, name), ('name', operator, name)] + domain
        return self._search(domain, limit=limit, order=order)
    property_type_id = fields.Many2one(
        'estate.property.type', string='Tipo de Propiedad',
        required=True, tracking=True)
    product_id = fields.Many2one(
        'product.template', string='Producto Vinculado', copy=False, readonly=True,
        help="Producto nativo de Odoo sincronizado para facturación")
    
    offer_type = fields.Selection([
        ('sale', 'Venta'),
        ('rent', 'Arrendamiento'),
    ], string='Tipo de Oferta', default='sale', tracking=True)

    # --- Ubicación ---
    street = fields.Char(string='Dirección')
    city = fields.Char(string='Ciudad', default='Cuenca', tracking=True)
    state_id = fields.Many2one(
        'res.country.state', string='Provincia/Estado',
        default=lambda self: self.env['res.country.state'].search(
            [('name', 'ilike', 'Azuay'), ('country_id.code', '=', 'EC')], limit=1))
    country_id = fields.Many2one(
        'res.country', string='País',
        default=lambda self: self.env['res.country'].search([('code', '=', 'EC')], limit=1))
    zip_code = fields.Char(string='Código Postal')

    _EC_POSTAL_CODES = {
        'cuenca': '010101', 'guayaquil': '090101', 'quito': '170101',
        'loja': '110101', 'ambato': '180101', 'riobamba': '060101',
        'machala': '070101', 'portoviejo': '130101', 'manta': '130701',
        'esmeraldas': '080101', 'ibarra': '100101', 'santo domingo': '230101',
    }

    @api.onchange('city')
    def _onchange_city_zip(self):
        if self.city:
            code = self._EC_POSTAL_CODES.get(self.city.lower().strip(), '')
            if code:
                self.zip_code = code
            # Auto-set Ecuador/Azuay when city is known
            if not self.country_id:
                ec = self.env['res.country'].search([('code', '=', 'EC')], limit=1)
                if ec:
                    self.country_id = ec
            if not self.state_id and self.city.lower().strip() == 'cuenca':
                azuay = self.env['res.country.state'].search(
                    [('name', 'ilike', 'Azuay'), ('country_id.code', '=', 'EC')], limit=1)
                if azuay:
                    self.state_id = azuay
            self.latitude = 0.0
            self.longitude = 0.0

    @api.onchange('state_id')
    def _onchange_state_set_country(self):
        """When province is selected, auto-set country to Ecuador."""
        if self.state_id and self.state_id.country_id:
            self.country_id = self.state_id.country_id

    @api.model
    def _fix_country_defaults(self):
        """Fix existing properties with wrong country/state. Called on module update."""
        ec = self.env['res.country'].search([('code', '=', 'EC')], limit=1)
        if not ec:
            return
        azuay = self.env['res.country.state'].search(
            [('name', 'ilike', 'Azuay'), ('country_id', '=', ec.id)], limit=1)
        # Fix country for all properties (this is an Ecuador-only system)
        bad_country = self.search([('country_id', '!=', ec.id)])
        if bad_country:
            bad_country.with_context(no_wp_sync=True, no_geocode=True).write(
                {'country_id': ec.id})
        # Set Azuay for properties in Cuenca with no state
        if azuay:
            cuenca_props = self.search([
                ('state_id', '=', False),
                ('city', 'ilike', 'Cuenca'),
            ])
            if cuenca_props:
                cuenca_props.with_context(no_wp_sync=True, no_geocode=True).write(
                    {'state_id': azuay.id})

    @api.model
    def _fix_ecuador_coordinates(self):
        """Corrige coordenadas con signo positivo erróneo para propiedades en Ecuador.
        Ecuador siempre tiene longitud negativa (hemisferio oeste) y Cuenca latitud negativa.
        Se ejecuta en cada actualización del módulo para reparar datos existentes.
        """
        # Propiedades con longitud positiva → definitivamente mal signo (Ecuador es siempre negativo en lon)
        wrong = self.search([('longitude', '>', 0)])
        fixed = 0
        for prop in wrong:
            new_lat = -abs(prop.latitude) if prop.latitude else 0.0
            new_lon = -abs(prop.longitude) if prop.longitude else 0.0
            super(EstateProperty, prop).write({'latitude': new_lat, 'longitude': new_lon})
            fixed += 1
        if fixed:
            _logger.info("_fix_ecuador_coordinates: corregidas %d propiedades con coordenadas incorrectas.", fixed)

    @api.onchange('street')
    def _onchange_street_keywords(self):
        if self.street and not self.sector_keywords:
            self.sector_keywords = self.street
        self.latitude = 0.0
        self.longitude = 0.0
    latitude = fields.Float(string='Latitud', digits=(10, 7))
    longitude = fields.Float(string='Longitud', digits=(10, 7))
    company_currency = fields.Many2one(
        'res.currency', string='Moneda', 
        default=lambda self: self.env.company.currency_id)
    map_url = fields.Char(string='URL del Mapa', compute='_compute_map_url')
    map_iframe = fields.Html(string='Vista de Mapa', compute='_compute_map_iframe', sanitize=False)

    @api.depends('latitude', 'longitude')
    def _compute_map_iframe(self):
        for rec in self:
            if rec.latitude and rec.longitude:
                lat = rec.latitude
                lng = rec.longitude
                # Use OpenStreetMap embed format
                url = f"https://www.openstreetmap.org/export/embed.html?bbox={lng-0.005}%2C{lat-0.005}%2C{lng+0.005}%2C{lat+0.005}&amp;layer=mapnik&amp;marker={lat}%2C{lng}"
                rec.map_iframe = (
                    f'<div style="position:relative; width:100%; padding-bottom:35%; border-radius:8px; border:1px solid #ddd; overflow:hidden;">'
                    f'<iframe src="{url}" style="position:absolute; top:0; left:0; width:100%; height:100%; border:none;"></iframe>'
                    f'</div>'
                )
            else:
                rec.map_iframe = '<div style="padding-bottom:25%; background:#f8f9fa; border:1px dashed #ccc; border-radius:8px; display:flex; align-items:center; justify-content:center; color:#6c757d; gap:6px"><i class="fa fa-map-marker"></i><small>Haz clic en <b>Ubicar en Mapa</b></small></div>'

    @api.depends('street', 'city', 'state_id', 'country_id', 'latitude', 'longitude')
    def _compute_map_url(self):
        for rec in self:
            if rec.latitude and rec.longitude:
                rec.map_url = f"https://www.google.com/maps/search/?api=1&query={rec.latitude},{rec.longitude}"
            else:
                parts = [p for p in [rec.street, rec.city, rec.state_id.name, rec.country_id.name] if p]
                address = ', '.join(parts).replace(' ', '+')
                if address:
                    rec.map_url = f"https://www.google.com/maps/search/?api=1&query={address}"
                else:
                    rec.map_url = False

    def action_open_map(self):
        self.ensure_one()
        if self.map_url:
            return {
                'type': 'ir.actions.act_url',
                'url': self.map_url,
                'target': 'new',
            }

    def _nominatim_search(self, query, countrycodes='ec'):
        """Shared Nominatim search. Returns (lat, lon, display_name) or None on any failure."""
        try:
            resp = requests.get(
                'https://nominatim.openstreetmap.org/search',
                params={'q': query, 'format': 'json', 'limit': 1, 'countrycodes': countrycodes},
                headers={'User-Agent': 'OdooEstateApp/1.0 (tesis@inmobiliaria.ec)'},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            if not data:
                return None
            lat = float(data[0]['lat'])
            lon = float(data[0]['lon'])
            return lat, lon, data[0].get('display_name', query)
        except requests.exceptions.ConnectionError:
            _logger.warning("Geocoding: no se pudo conectar a Nominatim (sin red o DNS). query=%s", query)
            return None
        except requests.exceptions.Timeout:
            _logger.warning("Geocoding: timeout al contactar Nominatim. query=%s", query)
            return None
        except Exception as e:
            _logger.warning("Geocoding: error inesperado. query=%s error=%s", query, e)
            return None

    def _auto_geocode_silent(self):
        """Auto-geocode without recursion — writes coords via super() to avoid re-triggering write()."""
        try:
            parts = [p for p in [self.street, self.city,
                                  self.state_id.name if self.state_id else None,
                                  'Ecuador'] if p]
            if len(parts) < 2:
                return
            result = self._nominatim_search(', '.join(parts))
            if not result:
                result = self._nominatim_search(', '.join(parts), countrycodes='')
            if result:
                lat, lon, _ = result
                super(EstateProperty, self).write({'latitude': lat, 'longitude': lon})
        except Exception as e:
            _logger.warning("_auto_geocode_silent failed: %s", e)

    def geocode_if_missing(self):
        """Called from JS on form load. Geocodes silently only when no coords exist yet.
        Returns True if coords were set, False if already existed or failed."""
        self.ensure_one()
        if self.latitude or self.longitude:
            return False
        self._auto_geocode_silent()
        return bool(self.latitude or self.longitude)

    def action_geocode_address(self):
        """Geocode the property address using Nominatim (OpenStreetMap) — free, no API key."""
        self.ensure_one()
        parts = [p for p in [self.street, self.city,
                             self.state_id.name if self.state_id else None,
                             'Ecuador'] if p]
        if not parts:
            raise UserError('Ingresa al menos la dirección y la ciudad para ubicar en el mapa.')
        query = ', '.join(parts)
        try:
            result = self._nominatim_search(query, countrycodes='ec')
            if not result:
                result = self._nominatim_search(query, countrycodes='')
            if result:
                lat, lon, display_name = result
                self.write({'latitude': lat, 'longitude': lon})
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Ubicación encontrada',
                        'message': f'Coordenadas: {lat:.5f}, {lon:.5f}',
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                # Retry at city level
                result2 = self._nominatim_search(f"{self.city}, Ecuador", countrycodes='ec')
                if result2:
                    lat, lon, _ = result2
                    self.write({'latitude': lat, 'longitude': lon})
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': 'Ubicación aproximada (ciudad)',
                            'message': f'No se encontró la calle exacta. Se usaron las coordenadas de {self.city}.',
                            'type': 'warning',
                            'sticky': False,
                        }
                    }
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Dirección no encontrada',
                        'message': f'No se pudo geocodificar: "{query}". Intenta con la dirección más específica.',
                        'type': 'warning',
                        'sticky': False,
                    }
                }
        except Exception as e:
            _logger.error("Geocoding error: %s", e)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error de geocodificación',
                    'message': str(e),
                    'type': 'danger',
                    'sticky': False,
                }
            }

    # --- Características ---
    price = fields.Float(string='Precio', tracking=True)
    bottom_price = fields.Float(string='Precio Tope (Mínimo)', tracking=True, help='El precio mínimo que el propietario está dispuesto a aceptar en una negociación.')
    area = fields.Float(string='Área (m²)', tracking=True)
    bedrooms = fields.Integer(string='Habitaciones', default=0, tracking=True)
    bathrooms = fields.Float(string='Baños', default=0.0, tracking=True)
    parking_spaces = fields.Integer(string='Parqueaderos', default=0, tracking=True)
    floor = fields.Integer(string='Piso/Planta')
    year_built = fields.Integer(string='Año de Construcción')
    
    # Etiquetas
    tag_ids = fields.Many2many(
        'estate.property.tag',
        'estate_property_tag_rel',
        'property_id', 'tag_id',
        string='Etiquetas')

    # Inteligencia Artificial
    ai_vision_description = fields.Text(string='Descripción IA Vision', readonly=True)

    # --- Mejora 14: Tour Virtual 360° ---
    tour_360_url = fields.Char(
        string='URL Tour 360°',
        help='URL de imagen equirectangular 360° o tour externo (Matterport, etc.). Se mostrará con Pannellum.js en el portal.')
    tour_360_active = fields.Boolean(
        string='Tour 360° Activo', default=False,
        help='Activa el visor 360° en el portal público.')

    # --- Mejora 13: Calculadora de Plusvalía ---
    roi_appreciation_rate = fields.Float(
        string='Apreciación Anual Estimada (%)', default=5.0,
        help='Porcentaje de plusvalía anual esperado. Promedio Ecuador: 5-8%.')
    roi_5year_value = fields.Float(
        string='Valor Estimado a 5 Años ($)', compute='_compute_roi', store=True)

    # --- AVM (Automated Valuation Model) ---
    avm_estimated_price = fields.Float(
        string='Valor M. Estimado (AVM)', readonly=True, tracking=True,
        help='Precio estimado por el Modelo Automático de Valoración (AVM) basado en ventas comparables en la misma ciudad y tipo de propiedad.')
    avm_last_calculated = fields.Datetime(
        string='Último AVM', readonly=True,
        help='Fecha y hora en que se calculó por última vez el valor estimado.')
    avm_status = fields.Selection([
        ('fair', 'Justo (Alineado al Mercado)'),
        ('high', 'Sobrevalorado'),
        ('low', 'Subestimado/Oportunidad'),
        ('insufficient', 'Datos Insuficientes')
    ], string='Estado AVM', compute='_compute_avm_status', store=True,
        help='Compara el precio de publicación con el valor estimado por el AVM. "Justo" = diferencia < 10%, "Sobrevalorado" = precio > AVM en más del 10%, "Subestimado" = precio < AVM en más del 10%.')
    # Mejora 6: AVM con comparables
    avm_comparable_count = fields.Integer(
        string='Comparables AVM', readonly=True,
        help='Número de propiedades similares usadas para calcular el AVM.')
    avm_confidence = fields.Selection([
        ('high', 'Alta (10+ comparables)'),
        ('medium', 'Media (3-9 comparables)'),
        ('low', 'Baja (1-2 comparables)'),
        ('none', 'Sin datos'),
    ], string='Confianza AVM', compute='_compute_avm_confidence', store=True)
    avm_price_trend = fields.Char(
        string='Tendencia de Precio', readonly=True,
        help='Tendencia del precio promedio en la zona en los últimos 6 meses.')

    # --- Predicción de Tiempo de Venta ---
    predicted_days_on_market = fields.Integer(
        string='Días Estimados en Mercado', compute='_compute_predicted_days', store=True,
        help='Basado en el promedio de propiedades similares vendidas en la misma ciudad y tipo.')

    # --- Property Score (0-100) ---
    property_score = fields.Integer(
        string='Puntuación de la Propiedad', compute='_compute_property_score', store=True,
        help='Puntuación de 0 a 100 que evalúa la calidad del expediente. Factores: precio alineado al mercado (+30), imágenes cargadas (+20), descripción completa (+10), precio mínimo definido (+10), propiedad visitada (+15), días en mercado razonables (+15). Mayor puntaje = más atractiva para compradores.')
    property_score_label = fields.Char(
        string='Nivel de Puntuación', compute='_compute_property_score', store=True,
        help='Clasificación del puntaje: Excelente (80+), Buena (60-79), Regular (40-59), Débil (<40).')

    # --- Fase 1: Captación y Exclusividad ---
    capture_sheet = fields.Binary(
        string='Hoja de Captación', attachment=True,
        help='Documento escaneado o PDF de la hoja de captación original.')
    capture_sheet_filename = fields.Char(string='Nombre del Archivo de Captación')
    capture_is_pdf = fields.Boolean(compute='_compute_capture_is_pdf')

    @api.depends('capture_sheet_filename')
    def _compute_capture_is_pdf(self):
        for rec in self:
            rec.capture_is_pdf = bool(rec.capture_sheet_filename and rec.capture_sheet_filename.lower().endswith('.pdf'))
    is_exclusive = fields.Boolean(
        string='En Exclusividad', default=False, tracking=True,
        help='Indica si la propiedad fue captada bajo contrato de exclusividad.')
    exclusive_user_id = fields.Many2one(
        'res.users', string='Asesor Responsable (Captador)', tracking=True,
        help='El asesor que captó la exclusividad de esta propiedad.')

    # --- Terreno / Solar ---
    is_land_type = fields.Boolean(
        string='Es Tipo Terreno',
        compute='_compute_is_land_type',
        store=False,
    )
    has_iprus = fields.Boolean(
        string='Tiene IPRUS', default=False, tracking=True,
        help='Informe de Regulación Metropolitana (IPRUS) emitido por el municipio para este terreno.')
    iprus_number = fields.Char(
        string='N° IPRUS', tracking=True,
        help='Número o código del documento IPRUS.')


    @api.depends('property_type_id', 'property_type_id.name')
    def _compute_is_land_type(self):
        _LAND_KEYWORDS = ('terreno', 'solar', 'lote', 'parcela', 'predio', 'campo')
        for rec in self:
            name = (rec.property_type_id.name or '').lower()
            rec.is_land_type = any(k in name for k in _LAND_KEYWORDS)

    @api.depends('avm_comparable_count')
    def _compute_avm_confidence(self):
        for rec in self:
            n = rec.avm_comparable_count or 0
            if n >= 10:
                rec.avm_confidence = 'high'
            elif n >= 3:
                rec.avm_confidence = 'medium'
            elif n >= 1:
                rec.avm_confidence = 'low'
            else:
                rec.avm_confidence = 'none'

    def action_recalculate_avm(self):
        """Mejora 6: Recalcula AVM con comparables reales y actualiza confianza."""
        from datetime import timedelta
        for prop in self:
            if not prop.property_type_id or not prop.city:
                continue
            six_months_ago = fields.Date.today() - timedelta(days=180)
            min_area = (prop.area or 0) * 0.85
            max_area = (prop.area or 0) * 1.15
            domain = [
                ('state', '=', 'sold'),
                ('property_type_id', '=', prop.property_type_id.id),
                ('city', 'ilike', prop.city),
                ('price', '>', 0),
                ('date_sold', '>=', six_months_ago),
            ]
            if prop.area and prop.area > 0:
                domain += [('area', '>=', min_area), ('area', '<=', max_area)]
            comparables = self.search(domain)
            if prop.id and isinstance(prop.id, int):
                comparables = comparables.filtered(lambda c: c.id != prop.id)
            if comparables:
                prices_per_m2 = [c.price / c.area for c in comparables if c.area and c.area > 0]
                if prices_per_m2:
                    avg_price_m2 = sum(prices_per_m2) / len(prices_per_m2)
                    estimated = avg_price_m2 * (prop.area or 1)
                    # Trend: compare first vs second half
                    half = len(comparables) // 2
                    if half > 0:
                        sorted_comps = comparables.sorted('date_sold')
                        first_half = sorted_comps[:half]
                        second_half = sorted_comps[half:]
                        avg_first = sum(c.price for c in first_half) / len(first_half)
                        avg_second = sum(c.price for c in second_half) / len(second_half)
                        if avg_second > avg_first * 1.03:
                            trend = 'Subiendo (+{:.1f}%)'.format(((avg_second/avg_first)-1)*100)
                        elif avg_second < avg_first * 0.97:
                            trend = 'Bajando ({:.1f}%)'.format(((avg_second/avg_first)-1)*100)
                        else:
                            trend = 'Estable'
                    else:
                        trend = 'Estable'
                    prop.write({
                        'avm_estimated_price': int(estimated * 100) / 100.0,
                        'avm_comparable_count': len(comparables),
                        'avm_price_trend': trend,
                        'avm_last_calculated': fields.Datetime.now(),
                    })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'AVM Recalculado',
                'message': 'El valor de mercado fue actualizado con comparables reales.',
                'type': 'success', 'sticky': False,
            }
        }

    @api.depends('price', 'avm_estimated_price')
    def _compute_avm_status(self):
        for rec in self:
            if not rec.avm_estimated_price or rec.avm_estimated_price == 0:
                rec.avm_status = 'insufficient'
                continue
                
            variance = (rec.price - rec.avm_estimated_price) / rec.avm_estimated_price
            if variance > 0.10: # > 10% more
                rec.avm_status = 'high'
            elif variance < -0.10: # < -10% less
                rec.avm_status = 'low'
            else:
                rec.avm_status = 'fair'

    @api.depends('property_type_id', 'city', 'state')
    def _compute_predicted_days(self):
        for rec in self:
            if not rec.property_type_id:
                rec.predicted_days_on_market = 0
                continue
            base_domain = [
                ('state', '=', 'sold'),
                ('property_type_id', '=', rec.property_type_id.id),
                ('days_on_market', '>', 0),
            ]
            if rec.id and isinstance(rec.id, int):
                base_domain.append(('id', '!=', rec.id))
            domain = base_domain + [('city', 'ilike', rec.city)] if rec.city else base_domain
            comparables = self.env['estate.property'].search(domain, limit=15)
            if not comparables and rec.city:
                comparables = self.env['estate.property'].search(domain, limit=15)
            if comparables:
                days_list = comparables.mapped('days_on_market')
                rec.predicted_days_on_market = int(sum(days_list) / len(days_list))
            else:
                rec.predicted_days_on_market = 0

    @api.depends('image_main', 'image_ids', 'description', 'wp_published',
                 'meeting_count', 'days_on_market', 'avm_status')
    def _compute_property_score(self):
        import re
        for rec in self:
            score = 0
            if rec.avm_status == 'fair':
                score += 33
            elif rec.avm_status == 'low':
                score += 43
            elif rec.avm_status == 'high':
               if rec.document_ids:
                score += min(len(rec.document_ids) * 5, 15)
            # Bonuses
            if rec.tour_360_active:
                score += 10
            if rec.capture_sheet:
                score += 5
            
            score = min(score, 100)
            text = re.sub(r'<[^>]+>', '', rec.description or '')
            if len(text) > 200:
                score += 10
            if rec.wp_published:
                score += 10
            score += min(rec.meeting_count * 5, 15)
            if rec.days_on_market > 30:
                weeks_over = (rec.days_on_market - 30) // 7
                score -= min(weeks_over, 20)
            final = max(0, min(100, score))
            rec.property_score = final
            if final >= 80:
                rec.property_score_label = 'Excelente'
            elif final >= 60:
                rec.property_score_label = 'Bueno'
            elif final >= 40:
                rec.property_score_label = 'Regular'
            else:
                rec.property_score_label = 'Incompleto'

    def action_calculate_avm(self):
        """Calcula el valor óptimo basado en propiedades similares VENDIDAS"""
        self.ensure_one()
        # Buscar propiedades vendidas del mismo tipo. Si tiene ciudad, filtrar por ciudad también.
        domain = [
            ('state', '=', 'sold'),
            ('id', '!=', self.id),
            ('property_type_id', '=', self.property_type_id.id)
        ]
        if self.city:
            domain.append(('city', 'ilike', self.city))
            
        comparables = self.env['estate.property'].search(domain, order='date_sold desc', limit=20)
        
        if not comparables:
            # Fallback: Solo buscar por tipo inmobiliario si no hay en la ciudad
            domain.pop()
            comparables = self.env['estate.property'].search(domain, order='date_sold desc', limit=20)
            if not comparables:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'AVM: Datos Insuficientes',
                        'message': 'No hay suficientes propiedades vendidas similares para calcular el AVM.',
                        'type': 'warning',
                        'sticky': False,
                    }
                }
            
        import math
        from datetime import date as _date
        today = _date.today()
        weighted_price = 0.0
        weighted_area = 0.0
        total_weight = 0.0
        direct_weighted_price = 0.0

        for comp in comparables:
            age_days = (today - comp.date_sold).days if comp.date_sold else 365
            age_weight = math.exp(-age_days / 365.0)
            year_diff = abs((self.year_built or 2000) - (comp.year_built or 2000))
            year_factor = max(1.0 - year_diff * 0.005, 0.70)
            weight = age_weight * year_factor
            direct_weighted_price += comp.price * weight
            if comp.area and comp.area > 0:
                weighted_price += comp.price * weight
                weighted_area += comp.area * weight
            total_weight += weight

        if total_weight == 0:
            total_weight = len(comparables)
            direct_weighted_price = sum(c.price for c in comparables)

        if weighted_area > 0 and self.area and self.area > 0:
            avg_price_per_sqm = weighted_price / weighted_area
            estimated_price = avg_price_per_sqm * self.area
        else:
            estimated_price = direct_weighted_price / total_weight
            
        self.write({
            'avm_estimated_price': estimated_price,
            'avm_last_calculated': fields.Datetime.now()
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'AVM Calculado Exitosamente',
                'message': f"Basado en {len(comparables)} ventas históricas (ponderadas por antigüedad y año de construcción) el valor estimado es ${estimated_price:,.2f}.",
                'type': 'success',
                'sticky': False,
            }
        }

    # --- Comisiones ---
    commission_percentage = fields.Float(string='Porcentaje Comisión (%)', default=5.0)
    commission_amount = fields.Float(
        string='Monto Comisión', compute='_compute_commission_amount', store=True)

    # --- Estado ---
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('available', 'Disponible'),
        ('reserved', 'Reservado'),
        ('sold', 'Vendido'),
        ('rented', 'Arrendado'),
    ], string='Estado', default='draft', tracking=True, required=True)

    active = fields.Boolean(string='Activo', default=True)

    # --- Métricas de Venta ---
    date_listed = fields.Date(string='Fecha de Publicación', tracking=True,
        help='Fecha en que la propiedad se puso en el mercado.')
    date_sold = fields.Date(string='Fecha de Venta', tracking=True,
        help='Fecha en que se cerró la venta.')
    days_on_market = fields.Integer(
        string='Días en el Mercado', compute='_compute_days_on_market', store=True,
        help='Cantidad de días que la propiedad estuvo disponible antes de venderse.')
    sold_by = fields.Selection([
        ('agency', 'Vendido por la Agencia'),
        ('owner', 'Vendido por el Dueño'),
    ], string='¿Quién Vendió?', tracking=True)

    # --- Arriendo ---
    date_rented = fields.Date(string='Fecha de Arrendamiento', tracking=True)
    tenant_id = fields.Many2one('res.partner', string='Arrendatario', tracking=True)
    rental_price = fields.Float(string='Canon Mensual de Arriendo ($)', tracking=True,
        help='Valor mensual del arriendo. La comisión se cobra solo sobre el primer mes.')

    # --- Contratos ---
    contract_end_date = fields.Date(string='Vencimiento de Contrato', tracking=True,
        help='Fecha en que vence el contrato de exclusividad.')
    contract_reminder_days = fields.Integer(
        string='Días para Recordatorio', default=30,
        help='Cuántos días antes del vencimiento se generará una alerta.')

    @api.depends('date_listed', 'date_sold')
    def _compute_days_on_market(self):
        for rec in self:
            if rec.date_listed and rec.date_sold:
                rec.days_on_market = (rec.date_sold - rec.date_listed).days
            elif rec.date_listed:
                rec.days_on_market = (fields.Date.today() - rec.date_listed).days
            else:
                rec.days_on_market = 0

    # --- Imágenes ---
    image_ids = fields.One2many(
        'estate.property.image', 'property_id', string='Imágenes')
    gallery_ids = fields.Many2many(
        'ir.attachment', string='Galería de Imágenes',
        help='Arrastra imágenes aquí para subirlas directamente.')
    image_main = fields.Binary(string='Imagen Principal')

    # --- WordPress ---
    wp_post_id = fields.Integer(
        string='WordPress Post ID', readonly=True, index='btree_not_null')
    wp_published = fields.Boolean(string='Publicado en WordPress', default=False)
    wp_post_id_backup = fields.Integer(
        string='WordPress Post ID (Backup)', readonly=True,
        help='Almacena el Post ID original al desvincular, permitiendo re-enlazar sin perder la referencia.')
    wp_unlinked = fields.Boolean(
        string='Desvinculado de WordPress', default=False,
        help='Indica que esta propiedad estaba enlazada a WordPress pero fue desvinculada. El Post ID original se conserva en el backup.')

    # --- Sectores relacionados (para CRM matching y búsqueda) ---
    sector_keywords = fields.Char(
        string='Sectores Relacionados',
        help='Sectores y barrios relacionados separados por coma. Ej: Paccha, El Valle, Ricaurte'
    )
    wp_publish_location = fields.Boolean(
        string='Publicar Ubicación en WP',
        default=True,
        help='Si está activo, la dirección exacta y el mapa se publican en WordPress. '
             'Desactívalo si el propietario no quiere revelar la dirección pública.'
    )

    # --- Relaciones y Ventas ---
    owner_id = fields.Many2one('res.partner', string='Propietario', tracking=True)
    proxy_id = fields.Many2one('res.partner', string='Apoderado', tracking=True,
                               help='Persona autorizada para actuar en nombre del propietario.')
    buyer_id = fields.Many2one('res.partner', string='Comprador', tracking=True)
    user_id = fields.Many2one('res.users', string='Asesor Responsable', default=lambda self: self.env.user, tracking=True)
    co_user_id = fields.Many2one('res.users', string='Co-Asesor', tracking=True,
                                 help='Segundo asesor que colabora en esta propiedad.')
    commission_split_pct = fields.Float(
        string='Split Co-Asesor (%)', default=50.0,
        help='Porcentaje de la comisión que corresponde al Co-Asesor (el resto es del Asesor Responsable).')

    # --- Negocio Cerrado (datos del cierre, capturados al vender) ---
    deal_deadline = fields.Date(
        string='Fecha Máxima de Cumplimiento',
        help='Fecha límite para completar la escritura / cierre definitivo.')
    deal_earnest_amount = fields.Float(
        string='Seña / Arras ($)',
        help='Monto entregado como reserva al cerrar el negocio.')
    deal_payment_type = fields.Selection([
        ('cash', 'Contado'),
        ('mortgage', 'Hipotecario (BIESS/Banco)'),
        ('owner', 'Financiamiento del Vendedor'),
        ('mixed', 'Mixto'),
        ('other', 'Otro'),
    ], string='Forma de Pago', default='cash')
    deal_payment_details = fields.Text(
        string='Detalles del Negocio',
        help='Condiciones de pago, plazos, observaciones del acuerdo.')
    deal_credit_institution = fields.Char(string='Institución de Crédito')
    deal_credit_advisor = fields.Char(string='Asesor de Crédito')
    deal_credit_advisor_phone = fields.Char(string='Teléfono Asesor de Crédito')
    deal_observations = fields.Text(string='Observaciones del Negocio')

    # --- Calculadora de Hipoteca ---
    mortgage_down_payment_pct = fields.Float(string='Entrada (%)', default=20.0,
                                             help='Porcentaje de entrada sobre el precio.')
    mortgage_rate = fields.Float(string='Tasa de Interés Anual (%)', default=9.5,
                                 help='Tasa referencial BIESS/banco. Promedio Ecuador: 9-11%.')
    mortgage_term_years = fields.Integer(string='Plazo (años)', default=20)
    mortgage_down_payment = fields.Float(string='Valor Entrada ($)', compute='_compute_mortgage', store=True)
    mortgage_loan_amount = fields.Float(string='Monto a Financiar ($)', compute='_compute_mortgage', store=True)
    mortgage_monthly_payment = fields.Float(string='Cuota Mensual Estimada ($)', compute='_compute_mortgage', store=True)

    # --- Historial de Precios ---
    price_history_ids = fields.One2many('estate.property.price.history', 'property_id', string='Historial de Precios')
    price_history_count = fields.Integer(string='Cambios de Precio', compute='_compute_price_history_count')

    # --- Ofertas ---
    offer_ids = fields.One2many('estate.property.offer', 'property_id', string='Ofertas')
    offer_count = fields.Integer(string='N° Ofertas', compute='_compute_offer_count')
    best_offer = fields.Float(string='Mejor Oferta', compute='_compute_best_offer', store=True)

    # --- Gastos ---
    expense_ids = fields.One2many('estate.property.expense', 'property_id', string='Gastos')
    expense_count = fields.Integer(string='N° Gastos', compute='_compute_expense_count')
    total_expenses = fields.Float(string='Total Gastos', compute='_compute_total_expenses', store=True)

    # --- Tasaciones ---
    appraisal_ids = fields.One2many('estate.appraisal', 'property_id', string='Tasaciones')
    appraisal_count = fields.Integer(string='N° Tasaciones', compute='_compute_appraisal_count')

    # --- Citas / Agenda ---
    meeting_count = fields.Integer(string='Citas', compute='_compute_meeting_count')
    commission_ids = fields.One2many('estate.commission', 'property_id', string='Historial de Comisiones')
    commission_count = fields.Integer(string='N° Comisiones', compute='_compute_commission_count')

    advisor_fb_post_ids = fields.One2many(
        'estate.advisor.fb.post', 'property_id', string='Posts Personales de Asesores')
    advisor_fb_post_count = fields.Integer(
        string='Posts FB', compute='_compute_advisor_fb_post_count')

    @api.depends('price', 'mortgage_down_payment_pct', 'mortgage_rate', 'mortgage_term_years')
    def _compute_mortgage(self):
        import math
        for rec in self:
            price = rec.price or 0.0
            down_pct = (rec.mortgage_down_payment_pct or 20.0) / 100.0
            annual_rate = (rec.mortgage_rate or 9.5) / 100.0
            years = rec.mortgage_term_years or 20
            down = price * down_pct
            loan = price - down
            rec.mortgage_down_payment = down
            rec.mortgage_loan_amount = loan
            if loan > 0 and annual_rate > 0 and years > 0:
                monthly_rate = annual_rate / 12
                n = years * 12
                rec.mortgage_monthly_payment = loan * (monthly_rate * (1 + monthly_rate) ** n) / ((1 + monthly_rate) ** n - 1)
            else:
                rec.mortgage_monthly_payment = 0.0

    def _compute_price_history_count(self):
        for rec in self:
            rec.price_history_count = len(rec.price_history_ids)

    @api.depends('offer_ids')
    def _compute_offer_count(self):
        for rec in self:
            rec.offer_count = len(rec.offer_ids)

    @api.depends('offer_ids.offer_amount', 'offer_ids.state')
    def _compute_best_offer(self):
        for rec in self:
            active_offers = rec.offer_ids.filtered(lambda o: o.state not in ('rejected', 'expired'))
            rec.best_offer = max(active_offers.mapped('offer_amount'), default=0.0)

    @api.depends('expense_ids')
    def _compute_expense_count(self):
        for rec in self:
            rec.expense_count = len(rec.expense_ids)

    @api.depends('expense_ids.amount', 'expense_ids.state')
    def _compute_total_expenses(self):
        for rec in self:
            paid = rec.expense_ids.filtered(lambda e: e.state == 'paid')
            rec.total_expenses = sum(paid.mapped('amount'))

    def _compute_appraisal_count(self):
        for rec in self:
            rec.appraisal_count = len(rec.appraisal_ids)

    def action_view_price_history(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Historial de Precios — {self.title}',
            'res_model': 'estate.property.price.history',
            'view_mode': 'list,form',
            'domain': [('property_id', '=', self.id)],
            'context': {'default_property_id': self.id},
        }

    def action_view_offers(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Ofertas — {self.title}',
            'res_model': 'estate.property.offer',
            'view_mode': 'list,form',
            'domain': [('property_id', '=', self.id)],
            'context': {'default_property_id': self.id},
        }

    def action_view_expenses(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Gastos — {self.title}',
            'res_model': 'estate.property.expense',
            'view_mode': 'list,form',
            'domain': [('property_id', '=', self.id)],
            'context': {'default_property_id': self.id},
        }

    @api.depends('commission_ids')
    def _compute_commission_count(self):
        for rec in self:
            rec.commission_count = len(rec.commission_ids)

    def action_view_commissions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Comisiones — {self.title}',
            'res_model': 'estate.commission',
            'view_mode': 'list,form',
            'domain': [('property_id', '=', self.id)],
            'context': {'default_property_id': self.id},
        }

    def action_view_appraisals(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Tasaciones — {self.title}',
            'res_model': 'estate.appraisal',
            'view_mode': 'list,form',
            'domain': [('property_id', '=', self.id)],
            'context': {'default_property_id': self.id},
        }

    def _record_price_change(self, old_price, new_price, reason='market'):
        """Registra un cambio de precio en el historial."""
        if old_price != new_price:
            self.env['estate.property.price.history'].create({
                'property_id': self.id,
                'old_price': old_price,
                'new_price': new_price,
                'change_reason': reason,
            })

    def _compute_meeting_count(self):
        for rec in self:
            rec.meeting_count = self.env['calendar.event'].sudo().search_count([('property_id', '=', rec.id)])

    def _compute_advisor_fb_post_count(self):
        for rec in self:
            rec.advisor_fb_post_count = self.env['estate.advisor.fb.post'].search_count([('property_id', '=', rec.id)])

    def action_view_personal_posts(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Publicaciones personales — {self.title or self.name}',
            'res_model': 'estate.advisor.fb.post',
            'view_mode': 'list,form',
            'domain': [('property_id', '=', self.id)],
            'context': {
                'default_property_id': self.id,
                'default_user_id': self.env.user.id,
            },
        }

    def action_log_personal_post_fb(self):
        self.ensure_one()
        self.env['estate.advisor.fb.post'].create({
            'property_id': self.id,
            'user_id': self.env.user.id,
            'platform': 'facebook',
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Publicación registrada',
                'message': f'Se registró tu publicación en Facebook para {self.title or self.name}.',
                'type': 'success',
                'sticky': False,
            },
        }

    def action_log_personal_post_ig(self):
        self.ensure_one()
        self.env['estate.advisor.fb.post'].create({
            'property_id': self.id,
            'user_id': self.env.user.id,
            'platform': 'instagram',
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Publicación registrada',
                'message': f'Se registró tu publicación en Instagram para {self.title or self.name}.',
                'type': 'success',
                'sticky': False,
            },
        }

    def action_view_meetings(self):
        self.ensure_one()
        action = self.env.ref('calendar.action_calendar_event').read()[0]
        action['domain'] = [('property_id', '=', self.id)]
        action['context'] = {
            'default_property_id': self.id,
            'default_name': f"Cita para: {self.title}",
        }
        return action

    # --- Órdenes de Venta ---
    sale_order_ids = fields.One2many('sale.order', 'property_id', string='Órdenes de Venta')
    sale_count = fields.Integer(string='Ventas', compute='_compute_sale_count')

    def _compute_sale_count(self):
        for rec in self:
            rec.sale_count = self.env['sale.order'].sudo().search_count([('property_id', '=', rec.id)])

    def action_view_sale_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Órdenes de Venta — {self.title}',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [('property_id', '=', self.id)],
            'context': {
                'default_property_id': self.id,
                'default_estate_transaction_type': 'sale',
                'default_partner_id': (self.buyer_id.id if self.buyer_id else False) or (self.owner_id.id if self.owner_id else False),
            },
        }

    def action_create_sale_order(self):
        self.ensure_one()
        partner = self.buyer_id or self.owner_id
        if not partner:
            raise UserError('Asigna un Comprador o Propietario a la propiedad antes de crear la orden de venta.')
        # Buscar lead activo de CRM del mismo comprador para vincularlo
        active_lead = self.env['crm.lead'].search([
            ('partner_id', '=', partner.id),
            ('target_property_id', '=', self.id),
            ('type', '=', 'opportunity'),
            ('probability', '>', 0),
            ('probability', '<', 100),
        ], limit=1)
        if not active_lead:
            # Buscar por partner aunque no tenga la propiedad asignada
            active_lead = self.env['crm.lead'].search([
                ('partner_id', '=', partner.id),
                ('type', '=', 'opportunity'),
                ('probability', '>', 0),
                ('probability', '<', 100),
            ], limit=1)
        order_vals = {
            'partner_id': partner.id,
            'property_id': self.id,
            'estate_transaction_type': 'sale',
            'lead_id': active_lead.id if active_lead else False,
        }
        if self.product_id:
            order_vals['order_line'] = [(0, 0, {
                'product_id': self.product_id.id,
                'name': self.title,
                'price_unit': self.price,
                'product_uom_qty': 1,
            })]
        order = self.env['sale.order'].create(order_vals)
        self.message_post(body=f'Orden de venta <b>{order.name}</b> creada desde esta propiedad.')
        if active_lead:
            active_lead.message_post(
                body=f'Orden de venta <b>{order.name}</b> creada para la propiedad '
                     f'<b>{self.title}</b> por ${self.price:,.2f}.')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Orden de Venta',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': order.id,
        }

    # --- Facturas vinculadas ---
    invoice_ids = fields.One2many('account.move', 'property_id', string='Facturas Emitidas')
    property_invoice_count = fields.Integer(string='Nº Facturas', compute='_compute_property_invoice_count')

    def _compute_property_invoice_count(self):
        for rec in self:
            rec.property_invoice_count = self.env['account.move'].sudo().search_count([
                ('property_id', '=', rec.id),
                ('move_type', '=', 'out_invoice'),
            ])

    def action_view_property_invoices(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Facturas — {self.title}',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('property_id', '=', self.id), ('move_type', '=', 'out_invoice')],
            'context': {
                'default_property_id': self.id,
                'default_move_type': 'out_invoice',
            },
        }
    # --- Código QR ---
    qr_image = fields.Binary(string='Código QR', compute='_compute_qr_image', store=True)

    @api.depends('title', 'price', 'map_url')
    def _compute_qr_image(self):
        for rec in self:
            if rec.title:
                qr_data = f"Propiedad: {rec.title}\nPrecio: ${rec.price:,.2f}\nUbicación: {rec.map_url or 'Consultar'}"
                qr = qrcode.QRCode(version=1, box_size=5, border=4)
                qr.add_data(qr_data)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                temp = BytesIO()
                img.save(temp, format="PNG")
                rec.qr_image = base64.b64encode(temp.getvalue())
            else:
                rec.qr_image = False

    @api.depends('price', 'commission_percentage')
    def _compute_commission_amount(self):
        for rec in self:
            rec.commission_amount = (rec.price or 0.0) * (rec.commission_percentage / 100.0)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code('estate.property') or 'Nuevo'

        properties = super().create(vals_list)

        # Sincronizar automáticamente con un producto nativo de Odoo
        for prop in properties:
            if not prop.product_id:
                product_vals = {
                    'name': f"Inmueble: {prop.title}",
                    'type': 'service',  # Servicio para no requerir control de inventario
                    'list_price': prop.price,
                    'default_code': prop.name,
                }
                product = self.env['product.template'].sudo().create(product_vals)
                prop.product_id = product.id
            # Precio inicial en historial
            if prop.price:
                self.env['estate.property.price.history'].create({
                    'property_id': prop.id,
                    'old_price': 0,
                    'new_price': prop.price,
                    'change_reason': 'initial',
                })
            # Auto-etiquetado de contactos
            if prop.owner_id:
                prop.owner_id._apply_estate_category('estate_management.partner_category_owner')
                if not prop.owner_id.is_property_owner:
                    prop.owner_id.sudo().write({'is_property_owner': True})
            if prop.buyer_id:
                prop.buyer_id._apply_estate_category('estate_management.partner_category_buyer')
            # Auto-publicar en WordPress si se creó con wp_published=True
            if prop.wp_published and hasattr(prop, '_trigger_wp_sync_async'):
                prop._trigger_wp_sync_async()
            # Auto-geocodificar si hay dirección pero sin coordenadas
            if prop.street and prop.city and not prop.latitude:
                try:
                    prop._auto_geocode_silent()
                except Exception:
                    pass
            # Auto-completar código postal
            if not prop.zip_code and prop.city:
                code = self._EC_POSTAL_CODES.get(prop.city.lower().strip(), '')
                if code:
                    super(EstateProperty, prop).write({'zip_code': code})

        # Convertir imágenes subidas en lote (gallery_ids) a image_ids
        properties._sync_gallery_to_images()

        return properties

    def _sync_gallery_to_images(self):
        """Convierte los adjuntos subidos de golpe en la zona de carga rápida
        (gallery_ids, widget many2many_binary) en registros estate.property.image.

        image_ids es la fuente canónica que usan WordPress, la IA y los reportes;
        gallery_ids es solo una zona de carga múltiple intuitiva. Tras convertir,
        se limpia la zona y se eliminan los adjuntos temporales."""
        Image = self.env['estate.property.image']
        for prop in self:
            if not prop.gallery_ids:
                continue
            base = Image.search_count([('property_id', '=', prop.id)])
            new_imgs = []
            for idx, att in enumerate(prop.gallery_ids, 1):
                if not att.datas:
                    continue
                clean_name = (att.name or f'Imagen {base + idx}').rsplit('.', 1)[0]
                new_imgs.append({
                    'property_id': prop.id,
                    'image': att.datas,
                    'name': clean_name,
                    'sequence': (base + idx) * 10,
                })
            if new_imgs:
                Image.create(new_imgs)
            # Limpiar zona de carga + borrar adjuntos temporales (guard anti-recursión)
            atts = prop.gallery_ids
            prop.with_context(_syncing_gallery=True).gallery_ids = [(5, 0, 0)]
            atts.sudo().unlink()

    @api.constrains('year_built')
    def _check_year_built(self):
        import datetime
        current_year = datetime.date.today().year
        for rec in self:
            if rec.year_built and rec.year_built > current_year:
                raise UserError(f'El año de construcción ({rec.year_built}) no puede ser mayor al año actual ({current_year}).')
            if rec.year_built and rec.year_built < 1800:
                raise UserError(f'El año de construcción ({rec.year_built}) no es válido.')

    @api.constrains('bottom_price', 'price')
    def _check_bottom_price(self):
        for rec in self:
            if rec.bottom_price and rec.price and rec.bottom_price >= rec.price:
                raise UserError(
                    f'El precio mínimo aceptable (${rec.bottom_price:,.2f}) debe ser menor al precio de publicación (${rec.price:,.2f}).'
                )

    @api.constrains('commission_split_pct')
    def _check_commission_split(self):
        for rec in self:
            if not (0 <= rec.commission_split_pct <= 100):
                raise UserError('El porcentaje de split del Co-Asesor debe estar entre 0% y 100%.')

    # ── Onchange warnings (avisan al usuario antes del guardado) ──────────────
    @api.onchange('year_built')
    def _onchange_year_built_warn(self):
        import datetime
        current_year = datetime.date.today().year
        if self.year_built and (self.year_built > current_year or self.year_built < 1800):
            return {'warning': {
                'title': 'Año de construcción inválido',
                'message': f'El año {self.year_built} no será aceptado al guardar. '
                           f'Debe estar entre 1800 y {current_year}.',
            }}

    @api.onchange('bottom_price', 'price')
    def _onchange_bottom_price_warn(self):
        if self.bottom_price and self.price and self.bottom_price >= self.price:
            return {'warning': {
                'title': 'Precio mínimo inválido',
                'message': (
                    f'El precio mínimo aceptable (${self.bottom_price:,.2f}) debe ser '
                    f'MENOR al precio de publicación (${self.price:,.2f}). '
                    f'Ajuste el valor antes de guardar.'
                ),
            }}

    @api.onchange('commission_split_pct')
    def _onchange_commission_split_warn(self):
        if self.commission_split_pct and not (0 <= self.commission_split_pct <= 100):
            return {'warning': {
                'title': 'Comisión fuera de rango',
                'message': 'El % de split del Co-Asesor debe estar entre 0 y 100.',
            }}

    # Campos que, cuando cambian, deben re-sincronizar la propiedad en WordPress
    _WP_SYNC_FIELDS = {
        'title', 'description', 'price', 'area', 'bedrooms', 'bathrooms',
        'parking_spaces', 'street', 'city', 'state_id', 'country_id', 'zip_code',
        'latitude', 'longitude', 'property_type_id', 'state', 'image_main',
        'image_ids', 'year_built', 'wp_publish_location', 'sector_keywords',
    }

    def write(self, vals):
        # Capturar precios ANTES del write para el historial
        old_prices = {}
        if 'price' in vals:
            old_prices = {prop.id: prop.price for prop in self}

        res = super().write(vals)
        # Convertir imágenes subidas en lote (gallery_ids) a image_ids
        if 'gallery_ids' in vals and not self.env.context.get('_syncing_gallery'):
            self._sync_gallery_to_images()
        # Sincronizar actualizaciones hacia product.template
        for prop in self:
            if prop.product_id:
                product_vals = {}
                if 'title' in vals:
                    product_vals['name'] = f"Inmueble: {vals['title']}"
                if 'price' in vals:
                    product_vals['list_price'] = vals['price']
                if product_vals:
                    prop.product_id.sudo().write(product_vals)
        # Auto-sync a WordPress si la propiedad ya está publicada y cambia
        # algún campo relevante. Guard no_wp_sync para evitar bucles.
        # Se ejecuta en un hilo de fondo para no bloquear el guardado.
        if not self.env.context.get('no_wp_sync'):
            changed_wp_fields = self._WP_SYNC_FIELDS.intersection(vals.keys())
            if changed_wp_fields:
                for prop in self:
                    wp_pub = getattr(prop, 'wp_published', False)
                    wp_id = getattr(prop, 'wp_post_id', 0)
                    if wp_pub and wp_id and hasattr(prop, '_trigger_wp_sync_async'):
                        prop._trigger_wp_sync_async()
        # Historial de precios (usando precios capturados antes del write)
        if old_prices:
            new_price = vals['price']
            for prop in self:
                old_price = old_prices.get(prop.id, 0)
                if old_price and old_price != new_price:
                    reason = 'reduction' if new_price < old_price else 'increase'
                    prop._record_price_change(old_price, new_price, reason)

        # Auto-etiquetado cuando cambia propietario o comprador
        if 'owner_id' in vals:
            for prop in self:
                if prop.owner_id:
                    prop.owner_id._apply_estate_category('estate_management.partner_category_owner')
                    if not prop.owner_id.is_property_owner:
                        prop.owner_id.sudo().write({'is_property_owner': True})
        if 'buyer_id' in vals:
            for prop in self:
                if prop.buyer_id:
                    prop.buyer_id._apply_estate_category('estate_management.partner_category_buyer')
        # Auto-geocodificar cuando cambia la dirección (pero no cuando solo cambian coords)
        _ADDRESS_FIELDS = frozenset({'street', 'city', 'state_id', 'country_id'})
        _COORD_FIELDS = frozenset({'latitude', 'longitude'})
        if (not self.env.context.get('no_geocode')
                and _ADDRESS_FIELDS.intersection(vals)
                and not _COORD_FIELDS.intersection(vals)):
            for prop in self:
                if prop.street and prop.city:
                    try:
                        prop._auto_geocode_silent()
                    except Exception:
                        pass
        return res

    def unlink(self):
        non_draft = self.filtered(lambda p: p.state not in ('draft',))
        # El asesor solo puede eliminar propiedades en Borrador. Gerencia,
        # Marketing y Administración pueden eliminar en cualquier estado.
        puede_todo = self.env.user.has_group('estate_management.estate_group_manager')
        if non_draft and not puede_todo:
            titles = ', '.join(non_draft.mapped('title') or non_draft.mapped('name'))
            raise UserError(
                f"Un asesor solo puede eliminar propiedades en Borrador. Estas ya están "
                f"publicadas o vendidas: {titles}.\n\nUsa 'Volver a Borrador' primero, "
                f"o pide a Gerencia/Administración que la elimine."
            )
        return super().unlink()

    def action_publish(self):
        """Borrador → Disponible: primera publicación al mercado."""
        for prop in self:
            if not prop.date_listed:
                prop.write({'date_listed': fields.Date.today()})
            prop.write({'state': 'available'})
            prop.message_post(
                body='Propiedad publicada en el mercado.',
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )

    def action_set_draft(self):
        """Volver a borrador (desde Disponible o Reservado)."""
        for prop in self:
            prop.write({'state': 'draft'})
            prop.message_post(
                body='Propiedad guardada como borrador (retirada del mercado temporalmente).',
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )

    def action_set_available(self):
        for prop in self:
            active_contracts = self.env['estate.contract'].search_count([
                ('property_id', '=', prop.id),
                ('state', '=', 'active'),
            ])
            if active_contracts:
                raise UserError(
                    f'"{prop.title}" tiene {active_contracts} contrato(s) activo(s). '
                    f'Cancela o cierra los contratos antes de cambiar el estado a Disponible.'
                )
        self.write({'state': 'available'})

    def action_relist(self):
        """Re-listar una propiedad ya vendida/arrendada para volver al mercado."""
        self.ensure_one()
        active_contracts = self.env['estate.contract'].search_count([
            ('property_id', '=', self.id),
            ('state', '=', 'active'),
        ])
        if active_contracts:
            raise UserError(
                'No puedes re-listar esta propiedad porque tiene contratos activos. '
                'Cancela o cierra los contratos primero.'
            )
        self.write({
            'state': 'available',
            'buyer_id': False,
            'date_sold': False,
            'sold_by': False,
            'tenant_id': False,
            'date_rented': False,
        })
        self.message_post(
            body='Propiedad re-listada en el mercado. Datos de venta anteriores archivados.',
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )

    def action_set_reserved(self):
        for prop in self:
            if prop.state != 'available':
                raise UserError(
                    f'"{prop.title}" solo puede reservarse cuando está Disponible (estado actual: {dict(prop._fields["state"].selection)[prop.state]}).'
                )
        self.write({'state': 'reserved'})

    def action_open_sale_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Vender Propiedad',
            'res_model': 'estate.sale.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_property_id': self.id,
                'default_buyer_id': self.buyer_id.id or False,
                'default_sale_price': self.price or 0.0,
                'default_commission_pct': self.commission_percentage or 5.0,
            },
        }

    def action_set_sold(self):
        self.ensure_one()
        if self.state not in ('available', 'reserved'):
            raise UserError('Solo se puede marcar como Vendida una propiedad Disponible o Reservada.')

        # Despublicar de WordPress antes de cambiar el estado
        if self.wp_published and self.wp_post_id and hasattr(self, 'action_unpublish_wordpress'):
            try:
                self.action_unpublish_wordpress()
            except Exception as e:
                _logger.warning(
                    'WP unpublish automático al vender propiedad %s falló: %s', self.id, e)

        vals = {'state': 'sold'}
        if not self.date_sold:
            vals['date_sold'] = fields.Date.today()
        if not self.sold_by:
            vals['sold_by'] = 'agency'
        self.with_context(no_wp_sync=True).write(vals)
        self._create_commission_records('sale', self.commission_amount, self.price, self.commission_percentage)

    def action_set_rented(self):
        self.ensure_one()
        if self.state not in ('available', 'reserved'):
            raise UserError('Solo se puede arrendar una propiedad Disponible o Reservada.')
        if not self.rental_price:
            raise UserError('Debes ingresar el Canon Mensual de Arriendo antes de continuar.')

        if self.wp_published and self.wp_post_id and hasattr(self, 'action_unpublish_wordpress'):
            try:
                self.action_unpublish_wordpress()
            except Exception as e:
                _logger.warning('WP unpublish al arrendar propiedad %s falló: %s', self.id, e)

        vals = {'state': 'rented', 'offer_type': 'rent'}
        if not self.date_rented:
            vals['date_rented'] = fields.Date.today()
        self.with_context(no_wp_sync=True).write(vals)

        # Comisión solo del PRIMER mes de arriendo
        first_month_commission = self.rental_price * (self.commission_percentage / 100.0)
        self._create_commission_records('rent', first_month_commission, self.rental_price, self.commission_percentage)

    def _process_native_sale(self, buyer, price, commission_amount, commission_pct):
        """Crea y confirma la orden de venta nativa (sale.order) y genera +
        contabiliza la factura (account.move) para que la venta quede registrada
        en los módulos nativos de Ventas y Facturación. Devuelve (order, invoice).
        """
        self.ensure_one()
        order = invoice = False

        # Vincular lead activo del comprador si existe
        active_lead = self.env['crm.lead'].search([
            ('partner_id', '=', buyer.id),
            ('target_property_id', '=', self.id),
            ('type', '=', 'opportunity'),
            ('probability', '>', 0), ('probability', '<', 100),
        ], limit=1) or self.env['crm.lead'].search([
            ('partner_id', '=', buyer.id),
            ('type', '=', 'opportunity'),
            ('probability', '>', 0), ('probability', '<', 100),
        ], limit=1)

        try:
            order_vals = {
                'partner_id': buyer.id,
                'property_id': self.id,
                'estate_transaction_type': 'sale',
                'lead_id': active_lead.id if active_lead else False,
            }
            if self.product_id:
                order_vals['order_line'] = [(0, 0, {
                    'product_id': self.product_id.product_variant_id.id,
                    'name': self.title,
                    'price_unit': price,
                    'product_uom_qty': 1,
                })]
            order = self.env['sale.order'].create(order_vals)
            order.action_confirm()

            # Forzar entregado = pedido para que sea facturable con cualquier política
            for line in order.order_line:
                if not line.display_type:
                    line.qty_delivered = line.product_uom_qty

            # Generar y contabilizar la factura desde la orden
            if order.order_line:
                invoices = order._create_invoices()
                if invoices:
                    invoices.action_post()
                    invoice = invoices[:1]
        except Exception as e:
            _logger.error('Flujo nativo de venta falló para propiedad %s: %s', self.id, e)
            raise UserError(
                'No se pudo generar la orden/factura de la venta: %s\n\n'
                'La propiedad NO se marcó como vendida.' % str(e))

        return order, invoice

    def _create_commission_records(self, commission_type, total_amount, sale_price, pct):
        """Crea registros de comisión, dividiendo entre asesor y co-asesor si aplica."""
        today = fields.Date.today()
        if self.co_user_id and 0 < self.commission_split_pct < 100:
            co_ratio = self.commission_split_pct / 100.0
            co_amount = total_amount * co_ratio
            main_amount = total_amount * (1.0 - co_ratio)
            self.env['estate.commission'].create({
                'property_id': self.id,
                'user_id': self.user_id.id,
                'sale_amount': sale_price,
                'commission_pct': pct * (1.0 - co_ratio),
                'amount': main_amount,
                'type': commission_type,
                'date': today,
                'state': 'approved',
            })
            self.env['estate.commission'].create({
                'property_id': self.id,
                'user_id': self.co_user_id.id,
                'sale_amount': sale_price,
                'commission_pct': pct * co_ratio,
                'amount': co_amount,
                'type': commission_type,
                'date': today,
                'state': 'approved',
            })
            self.message_post(
                body=f'Comisión de ${total_amount:,.2f} dividida: '
                     f'{self.user_id.name} ${main_amount:,.2f} ({100-self.commission_split_pct:.0f}%) / '
                     f'{self.co_user_id.name} ${co_amount:,.2f} ({self.commission_split_pct:.0f}%)',
                message_type='comment', subtype_xmlid='mail.mt_note',
            )
        else:
            self.env['estate.commission'].create({
                'property_id': self.id,
                'user_id': self.user_id.id,
                'sale_amount': sale_price,
                'commission_pct': pct,
                'amount': total_amount,
                'type': commission_type,
                'date': today,
                'state': 'approved',
            })

    def action_create_invoice(self):
        self.ensure_one()
        if not self.buyer_id:
            raise UserError('Para facturar la propiedad, debes asignarle un Comprador.')
        
        product = self.product_id.product_variant_id if self.product_id else False
        
        lines = [(0, 0, {
            'product_id': product.id if product else False,
            'name': f"Venta de Inmueble: {self.title}",
            'price_unit': self.price,
            'quantity': 1,
            # El inmueble se factura SIN IVA por defecto (sin el 15%).
            'tax_ids': [(6, 0, [])],
        })]
        
        # Agregar una línea descriptiva con la Comisión calculada para trazabilidad
        if self.commission_amount > 0 and self.user_id:
            lines.append((0, 0, {
                'display_type': 'line_note',
                'name': f"Comisión Calculada para Asesor ({self.user_id.name}): ${self.commission_amount:,.2f} ({self.commission_percentage}%)",
            }))
            
        # Crear la factura de venta (account.move)
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.buyer_id.id if self.buyer_id else (self.owner_id.id if self.owner_id else False),
            'invoice_origin': self.name,
            'invoice_line_ids': lines,
        }
            
        move = self.env['account.move'].create(invoice_vals)
        
        self.state = 'sold'
        
        # Retornar acción para abrir la vista de la Factura recién generada
        return {
            'name': 'Factura Generada',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': move.id,
            'target': 'current',
        }

    # --- Cron: Recordatorio de Contratos ---
    # _clean_phone() heredado de estate.phone.mixin

    def _send_contract_whatsapp_template(self, phone, prop_title, fecha_vencimiento, dias_restantes, destinatario):
        """Envía recordatorio de contrato por WhatsApp con plantilla aprobada de Meta.
        Plantilla: recordatorio_contrato
        Parámetros: {{1}} destinatario, {{2}} propiedad, {{3}} fecha, {{4}} días restantes.
        """
        ICP = self.env['ir.config_parameter'].sudo()
        phone_number_id = ICP.get_param('estate_calendar.whatsapp_phone_number_id', '')
        access_token = ICP.get_param('estate_calendar.whatsapp_access_token', '')
        template_name = ICP.get_param('estate_management.whatsapp_contract_template', 'recordatorio_contrato')
        if not phone_number_id or not access_token or not phone:
            return False
        clean = self._clean_phone(phone)
        try:
            resp = requests.post(
                f'https://graph.facebook.com/v25.0/{phone_number_id}/messages',
                json={
                    'messaging_product': 'whatsapp',
                    'to': clean,
                    'type': 'template',
                    'template': {
                        'name': template_name,
                        'language': {'code': 'es'},
                        'components': [{
                            'type': 'body',
                            'parameters': [
                                {'type': 'text', 'text': destinatario},
                                {'type': 'text', 'text': prop_title},
                                {'type': 'text', 'text': fecha_vencimiento},
                                {'type': 'text', 'text': str(dias_restantes)},
                            ],
                        }],
                    },
                },
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json',
                },
                timeout=30,
            )
            if resp.status_code == 200:
                _logger.info('WhatsApp contrato (plantilla) enviado a %s', clean)
                return True
            _logger.warning('WhatsApp contrato falló (%s): %s', resp.status_code, resp.text[:300])
            return False
        except Exception as e:
            _logger.error('WhatsApp contrato error: %s', e)
            return False

    @api.model
    def _cron_check_contract_expiry(self):
        """Revisa contratos próximos a vencer: crea actividades + envía WhatsApp."""
        today = fields.Date.today()
        properties = self.search([
            ('contract_end_date', '!=', False),
            ('state', 'in', ['available', 'reserved']),
        ])
        for prop in properties:
            days_left = (prop.contract_end_date - today).days
            fecha_str = prop.contract_end_date.strftime('%d/%m/%Y')

            if 0 < days_left <= prop.contract_reminder_days:
                existing = self.env['mail.activity'].search([
                    ('res_model', '=', 'estate.property'),
                    ('res_id', '=', prop.id),
                    ('summary', 'ilike', 'Contrato por vencer'),
                ], limit=1)
                if not existing:
                    # Actividad en Odoo
                    prop.activity_schedule(
                        'mail.mail_activity_data_todo',
                        date_deadline=prop.contract_end_date,
                        summary=f'Contrato por vencer ({days_left} días)',
                        note=f'El contrato de la propiedad "{prop.title}" vence el {fecha_str}. Quedan {days_left} días.',
                        user_id=prop.user_id.id or self.env.uid,
                    )
                    # WhatsApp al asesor (plantilla Meta)
                    advisor = prop.user_id
                    if advisor and advisor.partner_id.mobile:
                        self._send_contract_whatsapp_template(
                            advisor.partner_id.mobile,
                            prop.title, fecha_str, days_left,
                            advisor.name,
                        )

            elif days_left <= 0:
                existing = self.env['mail.activity'].search([
                    ('res_model', '=', 'estate.property'),
                    ('res_id', '=', prop.id),
                    ('summary', 'ilike', 'VENCIDO'),
                ], limit=1)
                if not existing:
                    # Actividad en Odoo
                    prop.activity_schedule(
                        'mail.mail_activity_data_todo',
                        date_deadline=today,
                        summary='Contrato VENCIDO',
                        note=f'El contrato de la propiedad "{prop.title}" VENCIÓ el {fecha_str}.',
                        user_id=prop.user_id.id or self.env.uid,
                    )
                    # WhatsApp al asesor (plantilla Meta)
                    advisor = prop.user_id
                    if advisor and advisor.partner_id.mobile:
                        self._send_contract_whatsapp_template(
                            advisor.partner_id.mobile,
                            prop.title, fecha_str, 0,
                            advisor.name,
                        )

    @api.model
    def _cron_price_alerts(self):
        """Detecta propiedades sobrevaluadas con mucho tiempo en mercado y crea alertas."""
        today = fields.Date.today()
        props = self.search([
            ('state', '=', 'available'),
            ('avm_status', '=', 'high'),
            ('date_listed', '!=', False),
        ])
        for prop in props:
            dom = (today - prop.date_listed).days
            if dom >= 45:
                existing = self.env['mail.activity'].search([
                    ('res_model', '=', 'estate.property'),
                    ('res_id', '=', prop.id),
                    ('summary', 'ilike', 'reducir precio'),
                ], limit=1)
                if not existing:
                    prop.activity_schedule(
                        'mail.mail_activity_data_todo',
                        date_deadline=today,
                        summary=f'Considera reducir el precio ({dom} días sobrevaluado)',
                        note=(
                            f'La propiedad "{prop.title}" lleva {dom} días en el mercado '
                            f'y está SOBREVALORADA según el AVM '
                            f'(precio actual: ${prop.price:,.2f}, '
                            f'AVM estimado: ${prop.avm_estimated_price:,.2f}). '
                            f'Se recomienda revisar el precio de venta.'
                        ),
                        user_id=prop.user_id.id or self.env.uid,
                    )

    @api.depends('price', 'roi_appreciation_rate')
    def _compute_roi(self):
        """Mejora 13: Calcula plusvalía estimada a 5 años."""
        for rec in self:
            price = rec.price or 0.0
            appreciation = (rec.roi_appreciation_rate or 0.0) / 100.0
            if price > 0 and appreciation > 0:
                rec.roi_5year_value = price * ((1 + appreciation) ** 5)
            else:
                rec.roi_5year_value = price

    @api.model
    def _cron_stagnant_properties_alert(self):
        """Mejora 8: Alerta para propiedades sin visita en 45+ días."""
        from datetime import timedelta
        today = fields.Date.today()
        cutoff = today - timedelta(days=45)
        props = self.search([('state', '=', 'available'), ('date_listed', '<=', cutoff)])
        for prop in props:
            has_recent_visit = self.env['calendar.event'].sudo().search_count([
                ('property_id', '=', prop.id),
                ('visit_state', '=', 'done'),
                ('start', '>=', fields.Datetime.to_datetime(cutoff)),
            ])
            if not has_recent_visit:
                existing = self.env['mail.activity'].search([
                    ('res_model', '=', 'estate.property'),
                    ('res_id', '=', prop.id),
                    ('summary', 'ilike', 'Propiedad estancada'),
                ], limit=1)
                if not existing:
                    dom = (today - prop.date_listed).days if prop.date_listed else 0
                    prop.activity_schedule(
                        'mail.mail_activity_data_todo',
                        date_deadline=today,
                        summary=f'Propiedad estancada ({dom} días sin visitas)',
                        note=(
                            f'"{prop.title}" lleva {dom} días en el mercado sin visitas confirmadas. '
                            f'Acciones sugeridas: revisar precio, actualizar fotos o hacer campaña en redes.'
                        ),
                        user_id=prop.user_id.id or self.env.uid,
                    )

    def action_unpublish_wp(self):
        """Botón 'Despublicar de WP': elimina la propiedad de WordPress y marca
        wp_published = False en Odoo. Delega al método del módulo estate_wordpress
        (action_unpublish_wordpress) si está disponible; de lo contrario solo limpia
        los campos locales."""
        self.ensure_one()
        if hasattr(self, 'action_unpublish_wordpress'):
            return self.action_unpublish_wordpress()
        # Fallback: solo limpiar en Odoo
        self.write({'wp_published': False, 'wp_post_id': 0})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Despublicado',
                'message': 'La propiedad fue marcada como no publicada en Odoo. '
                           'El módulo estate_wordpress no está instalado, verifica manualmente en WordPress.',
                'sticky': False,
                'type': 'warning',
            },
        }
