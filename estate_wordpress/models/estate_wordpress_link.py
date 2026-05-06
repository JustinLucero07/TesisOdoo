import logging
import re

import requests

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class EstateWordpressLinkWizard(models.TransientModel):
    _name = 'estate.wordpress.link.wizard'
    _description = 'Enlazar Propiedad con WordPress'

    # --- Selección ---
    property_id = fields.Many2one(
        'estate.property', string='Propiedad en Odoo', required=True,
        domain="[('wp_published', '=', False)]",
        help='Selecciona la propiedad de Odoo que quieres vincular a un post de WordPress.')

    wp_post_id = fields.Integer(
        string='Post ID de WordPress', required=True,
        help='ID del post en WordPress. Lo encuentras editando la propiedad en WordPress: '
             'la URL contiene ?post=XXXX, ese número es el ID.')

    # --- Preview (datos leídos desde WP) ---
    wp_title = fields.Char(string='Título en WordPress', readonly=True)
    wp_price = fields.Float(string='Precio en WordPress', readonly=True)
    wp_area = fields.Float(string='Área en WordPress', readonly=True)
    wp_bedrooms = fields.Integer(string='Habitaciones en WordPress', readonly=True)
    wp_status = fields.Char(string='Estado en WordPress', readonly=True)
    wp_preview_loaded = fields.Boolean(default=False)

    # --- Comparación ---
    odoo_title = fields.Char(string='Título en Odoo', related='property_id.title', readonly=True)
    odoo_price = fields.Float(string='Precio en Odoo', related='property_id.price', readonly=True)
    odoo_area = fields.Float(string='Área en Odoo', related='property_id.area', readonly=True)
    odoo_bedrooms = fields.Integer(string='Habitaciones en Odoo', related='property_id.bedrooms', readonly=True)

    # --- Opciones ---
    sync_data = fields.Selection([
        ('link_only', 'Solo vincular (no modificar datos de Odoo)'),
        ('import_wp', 'Vincular + Importar datos de WordPress a Odoo'),
    ], string='Modo de Enlace', default='link_only', required=True,
       help='Solo vincular: marca la propiedad como enlazada sin cambiar datos.\n'
            'Importar datos: además actualiza la propiedad de Odoo con los datos actuales de WordPress.')

    # --- Estado ---
    wizard_state = fields.Selection([
        ('select', 'Selección'),
        ('preview', 'Preview'),
        ('done', 'Completado'),
    ], default='select', string='Paso')

    result_message = fields.Text(string='Resultado', readonly=True)

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _get_wp_cfg(self):
        """Obtiene la configuración WordPress desde ir.config_parameter."""
        ICP = self.env['ir.config_parameter'].sudo()
        method = ICP.get_param('estate_wp.auth_method', 'basic')
        user = ICP.get_param('estate_wp.username', '')
        pwd = ICP.get_param('estate_wp.app_password', '')
        token = ICP.get_param('estate_wp.jwt_token', '')

        headers = {'User-Agent': 'Odoo/19 EstateLink/1.0'}
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
    # ACCIONES
    # =========================================================================

    def action_preview(self):
        """Busca el post en WordPress y muestra los datos para comparación."""
        self.ensure_one()
        cfg = self._get_wp_cfg()

        if cfg['active'] != 'True':
            raise UserError('La integración WordPress no está activa. Actívala en Ajustes → Integración WordPress.')
        if not cfg['url']:
            raise UserError('Falta configurar la URL de WordPress en Ajustes → Integración WordPress.')
        if not self.wp_post_id:
            raise UserError('Ingresa el Post ID de WordPress que quieres vincular.')

        # Verificar que no esté ya enlazada a otra propiedad
        existing = self.env['estate.property'].search([
            ('wp_post_id', '=', self.wp_post_id),
            ('wp_published', '=', True),
        ], limit=1)
        if existing:
            raise UserError(
                f'El Post ID {self.wp_post_id} ya está enlazado a la propiedad '
                f'"{existing.title}" (Ref: {existing.name}). '
                f'Desvincula esa propiedad primero si quieres reasignar el enlace.')

        # Fetch del post desde WordPress
        try:
            api_url = f"{cfg['url']}/wp-json/wp/v2/{cfg['post_type']}/{self.wp_post_id}"
            params = {'_embed': 1, 'context': 'edit'}
            resp = requests.get(
                api_url, params=params,
                auth=cfg['auth'], headers=cfg['headers'], timeout=20)

            if resp.status_code == 404:
                raise UserError(
                    f'No se encontró un post con ID {self.wp_post_id} en WordPress.\n'
                    f'Verifica que el ID sea correcto y que el post type sea "{cfg["post_type"]}".')
            if resp.status_code != 200:
                raise UserError(
                    f'Error al consultar WordPress. Código {resp.status_code}: {resp.text[:200]}')

            wp_prop = resp.json()
        except requests.RequestException as e:
            raise UserError(f'Error de conexión con WordPress: {str(e)}')

        # Extraer datos del post para preview
        raw_title = wp_prop.get('title', {}).get('rendered', '')
        title = re.sub(r'<[^>]+>', '', raw_title).strip() or 'Sin título'

        # Obtener meta usando la cascada completa del import wizard
        ImportWizard = self.env['estate.wordpress.import.wizard']
        wizard = ImportWizard.create({'max_properties': 1})
        extra_meta = wizard._fetch_single_post_meta(cfg, self.wp_post_id)
        get_meta = wizard._get_meta_getter(wp_prop, extra_meta)

        price = ImportWizard._safe_float(get_meta('fave_property_price'))
        area = ImportWizard._safe_float(
            get_meta('fave_property_size') or get_meta('fave_property_land'))
        bedrooms = ImportWizard._safe_int(
            get_meta('fave_property_bedrooms') or get_meta('fave_property_rooms'))

        status = wp_prop.get('status', 'desconocido')

        self.write({
            'wp_title': title,
            'wp_price': price,
            'wp_area': area,
            'wp_bedrooms': bedrooms,
            'wp_status': status,
            'wp_preview_loaded': True,
            'wizard_state': 'preview',
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_link(self):
        """Enlaza la propiedad de Odoo con el post de WordPress."""
        self.ensure_one()

        if not self.property_id:
            raise UserError('Selecciona una propiedad de Odoo.')
        if not self.wp_post_id:
            raise UserError('Especifica el Post ID de WordPress.')

        prop = self.property_id

        # Marcar enlace
        link_vals = {
            'wp_post_id': self.wp_post_id,
            'wp_published': True,
            'wp_unlinked': False,
        }

        changes_applied = []

        if self.sync_data == 'import_wp':
            # Importar datos de WP a Odoo
            cfg = self._get_wp_cfg()
            try:
                api_url = f"{cfg['url']}/wp-json/wp/v2/{cfg['post_type']}/{self.wp_post_id}"
                params = {'_embed': 1, 'context': 'edit'}
                resp = requests.get(
                    api_url, params=params,
                    auth=cfg['auth'], headers=cfg['headers'], timeout=30)

                if resp.status_code == 200:
                    wp_prop = resp.json()
                    ImportWizard = self.env['estate.wordpress.import.wizard']
                    wizard = ImportWizard.create({'max_properties': 1})
                    extra_meta = wizard._fetch_single_post_meta(cfg, self.wp_post_id)
                    import_vals = wizard._map_wp_to_vals(wp_prop, extra_meta)

                    # Preservar campos de enlace (los ponemos nosotros)
                    import_vals.pop('wp_post_id', None)
                    import_vals.pop('wp_published', None)

                    # Registrar cambios
                    for key in ['price', 'area', 'bedrooms', 'bathrooms', 'street', 'city', 'title']:
                        old = getattr(prop, key, None)
                        new = import_vals.get(key)
                        if new is not None and str(old) != str(new):
                            changes_applied.append(f"• {key}: {old} → {new}")

                    link_vals.update(import_vals)
            except Exception as e:
                _logger.warning(f"No se pudo importar datos de WP durante enlace: {e}")

        prop.with_context(no_wp_sync=True).write(link_vals)

        # Registrar en chatter
        mode_label = 'Solo enlazado' if self.sync_data == 'link_only' else 'Enlazado + datos importados'
        body = (f'<p><strong>🔗 Enlazado manualmente con WordPress</strong></p>'
                f'<p>Post ID: {self.wp_post_id} | Modo: {mode_label}</p>')
        if changes_applied:
            body += '<pre>' + '\n'.join(changes_applied) + '</pre>'
        prop.message_post(body=body, message_type='notification')

        result_msg = f'✅ Propiedad "{prop.title}" enlazada exitosamente al post WordPress ID {self.wp_post_id}.'
        if changes_applied:
            result_msg += f'\n{len(changes_applied)} campo(s) actualizados desde WordPress.'

        self.write({
            'wizard_state': 'done',
            'result_message': result_msg,
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_back_to_select(self):
        """Vuelve al paso de selección."""
        self.ensure_one()
        self.write({
            'wizard_state': 'select',
            'wp_preview_loaded': False,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
