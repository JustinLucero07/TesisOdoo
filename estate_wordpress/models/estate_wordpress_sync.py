import base64
import json
import logging
import requests

from odoo import models, api

_logger = logging.getLogger(__name__)

# =============================================================================
# MAPEO AUTOMÁTICO: Odoo → Houzez WordPress (inmobi.com.ec)
# =============================================================================

# property_type taxonomy: Odoo property_type_id.name → WordPress ID
HOUZEZ_TYPE_MAP = {
    'casa': 93,
    'casas': 93,
    'casa rentera': 126,
    'casa rentera / comercial': 126,
    'comercial': 126,
    'departamento': 95,
    'departamentos': 95,
    'suite': 95,
    'edificio': 96,
    'edificios': 96,
    'finca': 97,
    'quintas': 97,
    'finca / quinta': 97,
    'fincas / quintas': 97,
    'oficina': 98,
    'oficinas': 98,
    'local comercial': 98,
    'terreno': 94,
    'terrenos': 94,
    'lote': 94,
    'propiedad': 143,
}

# property_status taxonomy: Odoo state → WordPress ID
HOUZEZ_STATUS_MAP = {
    'available': 32,    # En Venta
    'reserved': 46,     # Nuevo Listado
    'sold': 123,        # Vendido
    'rented': 31,       # En Renta
}

# property_city taxonomy: Odoo city (texto libre) → WordPress ID
HOUZEZ_CITY_MAP = {
    'azogues': 137,
    'cañar': 106,
    'canar': 106,
    'cuenca': 102,
    'loja': 138,
    'paute': 130,
    'puerto inca': 142,
    'san fernando': 144,
    'san sebastian': 139,
    'santa isabel': 139,
    'san sebastian, santa isabel': 139,
    'sigsig': 127,
}

# property_feature taxonomy: texto → WordPress ID
HOUZEZ_FEATURE_MAP = {
    'aire acondicionado': 15,
    'amplio parqueadero': 103,
    'area social': 121,
    'área social': 121,
    'armarios empotrados': 116,
    'balcon': 117,
    'balcón': 117,
    'baño auxiliar': 109,
    'bano auxiliar': 109,
    'baño en habitacion principal': 110,
    'baño en habitación principal': 110,
    'barbacoa': 19,
    'buhardilla': 104,
    'cesped': 39,
    'césped': 39,
}


class EstatePropertyWordPress(models.Model):
    _inherit = 'estate.property'

    def _get_wp_config(self):
        """Get WordPress configuration."""
        ICP = self.env['ir.config_parameter'].sudo()
        method = ICP.get_param('estate_wp.auth_method', 'basic')
        user = ICP.get_param('estate_wp.username', '')
        pwd = ICP.get_param('estate_wp.app_password', '')
        token = ICP.get_param('estate_wp.jwt_token', '')

        auth = None
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Odoo/19'
        }

        if method == 'jwt' and token:
            headers['Authorization'] = f'Bearer {token}'
        else:
            auth = (user, pwd)

        return {
            'url': ICP.get_param('estate_wp.url', '').rstrip('/'),
            'auth': auth,
            'headers': headers,
            'active': ICP.get_param('estate_wp.active', 'False'),
            'post_type': ICP.get_param('estate_wp.post_type', 'property'),
            'agent_id': ICP.get_param('estate_wp.agent_id', ''),
        }

    # -------------------------------------------------------------------------
    # AUTO-MAP TAXONOMIES
    # -------------------------------------------------------------------------
    def _get_houzez_type_ids(self):
        """Map Odoo property type name → Houzez property_type taxonomy IDs."""
        if not self.property_type_id:
            return []
        name = self.property_type_id.name.strip().lower()
        wp_id = HOUZEZ_TYPE_MAP.get(name)
        if wp_id:
            return [wp_id]
        # Partial match fallback
        for key, val in HOUZEZ_TYPE_MAP.items():
            if key in name or name in key:
                return [val]
        _logger.warning(f"No Houzez type mapping for: '{name}'. Using 'Propiedad' (143).")
        return [143]  # fallback: Propiedad

    def _get_houzez_status_ids(self):
        """Map Odoo state → Houzez property_status taxonomy IDs."""
        wp_id = HOUZEZ_STATUS_MAP.get(self.state, 32)
        return [wp_id]

    def _get_houzez_city_ids(self):
        """Map Odoo city → Houzez property_city taxonomy IDs."""
        if not self.city:
            return []
        city = self.city.strip().lower()
        wp_id = HOUZEZ_CITY_MAP.get(city)
        if wp_id:
            return [wp_id]
        # Partial match fallback
        for key, val in HOUZEZ_CITY_MAP.items():
            if key in city or city in key:
                return [val]
        _logger.warning(f"No Houzez city mapping for: '{city}'")
        return []

    # -------------------------------------------------------------------------
    # AGENT SYNC
    # -------------------------------------------------------------------------
    def _wp_find_agent_id(self, cfg, email):
        """Find Houzez Agent ID by email or name in WordPress using Search API."""
        if not email:
            return 0
        try:
            # Fallback 1: Buscar en CPT houzez_agent por email directamente (útil si el título o contenido incluyen el email)
            agent_url = f"{cfg['url']}/wp-json/wp/v2/search"
            params = {'type': 'post', 'subtype': 'houzez_agent', 'search': email, 'per_page': 1}
            resp = requests.get(agent_url, params=params, auth=cfg['auth'], headers=cfg['headers'], timeout=15)
            
            if resp.status_code == 200:
                results = resp.json()
                if results and isinstance(results, list):
                    agent_id = results[0].get('id', 0)
                    _logger.info(f"WP Agent found for {email}: ID {agent_id}")
                    return agent_id

            # Fallback 2: Buscar por nombre real del asesor en lugar del correo (las Plantillas a veces ocultan el correo al buscador)
            agent_name = self.user_id.name
            _logger.info(f"WP Agent not found by email. Try mapping exactly Name: '{agent_name}'")
            params = {'type': 'post', 'subtype': 'houzez_agent', 'search': agent_name, 'per_page': 10}
            resp = requests.get(agent_url, params=params, auth=cfg['auth'], headers=cfg['headers'], timeout=15)
            if resp.status_code == 200:
                results = resp.json()
                if results and isinstance(results, list):
                    for res in results:
                        if res.get('title', '').strip().lower() == agent_name.strip().lower():
                            agent_id = res.get('id', 0)
                            _logger.info(f"WP Agent found by Name match '{agent_name}': ID {agent_id}")
                            return agent_id

            _logger.warning(f"No WP Agent mapped automatically for '{email}' or '{agent_name}'.")
        except Exception as e:
            _logger.error(f"WP Agent Search Error: {e}")
        return 0

    # -------------------------------------------------------------------------
    # IMAGE UPLOAD
    # -------------------------------------------------------------------------
    def _wp_upload_image(self, cfg, image_data, filename):
        """Upload image to WordPress Media Library. Returns media ID."""
        try:
            raw = base64.b64decode(image_data)
            media_url = f"{cfg['url']}/wp-json/wp/v2/media"

            upload_headers = {}
            if 'Authorization' in cfg['headers']:
                upload_headers['Authorization'] = cfg['headers']['Authorization']
            upload_headers['Content-Disposition'] = f'attachment; filename="{filename}"'
            upload_headers['Content-Type'] = 'image/jpeg'

            resp = requests.post(
                media_url, data=raw, auth=cfg['auth'],
                headers=upload_headers, timeout=120)

            if resp.status_code in (200, 201):
                try:
                    media_id = resp.json().get('id', 0)
                    _logger.info(f"WP media uploaded: {filename} → ID {media_id}")
                    return media_id
                except Exception:
                    _logger.error(f"WP media upload: 200 OK but body not JSON. Content: {resp.text[:500]}")
                    return 0
            else:
                _logger.warning(f"WP media upload failed ({resp.status_code}): {resp.text[:300]}")
                return 0
        except Exception as e:
            _logger.error(f"WP media upload exception: {e}")
            return 0

    def _wp_upload_all_images(self, cfg):
        """Upload main + gallery images. Returns (featured_id, [gallery_ids])."""
        featured_id = 0
        gallery_ids = []

        if self.image_main:
            featured_id = self._wp_upload_image(
                cfg, self.image_main, f"{self.name}_portada.jpg")

        for idx, img in enumerate(self.image_ids.sorted('sequence'), 1):
            if img.image:
                safe_name = (img.name or f'img_{idx}').replace(' ', '_').replace('/', '_')
                media_id = self._wp_upload_image(
                    cfg, img.image, f"{self.name}_{safe_name}.jpg")
                if media_id:
                    gallery_ids.append(media_id)

        if not featured_id and gallery_ids:
            featured_id = gallery_ids[0]

        return featured_id, gallery_ids

    # -------------------------------------------------------------------------
    # BUILD HOUZEZ META
    # -------------------------------------------------------------------------
    def _build_houzez_meta(self, cfg, featured_id, gallery_ids):
        """Build ALL Houzez meta fields."""
        # Address
        full_address = ', '.join([p for p in [
            self.street, self.city,
            self.state_id.name if self.state_id else None,
            self.zip_code,
            self.country_id.name if self.country_id else None
        ] if p])

        # GPS
        location = ''
        lat_str = ''
        lng_str = ''
        if self.latitude and self.longitude:
            lat_str = str(self.latitude)
            lng_str = str(self.longitude)
            location = f"{self.latitude},{self.longitude},15"

        meta = {
            # --- Información ---
            'fave_property_price': str(self.price or 0),
            'fave_property_size': str(self.area or 0),
            'fave_property_size_prefix': 'm²',
            'fave_property_land': str(self.area or 0),
            'fave_property_land_postfix': 'm²',
            'fave_property_bedrooms': str(self.bedrooms or 0),
            'fave_property_rooms': str(self.bedrooms or 0),
            'fave_property_bathrooms': str(self.bathrooms or 0),
            'fave_property_garage': str(self.parking_spaces or 0),
            'fave_property_garage_size': '',
            'fave_property_year': str(self.year_built or ''),
            'fave_property_id': self.name or '',

            # --- Mapa ---
            'fave_property_map': '1' if location else '0',
            'fave_property_location': location,
            'fave_property_map_address': full_address,
            'houzez_geolocation_lat': lat_str,
            'houzez_geolocation_long': lng_str,
            'fave_property_map_street_view': 'hide',

            # --- Dirección ---
            'fave_property_address': self.street or '',
            'fave_property_zip': self.zip_code or '',

            # --- Agente ---
            'fave_agent_display_option': 'agent_info',

            # --- Config ---
            'fave_featured': '0',
            'fave_loggedintoview': '0',
            'fave_prop_homeslider': 'no',
            'fave_single_top_area': 'global',
            'fave_single_content_area': 'global',
        }

        # Agent Sync: Dynamic search or hardcoded map
        if getattr(self.user_id, 'wp_agent_id', False):
            wp_agent_id = self.user_id.wp_agent_id.wp_id
            _logger.info(f"Using explicitly mapped WP Agent ID: {wp_agent_id}")
            meta['fave_agents'] = str(wp_agent_id)
            meta['fave_agents_list'] = [str(wp_agent_id)]
        else:
            agent_email = (self.user_id.login or self.user_id.email or '').strip()
            _logger.info(f"Searching WP Agent for Odoo User: {agent_email}")
            wp_agent_id = self._wp_find_agent_id(cfg, agent_email)
            
            if wp_agent_id:
                meta['fave_agents'] = str(wp_agent_id)
                meta['fave_agents_list'] = [str(wp_agent_id)] 
            elif cfg.get('agent_id'):
                meta['fave_agents'] = cfg['agent_id']

        # Featured image
        if featured_id:
            meta['_thumbnail_id'] = str(featured_id)

        # Gallery
        if gallery_ids:
            meta['fave_property_images'] = [str(gid) for gid in gallery_ids]

        return meta

    # -------------------------------------------------------------------------
    # STEP 1: Create/Update post (title, content, taxonomies, featured)
    # -------------------------------------------------------------------------
    def _wp_create_or_update_post(self, cfg, featured_id):
        """Create or update the WP post with taxonomies."""
        type_ids = self._get_houzez_type_ids()
        status_ids = self._get_houzez_status_ids()
        city_ids = self._get_houzez_city_ids()

        post_data = {
            'title': self.title or self.name,
            'content': self.description or '',
            'status': 'publish',
        }

        if type_ids:
            post_data['property_type'] = type_ids
        if status_ids:
            post_data['property_status'] = status_ids
        if city_ids:
            post_data['property_city'] = city_ids
        if featured_id:
            post_data['featured_media'] = featured_id

        api_url = f"{cfg['url']}/wp-json/wp/v2/{cfg['post_type']}"
        headers = dict(cfg['headers'])
        headers['Content-Type'] = 'application/json'

        response = None
        if self.wp_post_id:
            response = requests.post(
                f"{api_url}/{self.wp_post_id}",
                json=post_data, auth=cfg['auth'], headers=headers, timeout=120)
            if response.status_code == 404:
                self.wp_post_id = 0
                response = None

        if not response or response.status_code == 404:
            response = requests.post(
                api_url, json=post_data, auth=cfg['auth'], headers=headers, timeout=120)

        if response.status_code in (200, 201):
            return response.json().get('id', 0)
        else:
            _logger.error(f"WP create/update error: {response.text[:500]}")
            return 0

    # -------------------------------------------------------------------------
    # STEP 2: Save meta via custom endpoint
    # -------------------------------------------------------------------------
    def _wp_save_meta(self, cfg, post_id, meta_dict):
        """Save all meta via custom Odoo REST endpoint in WordPress."""
        endpoint = f"{cfg['url']}/wp-json/odoo-houzez/v1/meta/{post_id}"
        headers = dict(cfg['headers'])
        headers['Content-Type'] = 'application/json'

        try:
            resp = requests.post(
                endpoint, json=meta_dict, auth=cfg['auth'],
                headers=headers, timeout=60)

            if resp.status_code in (200, 201):
                result = resp.json()
                _logger.info(f"WP meta saved for post {post_id}: {result.get('updated', 0)} fields")
                return True
            else:
                _logger.error(f"WP meta save error ({resp.status_code}): {resp.text[:300]}")
                return False
        except Exception as e:
            _logger.error(f"WP meta save exception: {e}")
            return False

    # -------------------------------------------------------------------------
    # STEP 3: Set taxonomies via custom endpoint (fallback)
    # -------------------------------------------------------------------------
    def _wp_set_taxonomies(self, cfg, post_id):
        """Set taxonomy terms via custom endpoint if REST API didn't work."""
        endpoint = f"{cfg['url']}/wp-json/odoo-houzez/v1/taxonomies/{post_id}"
        headers = dict(cfg['headers'])
        headers['Content-Type'] = 'application/json'

        tax_data = {
            'property_type': self._get_houzez_type_ids(),
            'property_status': self._get_houzez_status_ids(),
            'property_city': self._get_houzez_city_ids(),
        }

        try:
            resp = requests.post(
                endpoint, json=tax_data, auth=cfg['auth'],
                headers=headers, timeout=30)
            if resp.status_code in (200, 201):
                _logger.info(f"WP taxonomies set for post {post_id}")
                return True
            else:
                _logger.warning(f"WP taxonomy endpoint not available ({resp.status_code})")
                return False
        except Exception as e:
            _logger.warning(f"WP taxonomy set exception: {e}")
            return False

    # -------------------------------------------------------------------------
    # MAIN PUBLISH ACTION
    # -------------------------------------------------------------------------
    def action_publish_wordpress(self):
        """Publish property to WordPress/Houzez — full auto-mapped integration."""
        self.ensure_one()
        cfg = self._get_wp_config()

        if cfg['active'] != 'True':
            return self._show_notification(
                '⚠️ Integración desactivada', 'Activar en Ajustes → WordPress')
        if not cfg['url']:
            return self._show_notification(
                '⚠️ Configuración incompleta', 'Falta la URL de WordPress.')

        try:
            # --- Step 1: Upload images ---
            featured_id, gallery_ids = self._wp_upload_all_images(cfg)

            # --- Step 2: Create/update post with taxonomies ---
            wp_id = self._wp_create_or_update_post(cfg, featured_id)
            if not wp_id:
                return self._show_notification(
                    '❌ Error', 'No se pudo crear la propiedad en WordPress.')

            # --- Step 3: Save ALL Houzez meta fields ---
            meta = self._build_houzez_meta(cfg, featured_id, gallery_ids)
            meta_saved = self._wp_save_meta(cfg, wp_id, meta)

            # --- Step 4: Fallback taxonomy assignment ---
            self._wp_set_taxonomies(cfg, wp_id)

            # --- Update Odoo ---
            self.write({'wp_post_id': wp_id, 'wp_published': True})

            # --- Build result ---
            type_name = self.property_type_id.name if self.property_type_id else '?'
            city_name = self.city or '?'
            info = [
                f"ID: {wp_id}",
                f"Tipo: {type_name}",
                f"Ciudad: {city_name}",
            ]
            if gallery_ids:
                info.append(f"{len(gallery_ids)} imgs")
            if featured_id:
                info.append("Portada ")
            if self.latitude and self.longitude:
                info.append("Mapa ")
            if meta_saved:
                info.append("Meta ")

            return self._show_notification(
                ' Publicado en WordPress', ' | '.join(info))

        except Exception as e:
            _logger.error(f"WordPress publish error: {str(e)}")
            return self._show_notification('❌ Error de conexión', str(e))

    # -------------------------------------------------------------------------
    # UNPUBLISH
    # -------------------------------------------------------------------------
    def action_unpublish_wordpress(self):
        self.ensure_one()
        cfg = self._get_wp_config()
        if self.wp_post_id:
            try:
                # WP requires ?force=true to delete custom post types that don't support Trash.
                api_url = f"{cfg['url']}/wp-json/wp/v2/{cfg['post_type']}/{self.wp_post_id}?force=true"
                headers = dict(cfg['headers'])
                headers['Content-Type'] = 'application/json'
                
                response = requests.delete(
                    api_url, auth=cfg['auth'], headers=headers, timeout=30)
                    
                if response.status_code in (200, 204):
                    self.write({'wp_post_id': 0, 'wp_published': False})
                    return self._show_notification('✅ Eliminado de WordPress', 'La propiedad fue borrada exitosamente.')
                elif response.status_code == 404:
                    # If it's already gone from WP, just clear it locally.
                    self.write({'wp_post_id': 0, 'wp_published': False})
                    return self._show_notification('✅ Sincronizado', 'La propiedad ya había sido eliminada en WordPress, se desenlazó en Odoo.')
                else:
                    error_msg = f"No se pudo eliminar en WP. Código {response.status_code}: {response.text[:100]}"
                    _logger.error(error_msg)
                    return self._show_notification('❌ Error al Eliminar', error_msg)
            except Exception as e:
                _logger.error(f"WordPress unpublish error: {str(e)}")
                return self._show_notification('❌ Error de conexión', str(e))
        else:
            self.write({'wp_published': False})
            return self._show_notification('✅ Acción completada', 'Se marcó como no publicado localmente (no existía en WP).')

    def _show_notification(self, title, message):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'sticky': False,
                'type': 'info',
            }
        }
