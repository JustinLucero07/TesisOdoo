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
        ('done', 'Completado'),
    ], default='draft', string='Estado')

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

    def _fetch_single_post_meta(self, cfg, wp_post_id):
        """
        Intenta obtener los meta de un post individual por varias rutas.
        Retorna dict con todos los meta encontrados (puede estar vacío).
        """
        post_type = cfg['post_type']
        combined = {}

        # Ruta 1: individual con context=edit y campos explícitos
        try:
            url = f"{cfg['url']}/wp-json/wp/v2/{post_type}/{wp_post_id}"
            resp = requests.get(
                url,
                params={'context': 'edit', '_fields': 'id,meta,acf'},
                auth=cfg['auth'], headers=cfg['headers'],
                timeout=20,
            )
            if resp.status_code == 200:
                data = resp.json()
                combined.update(data.get('meta', {}) or {})
                combined.update(data.get('acf', {}) or {})
        except Exception as e:
            _logger.debug("Meta individual fetch (ruta 1) falló para post %s: %s", wp_post_id, e)

        # Ruta 2: endpoint custom Houzez si existe
        houzez_routes = [
            f"{cfg['url']}/wp-json/houzez/v1/property-meta/{wp_post_id}",
            f"{cfg['url']}/wp-json/houzez/v1/properties/{wp_post_id}",
        ]
        for route in houzez_routes:
            try:
                resp = requests.get(
                    route, auth=cfg['auth'], headers=cfg['headers'], timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, dict):
                        combined.update({k: v for k, v in data.items() if v not in (None, '')})
                    break
            except Exception:
                pass

        # Ruta 3: /wp-json/wp/v2/{post_type}/{id} con _fields=meta solo
        if not combined:
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
                    combined.update(data.get('meta', {}) or {})
                    combined.update(data.get('acf', {}) or {})
                    # A veces los meta vienen a primer nivel con prefijo fave_
                    for key, val in data.items():
                        if key.startswith(('fave_', 'houzez_', 'property_')):
                            combined.setdefault(key, val)
            except Exception as e:
                _logger.debug("Meta individual fetch (ruta 3) falló para post %s: %s", wp_post_id, e)

        return combined

    def _get_meta_getter(self, wp_prop, extra_meta=None):
        """Retorna una función para obtener campos meta con fallback a acf y extra_meta."""
        meta = wp_prop.get('meta', {}) or {}
        acf = wp_prop.get('acf', {}) or {}
        extra = extra_meta or {}

        def get_meta(key, default=''):
            # Prioridad: meta directo → acf → extra_meta (fetch individual)
            for source in (meta, acf, extra):
                val = source.get(key)
                if val is not None:
                    if isinstance(val, list):
                        val = val[0] if val else None
                    if val not in (None, '', False):
                        return val
            return default

        return get_meta

    def _get_taxonomy_term_ids(self, wp_prop, taxonomy_name):
        """Extrae IDs de términos de una taxonomía desde _embedded."""
        try:
            terms_groups = wp_prop.get('_embedded', {}).get('wp:term', [])
            for group in terms_groups:
                for term in group:
                    if term.get('taxonomy') == taxonomy_name:
                        return [t['id'] for t in group if t.get('taxonomy') == taxonomy_name]
        except Exception:
            pass
        return []

    # =========================================================================
    # MAPEO WP → ODOO VALS
    # =========================================================================

    @staticmethod
    def _safe_float(val, default=0.0):
        try:
            return float(str(val).replace(',', '.').strip()) if val else default
        except Exception:
            return default

    @staticmethod
    def _safe_int(val, default=0):
        try:
            return int(float(str(val).strip())) if val else default
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
        """Convierte un dict de propiedad WP a vals para estate.property."""
        get_meta = self._get_meta_getter(wp_prop, extra_meta)

        # --- Título ---
        raw_title = wp_prop.get('title', {}).get('rendered', '')
        title = re.sub(r'<[^>]+>', '', raw_title).strip() or 'Propiedad sin título'

        # --- Descripción (HTML conservado) ---
        description = wp_prop.get('content', {}).get('rendered', '')

        # --- Campos numéricos ---
        price = self._safe_float(get_meta('fave_property_price'))
        area = self._safe_float(get_meta('fave_property_size'))
        bedrooms = self._safe_int(get_meta('fave_property_bedrooms'))
        bathrooms = self._safe_float(get_meta('fave_property_bathrooms'))
        parking = self._safe_int(get_meta('fave_property_garage'))
        year_raw = self._safe_int(get_meta('fave_property_year'))

        # --- Ubicación ---
        street = get_meta('fave_property_address')
        zip_code = get_meta('fave_property_zip')
        lat = (self._safe_float(get_meta('houzez_geolocation_lat'))
               or self._safe_float(get_meta('fave_latitude')))
        lng = (self._safe_float(get_meta('houzez_geolocation_long'))
               or self._safe_float(get_meta('fave_longitude')))

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

        # Mapear tipo de propiedad desde taxonomía WP
        property_type_id = False
        for tid in type_tax_ids:
            type_name = WP_TYPE_TO_ODOO.get(tid)
            if type_name:
                property_type_id = self._get_or_create_property_type(type_name).id
                break

        # Fallback 1: detectar tipo desde el nombre del término de taxonomía
        if not property_type_id:
            try:
                terms_groups = wp_prop.get('_embedded', {}).get('wp:term', [])
                for group in terms_groups:
                    for term in group:
                        if term.get('taxonomy') == 'property-type':
                            term_name = term.get('name', '').strip()
                            if term_name:
                                property_type_id = self._get_or_create_property_type(term_name).id
                                break
                    if property_type_id:
                        break
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

    def action_import(self):
        """Importa propiedades desde WordPress y crea/actualiza registros en Odoo."""
        self.ensure_one()
        cfg = self._get_wp_cfg()

        if cfg['active'] != 'True':
            raise UserError(
                'La integración WordPress no está activa.\n'
                'Actívala en Ajustes → Integración WordPress.')
        if not cfg['url']:
            raise UserError('Falta configurar la URL de WordPress en Ajustes → Integración WordPress.')

        wp_props = self._fetch_all_wp_properties(cfg)
        if not wp_props:
            raise UserError(
                'No se encontraron propiedades en WordPress.\n'
                'Verifica la URL, credenciales y que el post type sea correcto.')

        Property = self.env['estate.property']
        imported = updated = skipped = 0
        errors = []

        for wp_prop in wp_props:
            wp_id = wp_prop.get('id', 0)
            raw_title = wp_prop.get('title', {}).get('rendered', f'Post {wp_id}')
            display_title = re.sub(r'<[^>]+>', '', raw_title).strip()

            try:
                with self.env.cr.savepoint():
                    # Si los meta del bulk-fetch parecen vacíos, pedir el post individualmente
                    extra_meta = {}
                    if wp_id and self._meta_looks_empty(wp_prop):
                        extra_meta = self._fetch_single_post_meta(cfg, wp_id)

                    vals = self._map_wp_to_vals(wp_prop, extra_meta)

                    existing = (
                        Property.search([('wp_post_id', '=', wp_id)], limit=1)
                        if wp_id else False
                    )

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
                errors.append(f"[{display_title}]: {str(e)}")
                _logger.error(f"Error importando WP post {wp_id}: {e}", exc_info=True)

        self.write({
            'import_state': 'done',
            'imported_count': imported,
            'updated_count': updated,
            'skipped_count': skipped,
            'error_log': '\n'.join(errors) if errors else False,
        })

        # Reabrir el wizard para mostrar resultados
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
