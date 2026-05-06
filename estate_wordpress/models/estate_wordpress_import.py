import base64
import json
import logging
import re

import requests

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# =============================================================================
# MAPEOS INVERSOS: WordPress taxonomy ID → valor en Odoo
# =============================================================================

WP_TYPE_TO_ODOO = {
    93: 'Casa',
    94: 'Terreno',
    95: 'Departamento',
    96: 'Edificio',
    97: 'Finca / Quinta',
    98: 'Oficina',
    126: 'Casa Rentera / Comercial',
    143: 'Propiedad',
}

# property-status taxonomy ID → state de estate.property
WP_STATUS_TO_STATE = {
    32: 'available',   # En Venta
    46: 'reserved',    # Nuevo Listado
    123: 'sold',       # Vendido
    31: 'rented',      # En Renta / Alquiler
}

# property-status taxonomy ID → offer_type de estate.property
WP_STATUS_TO_OFFER_TYPE = {
    32: 'sale',
    46: 'sale',
    123: 'sale',
    31: 'rent',
}

# property-city taxonomy ID → nombre de ciudad en Odoo
WP_CITY_TO_ODOO = {
    102: 'Cuenca',
    137: 'Azogues',
    106: 'Cañar',
    138: 'Loja',
    130: 'Paute',
    142: 'Puerto Inca',
    144: 'San Fernando',
    139: 'Santa Isabel',
    127: 'Sigsig',
}


class EstateWordpressImportLine(models.TransientModel):
    _name = 'estate.wordpress.import.line'
    _description = 'Línea de Preview de Importación WordPress'

    wizard_id = fields.Many2one('estate.wordpress.import.wizard', ondelete='cascade')
    selected = fields.Boolean('Importar', default=True)
    wp_post_id = fields.Integer('Post ID')
    title = fields.Char('Título')
    price = fields.Float('Precio')
    area = fields.Float('Área m²')
    bedrooms = fields.Integer('Habitaciones')
    city = fields.Char('Ciudad')
    status = fields.Char('Estado WP')
    already_exists = fields.Boolean('Ya existe en Odoo')
    odoo_property_id = fields.Many2one('estate.property', string='Propiedad en Odoo')


class EstateWordpressImportWizard(models.TransientModel):
    _name = 'estate.wordpress.import.wizard'
    _description = 'Importar Propiedades desde WordPress'

    # --- Opciones ---
    import_images = fields.Boolean(
        'Importar Imágenes', default=True,
        help='Descarga imagen principal y galería. El proceso tarda más según la cantidad de imágenes.')
    update_existing = fields.Boolean(
        'Actualizar existentes', default=False,
        help='Si está activo, actualiza las propiedades que ya existen en Odoo (identificadas por WordPress Post ID).')
    max_properties = fields.Integer(
        'Máximo a importar', default=100,
        help='Límite de propiedades a traer en esta sesión. WordPress devuelve 20 por página.')

    # --- Estado del wizard ---
    import_state = fields.Selection([
        ('draft', 'Configuración'),
        ('preview', 'Selección'),
        ('done', 'Completado'),
    ], default='draft', string='Estado')

    # --- Preview lines ---
    preview_line_ids = fields.One2many(
        'estate.wordpress.import.line', 'wizard_id', string='Propiedades encontradas')
    preview_total = fields.Integer('Total encontradas', readonly=True)

    # --- Resultados ---
    imported_count = fields.Integer('Importadas', readonly=True)
    updated_count = fields.Integer('Actualizadas', readonly=True)
    skipped_count = fields.Integer('Omitidas', readonly=True)
    error_log = fields.Text('Registro de Errores', readonly=True)

    # =========================================================================
    # HELPERS DE CONFIGURACIÓN
    # =========================================================================

    def _get_wp_cfg(self):
        """Obtiene la configuración WordPress desde ir.config_parameter."""
        ICP = self.env['ir.config_parameter'].sudo()
        method = ICP.get_param('estate_wp.auth_method', 'basic')
        user = ICP.get_param('estate_wp.username', '')
        pwd = ICP.get_param('estate_wp.app_password', '')
        token = ICP.get_param('estate_wp.jwt_token', '')

        headers = {'User-Agent': 'Odoo/19 EstateImport/1.0'}
        auth = None

        if method == 'jwt' and token:
            headers['Authorization'] = f'Bearer {token}'
        else:
            auth = (user, pwd)

        return {
            'url': ICP.get_param('estate_wp.url', '').rstrip('/'),
            'auth': auth,
            'headers': headers,
            'post_type': ICP.get_param('estate_wp.post_type', 'property'),
            'active': ICP.get_param('estate_wp.active', 'False'),
        }

    # =========================================================================
    # FETCH DE PROPIEDADES DESDE WP REST API
    # =========================================================================

    def _fetch_all_wp_properties(self, cfg):
        """Pagina por la WP REST API y devuelve todas las propiedades hasta el límite."""
        all_props = []
        page = 1
        per_page = 20
        post_type = cfg['post_type']

        while len(all_props) < self.max_properties:
            url = f"{cfg['url']}/wp-json/wp/v2/{post_type}"
            params = {
                'per_page': per_page,
                'page': page,
                '_embed': 1,
                'context': 'edit',
            }
            try:
                resp = requests.get(
                    url, params=params,
                    auth=cfg['auth'], headers=cfg['headers'],
                    timeout=30)

                if resp.status_code in (400, 404) and page > 1:
                    break  # No hay más páginas
                if resp.status_code != 200:
                    _logger.error(f"WP fetch página {page}: {resp.status_code} - {resp.text[:300]}")
                    break

                data = resp.json()
                if not data:
                    break

                all_props.extend(data)

                total_pages = int(resp.headers.get('X-WP-TotalPages', 1))
                if page >= total_pages:
                    break
                page += 1

            except Exception as e:
                _logger.error(f"WP fetch error página {page}: {e}")
                break

        return all_props[:self.max_properties]

    # =========================================================================
    # DESCARGA DE IMÁGENES
    # =========================================================================

    def _download_image(self, url, cfg):
        """Descarga una imagen por URL y la retorna en base64, o False si falla."""
        try:
            resp = requests.get(url, auth=cfg['auth'], headers=cfg['headers'], timeout=30)
            if resp.status_code == 200 and resp.content:
                return base64.b64encode(resp.content).decode('utf-8')
        except Exception as e:
            _logger.warning(f"No se pudo descargar imagen {url}: {e}")
        return False

    def _get_media_url_by_id(self, cfg, media_id):
        """Obtiene la URL de un attachment de la galería dado su media ID en WP."""
        try:
            url = f"{cfg['url']}/wp-json/wp/v2/media/{media_id}"
            resp = requests.get(url, auth=cfg['auth'], headers=cfg['headers'], timeout=15)
            if resp.status_code == 200:
                return resp.json().get('source_url', '')
        except Exception:
            pass
        return ''

    # =========================================================================
    # PARSEO DE META Y TAXONOMÍAS
    # =========================================================================

    def _fetch_meta_via_xmlrpc(self, cfg, wp_post_id):
        """
        Obtiene TODOS los custom fields de un post via WordPress XML-RPC.
        XML-RPC está activo por defecto en WordPress y devuelve todos los meta
        sin necesidad de register_meta() — a diferencia de la REST API.

        NOTA: XML-RPC usa usuario+contraseña directamente (no JWT).
        Por eso leemos las credenciales desde ICP, sin depender de cfg['auth'].
        """
        try:
            from xmlrpc.client import ServerProxy
            ICP = self.env['ir.config_parameter'].sudo()
            user = ICP.get_param('estate_wp.username', '')
            pwd = ICP.get_param('estate_wp.app_password', '')
            if not user or not pwd:
                _logger.debug("XML-RPC: sin credenciales configuradas, saltando.")
                return {}

            xmlrpc_url = f"{cfg['url']}/xmlrpc.php"
            server = ServerProxy(xmlrpc_url, allow_none=True)
            # blog_id=1, username, password, post_id, fields
            post = server.wp.getPost(1, user, pwd, int(wp_post_id), ['custom_fields'])

            meta = {}
            for field in (post.get('custom_fields') or []):
                key = field.get('key', '')
                val = field.get('value', '')
                # Excluir campos internos de WP (prefijo _) y vacíos
                if key and not key.startswith('_') and val not in ('', None):
                    meta[key] = val

            _logger.info(
                "XML-RPC: post %s → %d custom fields obtenidos (price=%s, size=%s, beds=%s)",
                wp_post_id, len(meta),
                meta.get('fave_property_price', '?'),
                meta.get('fave_property_size', '?'),
                meta.get('fave_property_bedrooms', '?'))
            return meta
        except Exception as e:
            _logger.warning("XML-RPC meta fetch falló para post %s: %s", wp_post_id, e)
            return {}

    def _fetch_single_post_meta(self, cfg, wp_post_id):
        """
        Estrategia en cascada para obtener los meta de un post Houzez.
        Usa las MISMAS llaves que _build_houzez_meta() del sync:
          fave_property_price, fave_property_size, fave_property_land,
          fave_property_bedrooms, fave_property_rooms, fave_property_bathrooms,
          fave_property_garage, fave_property_year, fave_property_id,
          fave_property_address, fave_property_zip,
          houzez_geolocation_lat, houzez_geolocation_long,
          fave_property_map_address, fave_property_location
        """
        combined = {}
        KEY_FIELDS = ('fave_property_price', 'fave_property_size', 'fave_property_bedrooms')

        def _has_key_data():
            return any(
                combined.get(k) and str(combined[k]).strip() not in ('', '0', '0.0')
                for k in KEY_FIELDS
            )

        # === Estrategia 1: XML-RPC (siempre devuelve custom fields en WP) ===
        xmlrpc_meta = self._fetch_meta_via_xmlrpc(cfg, wp_post_id)
        if xmlrpc_meta:
            combined.update(xmlrpc_meta)
            _logger.info(
                "Import meta post %s — XML-RPC: %d campos. price=%s, size=%s, beds=%s",
                wp_post_id, len(xmlrpc_meta),
                xmlrpc_meta.get('fave_property_price', '?'),
                xmlrpc_meta.get('fave_property_size', '?'),
                xmlrpc_meta.get('fave_property_bedrooms', '?'))
            if _has_key_data():
                return combined

        # === Estrategia 2: Plugin odoo-meta-reader (GET, lee TODOS los meta) ===
        try:
            meta_url = f"{cfg['url']}/wp-json/odoo-meta/v1/read/{wp_post_id}"
            resp = requests.get(
                meta_url, auth=cfg['auth'], headers=cfg['headers'], timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict):
                    for k, v in data.items():
                        if v not in (None, '', []):
                            combined.setdefault(k, v)
                    _logger.info(
                        "Import meta post %s — odoo-meta-reader: %d campos. price=%s, size=%s, beds=%s",
                        wp_post_id, len(data),
                        combined.get('fave_property_price', '?'),
                        combined.get('fave_property_size', '?'),
                        combined.get('fave_property_bedrooms', '?'))
                    if _has_key_data():
                        return combined
        except Exception as e:
            _logger.debug("odoo-meta-reader endpoint no disponible para post %s: %s", wp_post_id, e)

        # === Estrategia 3: Endpoint custom odoo-houzez (el MISMO que usamos para GUARDAR) ===
        try:
            meta_url = f"{cfg['url']}/wp-json/odoo-houzez/v1/meta/{wp_post_id}"
            resp = requests.get(
                meta_url, auth=cfg['auth'], headers=cfg['headers'], timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict):
                    meta_data = data.get('meta', data)
                    if isinstance(meta_data, dict):
                        for k, v in meta_data.items():
                            if v not in (None, '', []):
                                combined.setdefault(k, v)
                    _logger.info(
                        "Import meta post %s — odoo-houzez endpoint: price=%s, size=%s",
                        wp_post_id,
                        combined.get('fave_property_price', '?'),
                        combined.get('fave_property_size', '?'))
                    if _has_key_data():
                        return combined
        except Exception as e:
            _logger.debug("odoo-houzez meta endpoint no disponible para post %s: %s", wp_post_id, e)

        # === Estrategia 3: REST individual con context=edit ===
        post_type = cfg['post_type']
        try:
            url = f"{cfg['url']}/wp-json/wp/v2/{post_type}/{wp_post_id}"
            resp = requests.get(
                url,
                params={'context': 'edit'},
                auth=cfg['auth'], headers=cfg['headers'],
                timeout=20,
            )
            if resp.status_code == 200:
                data = resp.json()
                # Extraer meta registrado
                rest_meta = data.get('meta', {}) or {}
                rest_acf = data.get('acf', {}) or {}
                for source in (rest_meta, rest_acf):
                    for k, v in source.items():
                        if v not in (None, '', [], False):
                            combined.setdefault(k, v)
                # Houzez a veces expone campos a primer nivel con prefijo fave_ o houzez_
                for key, val in data.items():
                    if key.startswith(('fave_', 'houzez_')) and val not in (None, '', [], False):
                        combined.setdefault(key, val)
                _logger.info(
                    "Import meta post %s — REST edit: price=%s, size=%s, beds=%s",
                    wp_post_id,
                    combined.get('fave_property_price', '?'),
                    combined.get('fave_property_size', '?'),
                    combined.get('fave_property_bedrooms', '?'))
                if _has_key_data():
                    return combined
        except Exception as e:
            _logger.debug("REST individual fetch falló para post %s: %s", wp_post_id, e)

        # === Estrategia 4: endpoints custom Houzez (tema) ===
        if not _has_key_data():
            for route in [
                f"{cfg['url']}/wp-json/houzez/v1/property-meta/{wp_post_id}",
                f"{cfg['url']}/wp-json/houzez/v1/properties/{wp_post_id}",
            ]:
                try:
                    resp = requests.get(
                        route, auth=cfg['auth'], headers=cfg['headers'], timeout=10)
                    if resp.status_code == 200:
                        data = resp.json()
                        if isinstance(data, dict):
                            if 'data' in data and isinstance(data['data'], dict):
                                for k, v in data['data'].items():
                                    if v not in (None, ''):
                                        combined.setdefault(k, v)
                            for k, v in data.items():
                                if k != 'data' and v not in (None, '', {}, []):
                                    combined.setdefault(k, v)
                        _logger.info(
                            "Import meta post %s — Houzez endpoint %s: price=%s",
                            wp_post_id, route.split('/')[-2],
                            combined.get('fave_property_price', '?'))
                        if _has_key_data():
                            break
                except Exception:
                    pass

        # === Estrategia 5: REST individual SIN context=edit (público) ===
        if not _has_key_data():
            try:
                url = f"{cfg['url']}/wp-json/wp/v2/{post_type}/{wp_post_id}"
                resp = requests.get(
                    url, auth=cfg['auth'], headers=cfg['headers'], timeout=20)
                if resp.status_code == 200:
                    data = resp.json()
                    for key, val in data.items():
                        if key.startswith(('fave_', 'houzez_')) and val not in (None, '', [], False):
                            combined.setdefault(key, val)
            except Exception:
                pass

        # Log final si seguimos sin datos
        if not _has_key_data():
            _logger.warning(
                "Import meta post %s: NO SE ENCONTRARON DATOS después de 5 estrategias. "
                "Llaves encontradas: %s",
                wp_post_id, list(combined.keys())[:20])

        return combined

    def _get_meta_getter(self, wp_prop, extra_meta=None):
        """Retorna una función para obtener campos meta con fallback a acf y extra_meta."""
        meta = wp_prop.get('meta', {}) or {}
        acf = wp_prop.get('acf', {}) or {}
        # Houzez a veces inyecta meta directamente en la respuesta principal o en 'houzez_meta'
        h_meta = wp_prop.get('houzez_meta', {}) or {}
        extra = extra_meta or {}

        def get_meta(key, default=''):
            # Prioridad: meta directo → acf → houzez_meta → extra_meta (fetch individual) → raíz del post
            for source in (meta, acf, h_meta, extra, wp_prop):
                if not isinstance(source, dict):
                    continue
                val = source.get(key)
                if val is not None:
                    if isinstance(val, list):
                        val = val[0] if val else None
                    if val not in (None, '', False):
                        return val
            return default

        return get_meta

    def _get_taxonomy_term_ids(self, wp_prop, taxonomy_name):
        """Extrae IDs de términos de una taxonomía desde _embedded (soporta - y _)."""
        alt_name = taxonomy_name.replace('-', '_') if '-' in taxonomy_name else taxonomy_name.replace('_', '-')
        try:
            terms_groups = wp_prop.get('_embedded', {}).get('wp:term', [])
            for group in terms_groups:
                # Verificar si el grupo pertenece a la taxonomía buscada
                first_term = group[0] if group else {}
                if first_term.get('taxonomy') in (taxonomy_name, alt_name):
                    return [t['id'] for t in group]
        except Exception:
            pass
        return []

    def _get_taxonomy_term_names(self, wp_prop, taxonomy_name):
        """Extrae NOMBRES de términos de una taxonomía desde _embedded."""
        alt_name = taxonomy_name.replace('-', '_') if '-' in taxonomy_name else taxonomy_name.replace('_', '-')
        try:
            terms_groups = wp_prop.get('_embedded', {}).get('wp:term', [])
            for group in terms_groups:
                first_term = group[0] if group else {}
                if first_term.get('taxonomy') in (taxonomy_name, alt_name):
                    return [t['name'] for t in group if t.get('name')]
        except Exception:
            pass
        return []

    # =========================================================================
    # MAPEO WP → ODOO VALS
    # =========================================================================

    @staticmethod
    def _safe_float(val, default=0.0):
        if not val:
            return default
        try:
            # Limpiar símbolos de moneda y caracteres no numéricos excepto coma/punto
            clean_val = re.sub(r'[^\d,.]', '', str(val)).strip()
            # Manejar formato europeo/latino: 1.000,50 -> 1000.50
            if ',' in clean_val and '.' in clean_val:
                if clean_val.rfind(',') > clean_val.rfind('.'):
                    clean_val = clean_val.replace('.', '').replace(',', '.')
                else:
                    clean_val = clean_val.replace(',', '')
            elif ',' in clean_val:
                clean_val = clean_val.replace(',', '.')
            return float(clean_val)
        except Exception:
            return default

    @staticmethod
    def _safe_int(val, default=0):
        if not val:
            return default
        try:
            clean_val = re.sub(r'[^\d]', '', str(val)).strip()
            return int(clean_val) if clean_val else default
        except Exception:
            return default

    def _get_or_create_property_type(self, type_name):
        """Busca o crea un registro estate.property.type."""
        PropertyType = self.env['estate.property.type']
        ptype = PropertyType.search([('name', 'ilike', type_name)], limit=1)
        if not ptype:
            ptype = PropertyType.create({'name': type_name})
        return ptype

    def _meta_looks_empty(self, wp_prop):
        """True si los campos meta numéricos clave están todos vacíos/cero."""
        meta = wp_prop.get('meta', {}) or {}
        acf = wp_prop.get('acf', {}) or {}
        key_fields = ['fave_property_price', 'fave_property_size', 'fave_property_bedrooms']
        for key in key_fields:
            val = meta.get(key) or acf.get(key)
            if val and str(val).strip() not in ('', '0', '0.0'):
                return False
        return True

    def _map_wp_to_vals(self, wp_prop, extra_meta=None):
        """Convierte un dict de propiedad WP a vals para estate.property.
        
        Campos leídos — SIMÉTRICOS con _build_houzez_meta() del sync:
          fave_property_price, fave_property_size, fave_property_land,
          fave_property_bedrooms, fave_property_rooms, fave_property_bathrooms,
          fave_property_garage, fave_property_year, fave_property_id,
          fave_property_address, fave_property_zip,
          fave_property_map_address, fave_property_location,
          houzez_geolocation_lat, houzez_geolocation_long
        """
        get_meta = self._get_meta_getter(wp_prop, extra_meta)

        # --- Título ---
        raw_title = wp_prop.get('title', {}).get('rendered', '')
        title = re.sub(r'<[^>]+>', '', raw_title).strip() or 'Propiedad sin título'

        # --- Descripción (HTML conservado) ---
        description = wp_prop.get('content', {}).get('rendered', '')

        # --- Campos numéricos (mismas llaves que _build_houzez_meta) ---
        price = self._safe_float(get_meta('fave_property_price'))
        area = self._safe_float(
            get_meta('fave_property_size')
            or get_meta('fave_property_land'))
        bedrooms = self._safe_int(
            get_meta('fave_property_bedrooms')
            or get_meta('fave_property_rooms'))
        bathrooms = self._safe_float(get_meta('fave_property_bathrooms'))
        parking = self._safe_int(get_meta('fave_property_garage'))
        year_raw = self._safe_int(get_meta('fave_property_year'))

        # --- Ubicación (mismas llaves que _build_houzez_meta) ---
        street = get_meta('fave_property_address')
        if not street:
            street = get_meta('fave_property_map_address')
        zip_code = get_meta('fave_property_zip')

        # GPS: primero houzez_geolocation_*, luego fave_property_location ("lat,lng,zoom")
        lat = self._safe_float(get_meta('houzez_geolocation_lat'))
        lng = self._safe_float(get_meta('houzez_geolocation_long'))

        if not (lat and lng):
            location_str = get_meta('fave_property_location')
            if location_str and ',' in str(location_str):
                parts = str(location_str).split(',')
                if len(parts) >= 2:
                    lat = lat or self._safe_float(parts[0])
                    lng = lng or self._safe_float(parts[1])

        # Log detallado de lo que se extrajo
        _logger.info(
            "Mapeo WP→Odoo [%s]: price=%s, area=%s, beds=%s, baths=%s, "
            "parking=%s, street=%s, city_tax=%s, lat=%s, lng=%s",
            title[:40], price, area, bedrooms, bathrooms,
            parking, (street or '')[:30],
            self._get_taxonomy_term_ids(wp_prop, 'property-city'),
            lat, lng)

        # --- Taxonomías ---
        type_tax_ids = self._get_taxonomy_term_ids(wp_prop, 'property-type')
        status_tax_ids = self._get_taxonomy_term_ids(wp_prop, 'property-status')
        city_tax_ids = self._get_taxonomy_term_ids(wp_prop, 'property-city')

        # Mapear estado y tipo de oferta
        odoo_state = 'available'
        offer_type = 'sale'
        for tid in status_tax_ids:
            if tid in WP_STATUS_TO_STATE:
                odoo_state = WP_STATUS_TO_STATE[tid]
                offer_type = WP_STATUS_TO_OFFER_TYPE[tid]
                break
        
        # Fallback por nombre de estado si el ID no está mapeado
        if odoo_state == 'available' and not status_tax_ids:
            status_names = self._get_taxonomy_term_names(wp_prop, 'property-status')
            for sname in status_names:
                sname_l = sname.lower()
                if 'venta' in sname_l:
                    odoo_state, offer_type = 'available', 'sale'
                    break
                elif any(x in sname_l for x in ('renta', 'alquiler', 'arriendo')):
                    odoo_state, offer_type = 'available', 'rent'
                    break

        # Mapear tipo de propiedad desde taxonomía WP
        property_type_id = False
        for tid in type_tax_ids:
            type_name = WP_TYPE_TO_ODOO.get(tid)
            if type_name:
                property_type_id = self._get_or_create_property_type(type_name).id
                break
        
        # Fallback por nombre de término para Tipo de Propiedad
        if not property_type_id:
            type_names = self._get_taxonomy_term_names(wp_prop, 'property-type')
            if type_names:
                property_type_id = self._get_or_create_property_type(type_names[0]).id
        
        # Fallback 1: detectar tipo desde el nombre del término de taxonomía (ya cubierto arriba, pero mantenemos por seguridad)
        if not property_type_id:
            try:
                # El código anterior usaba una búsqueda manual en _embedded, la nueva _get_taxonomy_term_names es más limpia.
                pass
            except Exception:
                pass

        # Fallback 2: detectar tipo por palabras clave en el título
        if not property_type_id:
            title_lower = title.lower()
            keyword_map = [
                (['terreno', 'lote', 'solar'], 'Terreno'),
                (['departamento', 'depto', 'suite'], 'Departamento'),
                (['casa', 'villa', 'chalet'], 'Casa'),
                (['oficina', 'local comercial'], 'Oficina'),
                (['edificio'], 'Edificio'),
                (['finca', 'quinta', 'hacienda'], 'Finca / Quinta'),
            ]
            for keywords, type_name in keyword_map:
                if any(kw in title_lower for kw in keywords):
                    property_type_id = self._get_or_create_property_type(type_name).id
                    break

        # Fallback 3: tipo genérico garantizado
        if not property_type_id:
            property_type_id = self._get_or_create_property_type('Propiedad').id

        # Mapear ciudad
        city = ''
        for tid in city_tax_ids:
            city = WP_CITY_TO_ODOO.get(tid, '')
            if city:
                break
        
        # Fallback por nombre de término si el ID no está mapeado
        if not city:
            city_names = self._get_taxonomy_term_names(wp_prop, 'property-city')
            if city_names:
                city = city_names[0]
        
        if not city:
            city = get_meta('fave_property_city', '')

        vals = {
            'title': title,
            'description': description,
            'price': price,
            'area': area,
            'bedrooms': bedrooms,
            'bathrooms': bathrooms,
            'parking_spaces': parking,
            'street': street,
            'zip_code': zip_code,
            'city': city,
            'state': odoo_state,
            'offer_type': offer_type,
            'wp_post_id': wp_prop.get('id', 0),
            'wp_published': True,
        }

        if property_type_id:
            vals['property_type_id'] = property_type_id

        import datetime
        current_year = datetime.date.today().year
        if year_raw and 1800 <= year_raw <= current_year:
            vals['year_built'] = year_raw

        if lat:
            vals['latitude'] = lat
        if lng:
            vals['longitude'] = lng

        return vals

    # =========================================================================
    # IMPORTACIÓN DE IMÁGENES
    # =========================================================================

    def _get_all_gallery_urls(self, cfg, wp_post_id, wp_prop):
        """Obtiene todas las URLs de imágenes de galería usando dos estrategias."""
        urls_seen = set()
        gallery_urls = []

        # --- Estrategia 1: meta fave_property_images (IDs de media Houzez) ---
        get_meta = self._get_meta_getter(wp_prop)
        raw_gallery = get_meta('fave_property_images', [])
        gallery_media_ids = []

        if isinstance(raw_gallery, list):
            gallery_media_ids = [int(x) for x in raw_gallery if str(x).strip().isdigit()]
        elif isinstance(raw_gallery, str) and raw_gallery:
            try:
                parsed = json.loads(raw_gallery)
                if isinstance(parsed, list):
                    gallery_media_ids = [int(x) for x in parsed if str(x).strip().isdigit()]
            except Exception:
                for part in raw_gallery.split(','):
                    part = part.strip()
                    if part.isdigit():
                        gallery_media_ids.append(int(part))

        for media_id in gallery_media_ids:
            url = self._get_media_url_by_id(cfg, media_id)
            if url and url not in urls_seen:
                urls_seen.add(url)
                gallery_urls.append(url)

        # --- Estrategia 2: /wp-json/wp/v2/media?parent=POST_ID ---
        # Trae TODOS los adjuntos del post, independientemente del meta Houzez
        if wp_post_id:
            try:
                media_api = f"{cfg['url']}/wp-json/wp/v2/media"
                resp = requests.get(
                    media_api,
                    params={'parent': wp_post_id, 'per_page': 50},
                    auth=cfg['auth'], headers=cfg['headers'],
                    timeout=20)
                if resp.status_code == 200:
                    for item in resp.json():
                        url = item.get('source_url', '')
                        # También intenta la versión large/medium si existe
                        sizes = item.get('media_details', {}).get('sizes', {})
                        best_url = (
                            sizes.get('large', {}).get('source_url')
                            or sizes.get('full', {}).get('source_url')
                            or url
                        )
                        if best_url and best_url not in urls_seen:
                            urls_seen.add(best_url)
                            gallery_urls.append(best_url)
            except Exception as e:
                _logger.warning(f"No se pudo consultar media?parent={wp_post_id}: {e}")

        return gallery_urls

    def _import_images_for_property(self, prop, wp_prop, cfg):
        """Descarga y asocia imagen principal + toda la galería a la propiedad."""
        wp_post_id = wp_prop.get('id', 0)
        featured_url = ''

        # Imagen principal desde _embedded
        try:
            media_list = wp_prop.get('_embedded', {}).get('wp:featuredmedia', [])
            if media_list:
                featured_url = media_list[0].get('source_url', '')
        except Exception:
            pass

        if featured_url:
            img_b64 = self._download_image(featured_url, cfg)
            if img_b64:
                prop.image_main = img_b64

        # Galería completa: meta Houzez + adjuntos del post
        gallery_urls = self._get_all_gallery_urls(cfg, wp_post_id, wp_prop)

        image_vals = []
        for idx, url in enumerate(gallery_urls[:20], 1):
            # Saltar si es la misma que la portada
            if url == featured_url:
                continue
            img_b64 = self._download_image(url, cfg)
            if img_b64:
                image_vals.append({
                    'name': f'Imagen {idx}',
                    'image': img_b64,
                    'sequence': idx * 10,
                    'property_id': prop.id,
                })

        if image_vals:
            self.env['estate.property.image'].create(image_vals)

    # =========================================================================
    # ACCIÓN PRINCIPAL
    # =========================================================================

    def action_preview(self):
        """Paso 1: Busca propiedades en WordPress y las muestra para selección."""
        self.ensure_one()
        cfg = self._get_wp_cfg()

        if cfg['active'] != 'True':
            raise UserError(
                'La integración WordPress no está activa.\n'
                'Actívala en Ajustes → Integración WordPress.')
        if not cfg['url']:
            raise UserError('Falta configurar la URL de WordPress.')

        wp_props = self._fetch_all_wp_properties(cfg)
        if not wp_props:
            raise UserError(
                'No se encontraron propiedades en WordPress.\n'
                'Verifica la URL, credenciales y post type.')

        # Limpiar líneas anteriores
        self.preview_line_ids.unlink()

        Property = self.env['estate.property']
        lines = []

        for wp_prop in wp_props:
            wp_id = wp_prop.get('id', 0)
            raw_title = wp_prop.get('title', {}).get('rendered', f'Post {wp_id}')
            title = re.sub(r'<[^>]+>', '', raw_title).strip() or 'Sin título'

            # Obtener meta — intentar endpoint GET primero, luego REST rápido
            meta = wp_prop.get('meta', {}) or {}
            acf = wp_prop.get('acf', {}) or {}

            # Intentar endpoint GET para tener datos reales en el preview
            try:
                meta_url = f"{cfg['url']}/wp-json/odoo-houzez/v1/meta/{wp_id}"
                resp = requests.get(
                    meta_url, auth=cfg['auth'], headers=cfg['headers'], timeout=10)
                if resp.status_code == 200:
                    extra = resp.json()
                    if isinstance(extra, dict):
                        meta.update(extra)
                        _logger.info("Preview: post %s meta GET OK, %d campos", wp_id, len(extra))
            except Exception:
                pass

            price = self._safe_float(
                meta.get('fave_property_price') or acf.get('fave_property_price'))
            area = self._safe_float(
                meta.get('fave_property_size') or acf.get('fave_property_size'))
            beds = self._safe_int(
                meta.get('fave_property_bedrooms') or acf.get('fave_property_bedrooms'))

            # Extraer ciudad desde taxonomías
            city = ''
            city_ids = self._get_taxonomy_term_ids(wp_prop, 'property-city')
            for tid in city_ids:
                city = WP_CITY_TO_ODOO.get(tid, '')
                if city:
                    break
            if not city:
                city_names = self._get_taxonomy_term_names(wp_prop, 'property-city')
                city = city_names[0] if city_names else ''

            # Status
            status = wp_prop.get('status', 'publish')

            # ¿Ya existe en Odoo?
            existing = Property.search([('wp_post_id', '=', wp_id)], limit=1) if wp_id else False

            lines.append({
                'wizard_id': self.id,
                'selected': not bool(existing),  # Desmarcar las que ya existen
                'wp_post_id': wp_id,
                'title': title[:200],
                'price': price,
                'area': area,
                'bedrooms': beds,
                'city': city,
                'status': status,
                'already_exists': bool(existing),
                'odoo_property_id': existing.id if existing else False,
            })

        self.env['estate.wordpress.import.line'].create(lines)

        self.write({
            'import_state': 'preview',
            'preview_total': len(lines),
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'estate.wordpress.import.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_select_all(self):
        """Marcar todas las líneas como seleccionadas."""
        self.preview_line_ids.write({'selected': True})
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_select_none(self):
        """Desmarcar todas las líneas."""
        self.preview_line_ids.write({'selected': False})
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_select_new_only(self):
        """Seleccionar solo las que NO existen en Odoo."""
        for line in self.preview_line_ids:
            line.selected = not line.already_exists
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_import(self):
        """Paso 2: Importa las propiedades SELECCIONADAS desde WordPress."""
        self.ensure_one()
        cfg = self._get_wp_cfg()

        selected_lines = self.preview_line_ids.filtered('selected')
        if not selected_lines:
            raise UserError('No seleccionaste ninguna propiedad para importar.')

        # Necesitamos re-fetch los datos completos de WP para cada propiedad seleccionada
        Property = self.env['estate.property'].with_context(no_wp_sync=True)
        imported = updated = skipped = 0
        errors = []

        for line in selected_lines:
            wp_id = line.wp_post_id
            try:
                with self.env.cr.savepoint():
                    # Fetch del post individual con embed
                    post_type = cfg['post_type']
                    api_url = f"{cfg['url']}/wp-json/wp/v2/{post_type}/{wp_id}"
                    resp = requests.get(
                        api_url,
                        params={'_embed': 1, 'context': 'edit'},
                        auth=cfg['auth'], headers=cfg['headers'], timeout=30)

                    if resp.status_code != 200:
                        errors.append(f"[{line.title}]: HTTP {resp.status_code}")
                        continue

                    wp_prop = resp.json()

                    # Fetch meta completo (XML-RPC + cascada)
                    extra_meta = self._fetch_single_post_meta(cfg, wp_id)
                    vals = self._map_wp_to_vals(wp_prop, extra_meta)

                    existing = Property.search([('wp_post_id', '=', wp_id)], limit=1) if wp_id else False

                    if existing and not self.update_existing:
                        skipped += 1
                        continue

                    if existing:
                        existing.write(vals)
                        prop = existing
                        updated += 1
                    else:
                        prop = Property.create(vals)
                        imported += 1

                    if self.import_images:
                        self._import_images_for_property(prop, wp_prop, cfg)

            except Exception as e:
                errors.append(f"[{line.title}]: {str(e)}")
                _logger.error(f"Error importando WP post {wp_id}: {e}", exc_info=True)

        self.write({
            'import_state': 'done',
            'imported_count': imported,
            'updated_count': updated,
            'skipped_count': skipped,
            'error_log': '\n'.join(errors) if errors else False,
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'estate.wordpress.import.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_view_imported_properties(self):
        """Abre el listado de propiedades publicadas/importadas desde WordPress."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Propiedades de WordPress',
            'res_model': 'estate.property',
            'view_mode': 'list,form',
            'domain': [('wp_published', '=', True)],
            'target': 'current',
        }

