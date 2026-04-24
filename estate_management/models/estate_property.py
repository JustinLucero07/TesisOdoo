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
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'title'

    name = fields.Char(
        string='Referencia', readonly=True, copy=False,
        default='Nuevo')
    title = fields.Char(string='Título', required=True, tracking=True)
    description = fields.Html(string='Descripción')

    def name_get(self):
        return [(rec.id, f"{rec.title} [{rec.name}]" if rec.name and rec.name != 'Nuevo' else rec.title or 'Nuevo')
                for rec in self]

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
        ('rent', 'Alquiler'),
    ], string='Tipo de Oferta', default='sale', tracking=True)

    # --- Ubicación ---
    street = fields.Char(string='Dirección')
    city = fields.Char(string='Ciudad', tracking=True)
    state_id = fields.Many2one(
        'res.country.state', string='Provincia/Estado')
    country_id = fields.Many2one(
        'res.country', string='País',
        default=lambda self: self.env.company.country_id)
    zip_code = fields.Char(string='Código Postal')
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

    def action_geocode_address(self):
        """Geocode the property address using Nominatim (OpenStreetMap) — free, no API key."""
        self.ensure_one()
        parts = [p for p in [self.street, self.city,
                             self.state_id.name if self.state_id else None,
                             self.country_id.name if self.country_id else None] if p]
        if not parts:
            raise UserError('Ingresa al menos la dirección y la ciudad para ubicar en el mapa.')
        query = ', '.join(parts)
        try:
            resp = requests.get(
                'https://nominatim.openstreetmap.org/search',
                params={'q': query, 'format': 'json', 'limit': 1},
                headers={'User-Agent': 'OdooEstateApp/1.0'},
                timeout=10,
            )
            data = resp.json()
            if data:
                lat = float(data[0]['lat'])
                lon = float(data[0]['lon'])
                self.write({'latitude': lat, 'longitude': lon})
                display_name = data[0].get('display_name', query)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Ubicación encontrada',
                        'message': f'Coordenadas actualizadas: {lat:.5f}, {lon:.5f}\n{display_name}',
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Dirección no encontrada',
                        'message': f'No se pudo geocodificar: "{query}". Intenta con más detalles.',
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
    area = fields.Float(string='Área (m²)')
    bedrooms = fields.Integer(string='Habitaciones', default=0)
    bathrooms = fields.Float(string='Baños', default=0.0)
    parking_spaces = fields.Integer(string='Parqueaderos', default=0)
    vehicle_capacity = fields.Integer(
        string='Capacidad Vehículos', default=0,
        help='Número total de vehículos que caben en los parqueaderos.')
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

    # --- Mejora 13: Calculadora de Rentabilidad (ROI) ---
    roi_monthly_rent_estimate = fields.Float(
        string='Renta Mensual Estimada ($)',
        help='Ingresa el arriendo mensual estimado para calcular el ROI.')
    roi_appreciation_rate = fields.Float(
        string='Apreciación Anual Estimada (%)', default=5.0,
        help='Porcentaje de plusvalía anual esperado. Promedio Ecuador: 5-8%.')
    roi_annual_yield = fields.Float(
        string='Rendimiento Anual por Arriendo (%)', compute='_compute_roi', store=True)
    roi_5year_value = fields.Float(
        string='Valor Estimado a 5 Años ($)', compute='_compute_roi', store=True)
    roi_monthly_cashflow = fields.Float(
        string='Flujo de Caja Mensual ($)', compute='_compute_roi', store=True,
        help='Ingreso neto mensual estimado (renta - mantenimiento estimado 15%).')

    # --- AVM (Automated Valuation Model) ---
    avm_estimated_price = fields.Float(string='Valor M. Estimado (AVM)', readonly=True, tracking=True)
    avm_last_calculated = fields.Datetime(string='Último AVM', readonly=True)
    avm_status = fields.Selection([
        ('fair', 'Justo (Alineado al Mercado)'),
        ('high', 'Sobrevalorado'),
        ('low', 'Subestimado/Oportunidad'),
        ('insufficient', 'Datos Insuficientes')
    ], string='Estado AVM', compute='_compute_avm_status', store=True)
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
        help='Puntuación 0-100 que mide completitud y atractivo del expediente.')
    property_score_label = fields.Char(
        string='Nivel de Puntuación', compute='_compute_property_score', store=True)

    # --- Fase 1: Captación y Exclusividad ---
    capture_sheet = fields.Binary(
        string='Hoja de Captación', attachment=True,
        help='Documento escaneado o PDF de la hoja de captación original.')
    capture_sheet_filename = fields.Char(string='Nombre del Archivo de Captación')
    is_exclusive = fields.Boolean(
        string='En Exclusividad', default=False, tracking=True,
        help='Indica si la propiedad fue captada bajo contrato de exclusividad.')
    exclusive_user_id = fields.Many2one(
        'res.users', string='Asesor Responsable (Captador)', tracking=True,
        help='El asesor que captó la exclusividad de esta propiedad.')


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
                            trend = '📈 Subiendo (+{:.1f}%)'.format(((avg_second/avg_first)-1)*100)
                        elif avg_second < avg_first * 0.97:
                            trend = '📉 Bajando ({:.1f}%)'.format(((avg_second/avg_first)-1)*100)
                        else:
                            trend = '➡️ Estable'
                    else:
                        trend = '➡️ Estable'
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
        ('available', 'Disponible'),
        ('reserved', 'Reservado'),
        ('sold', 'Vendido'),
        ('rented', 'Alquilado'),
    ], string='Estado', default='available', tracking=True, required=True)

    active = fields.Boolean(string='Activo', default=True)

    # --- Métricas de Venta ---
    date_listed = fields.Date(string='Fecha de Publicación', tracking=True,
        help='Fecha en que la propiedad se puso en el mercado.')
    date_sold = fields.Date(string='Fecha de Venta/Alquiler', tracking=True,
        help='Fecha en que se cerró la venta o alquiler.')
    days_on_market = fields.Integer(
        string='Días en el Mercado', compute='_compute_days_on_market', store=True,
        help='Cantidad de días que la propiedad estuvo disponible antes de venderse.')
    sold_by = fields.Selection([
        ('agency', 'Vendido por la Agencia'),
        ('owner', 'Vendido por el Dueño'),
    ], string='¿Quién Vendió?', tracking=True)

    # --- Contratos ---
    contract_end_date = fields.Date(string='Vencimiento de Contrato', tracking=True,
        help='Fecha en que vence el contrato de alquiler o exclusividad.')
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
    wp_post_id = fields.Integer(string='WordPress Post ID', readonly=True)
    wp_published = fields.Boolean(string='Publicado en WordPress', default=False)

    # --- Relaciones y Ventas ---
    owner_id = fields.Many2one('res.partner', string='Propietario')
    buyer_id = fields.Many2one('res.partner', string='Comprador', tracking=True)
    user_id = fields.Many2one('res.users', string='Asesor Responsable', default=lambda self: self.env.user, tracking=True)
    co_user_id = fields.Many2one('res.users', string='Co-Asesor', tracking=True,
                                 help='Segundo asesor que colabora en esta propiedad.')
    commission_split_pct = fields.Float(
        string='Split Co-Asesor (%)', default=50.0,
        help='Porcentaje de la comisión que corresponde al Co-Asesor (el resto es del Asesor Responsable).')

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
                'default_estate_transaction_type': 'sale' if self.offer_type == 'sale' else 'rent',
                'default_partner_id': self.buyer_id.id or self.owner_id.id or False,
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
            'estate_transaction_type': 'sale' if self.offer_type == 'sale' else 'rent',
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
        self.message_post(body=f'🛒 Orden de venta <b>{order.name}</b> creada desde esta propiedad.')
        if active_lead:
            active_lead.message_post(
                body=f'🛒 Orden de venta <b>{order.name}</b> creada para la propiedad '
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

        return properties

    def write(self, vals):
        res = super().write(vals)
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
        # Auto-sync price/title change to WordPress if already published
        # hasattr guard: estate_wordpress es módulo opcional (R4 fix)
        if 'price' in vals or 'title' in vals or 'description' in vals:
            for prop in self:
                wp_pub = getattr(prop, 'wp_published', False)
                wp_id = getattr(prop, 'wp_post_id', 0)
                if wp_pub and wp_id and hasattr(prop, 'action_publish_wordpress'):
                    try:
                        prop.action_publish_wordpress()
                    except Exception:
                        pass  # Silent — WP sync failures should not block saves
        # Historial de precios
        if 'price' in vals:
            for prop in self:
                old = prop.price
                new = vals['price']
                if old and old != new:
                    reason = 'reduction' if new < old else 'increase'
                    prop._record_price_change(old, new, reason)

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
        return res

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
        """Re-listar una propiedad ya vendida/alquilada para volver al mercado."""
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
        })
        self.message_post(
            body='Propiedad re-listada en el mercado. Datos de venta/alquiler anteriores archivados.',
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )

    def action_set_reserved(self):
        self.write({'state': 'reserved'})

    def action_set_sold(self):
        self.ensure_one()
        vals = {'state': 'sold', 'offer_type': 'sale'}
        if not self.date_sold:
            vals['date_sold'] = fields.Date.today()
        if not self.sold_by:
            vals['sold_by'] = 'agency'
        self.write(vals)
        self.env['estate.commission'].create({
            'property_id': self.id,
            'user_id': self.user_id.id,
            'amount': self.commission_amount,
            'type': 'sale',
            'date': fields.Date.today(),
        })

    def action_set_rented(self):
        self.ensure_one()
        self.write({'state': 'rented', 'offer_type': 'rent'})
        # Para alquileres, asumimos una comisión del 50% del precio (ajustable) o según porcentaje
        self.env['estate.commission'].create({
            'property_id': self.id,
            'user_id': self.user_id.id,
            'amount': self.commission_amount or (self.price * 0.5), # Ejemplo: medio mes de alquiler
            'type': 'rental',
            'date': fields.Date.today(),
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
    def _clean_phone(self, phone):
        """Normaliza número a formato internacional sin + (ej: 593981112222)."""
        clean = phone.replace(' ', '').replace('-', '').replace('+', '').replace('(', '').replace(')', '')
        if clean.startswith('0') and len(clean) == 10:
            clean = '593' + clean[1:]
        elif not clean.startswith('593'):
            clean = '593' + clean
        return clean

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
            ('state', 'in', ['available', 'reserved', 'rented']),
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
                        summary=f'⚠️ Contrato por vencer ({days_left} días)',
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
                        summary='❌ ¡Contrato VENCIDO!',
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
                        summary=f'💡 Considera reducir el precio ({dom} días sobrevaluado)',
                        note=(
                            f'La propiedad "{prop.title}" lleva {dom} días en el mercado '
                            f'y está SOBREVALORADA según el AVM '
                            f'(precio actual: ${prop.price:,.2f}, '
                            f'AVM estimado: ${prop.avm_estimated_price:,.2f}). '
                            f'Se recomienda revisar el precio de venta.'
                        ),
                        user_id=prop.user_id.id or self.env.uid,
                    )

    @api.depends('price', 'roi_monthly_rent_estimate', 'roi_appreciation_rate')
    def _compute_roi(self):
        """Mejora 13: Calcula métricas de rentabilidad para inversores."""
        for rec in self:
            price = rec.price or 0.0
            monthly_rent = rec.roi_monthly_rent_estimate or 0.0
            appreciation = (rec.roi_appreciation_rate or 0.0) / 100.0
            if price > 0 and monthly_rent > 0:
                annual_rent = monthly_rent * 12
                rec.roi_annual_yield = (annual_rent / price) * 100.0
                maintenance = monthly_rent * 0.15
                rec.roi_monthly_cashflow = monthly_rent - maintenance
            else:
                rec.roi_annual_yield = 0.0
                rec.roi_monthly_cashflow = 0.0
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
                        summary=f'🛑 Propiedad estancada ({dom} días sin visitas)',
                        note=(
                            f'"{prop.title}" lleva {dom} días en el mercado sin visitas confirmadas. '
                            f'Acciones sugeridas: revisar precio, actualizar fotos o hacer campaña en redes.'
                        ),
                        user_id=prop.user_id.id or self.env.uid,
                    )
