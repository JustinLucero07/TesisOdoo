from odoo import models, fields


class EstateWordPressConfig(models.TransientModel):
    _inherit = 'res.config.settings'

    wp_url = fields.Char(
        string='URL de WordPress',
        config_parameter='estate_wp.url',
        help='URL base de WordPress (ej: https://miinmobiliaria.com)')

    wp_username = fields.Char(
        string='Usuario WordPress',
        config_parameter='estate_wp.username')

    wp_app_password = fields.Char(
        string='Contraseña / App Pass',
        config_parameter='estate_wp.app_password',
        help='Contraseña normal (si usa JWT) o de Aplicación (si usa Básico)')

    wp_auth_method = fields.Selection([
        ('basic', 'Contraseña de Aplicación (Básico)'),
        ('jwt', 'JSON Web Token (JWT) - Recomendado'),
    ], string='Método de Autenticación', config_parameter='estate_wp.auth_method', default='basic')

    wp_jwt_token = fields.Char(
        string='Token JWT Actual',
        config_parameter='estate_wp.jwt_token',
        help='Token generado automáticamente tras probar la conexión.')

    wp_active = fields.Boolean(
        string='Integración WordPress Activa',
        config_parameter='estate_wp.active',
        default=False)

    wp_category_id = fields.Integer(
        string='Categoría WordPress (solo para Posts)',
        config_parameter='estate_wp.category_id',
        help='Solo aplica si usas Post Type "posts". Para Houzez (property), dejar en 0.')

    wp_post_type = fields.Char(
        string='WordPress Post Type',
        config_parameter='estate_wp.post_type',
        default='property',
        help='Para Houzez usar: property')

    # --- Houzez Taxonomy IDs ---
    wp_property_type_id = fields.Char(
        string='ID Tipo Propiedad (Houzez)',
        config_parameter='estate_wp.property_type_id',
        help='ID de la taxonomía property_type en Houzez (ej: 93=Casas, 95=Departamentos). Separar múltiples con coma.')

    wp_property_status_id = fields.Char(
        string='ID Estado Propiedad (Houzez)',
        config_parameter='estate_wp.property_status_id',
        help='ID de la taxonomía property_status (ej: 32=En Venta, 123=Vendido)')

    wp_property_city_id = fields.Char(
        string='ID Ciudad (Houzez)',
        config_parameter='estate_wp.property_city_id',
        help='ID de la taxonomía property_city (ej: 102=Cuenca)')

    wp_agent_id = fields.Char(
        string='ID Agente en WordPress',
        config_parameter='estate_wp.agent_id',
        help='ID del agente en Houzez (consultar en WordPress → Agentes)')

    wp_webhook_secret = fields.Char(
        string='Token Secreto (Webhook)',
        config_parameter='estate_wp.webhook_secret',
        help='Clave secreta que debe incluir WordPress al enviar formularios a Odoo. '
             'Coloca el mismo valor en el plugin de WordPress.')

    def action_wp_test_connection(self):
        """Prueba la conexión y obtiene el token si es necesario."""
        import requests
        self.ensure_one()

        url = self.wp_url.rstrip('/')
        user = self.wp_username
        pwd = self.wp_app_password

        if self.wp_auth_method == 'jwt':
            token_url = f"{url}/wp-json/jwt-auth/v1/token"
            try:
                resp = requests.post(token_url, json={'username': user, 'password': pwd}, timeout=15)
                if resp.status_code == 200:
                    token = resp.json().get('token')
                    self.env['ir.config_parameter'].sudo().set_param('estate_wp.jwt_token', token)
                    return self._msg('Conexión JWT Exitosa', f'Token obtenido correctamente: {token[:15]}...')
                else:
                    return self._msg('Error JWT', f'Código {resp.status_code}: {resp.text}')
            except Exception as e:
                return self._msg('Error de Conexión', str(e))
        else:
            test_url = f"{url}/wp-json/wp/v2/posts?per_page=1"
            try:
                resp = requests.get(test_url, auth=(user, pwd), timeout=15)
                if resp.status_code == 200:
                    return self._msg('Conexión Básica Exitosa', 'Credenciales válidas.')
                else:
                    return self._msg('Error de Autenticación', f'Código {resp.status_code}')
            except Exception as e:
                return self._msg('Error de Conexión', str(e))

    def action_fetch_wp_agents(self):
        import requests
        self.ensure_one()
        url = self.wp_url.rstrip('/')
        user = self.wp_username
        pwd = self.wp_app_password
        
        auth = None
        headers = {}
        if self.wp_auth_method == 'jwt':
            token = self.env['ir.config_parameter'].sudo().get_param('estate_wp.jwt_token', '')
            if token:
                headers['Authorization'] = f'Bearer {token}'
        else:
            auth = (user, pwd)
            
        # Forzar búsqueda a través de WP Search API que expone a los Custom Post Types nativamente
        agents_url = f"{url}/wp-json/wp/v2/search?type=post&subtype=houzez_agent&per_page=100"
        headers['User-Agent'] = 'Mozilla/5.0 Chrome Odoo'

        try:
            resp = requests.get(agents_url, auth=auth, headers=headers, timeout=15)
            if resp.status_code == 200:
                agents = resp.json()
                count = 0
                for ag in agents:
                    wp_id = ag.get('id')
                    # en /search el campo de título viene directo
                    name = ag.get('title', 'Desconocido')
                    
                    existing = self.env['estate.wp.agent'].search([('wp_id', '=', wp_id)])
                    if not existing:
                        self.env['estate.wp.agent'].create({'wp_id': wp_id, 'name': name})
                        count += 1
                    else:
                        existing.write({'name': name})
                return self._msg('Agentes Houzez Sincronizados', f'Se descargaron {len(agents)} agentes reales de Houzez ({count} nuevos). Recuerda ir a tus Preferencias para asignar este Agente WP y poder publicar sin errores.')
            else:
                return self._msg('Error', f'No se pudieron cargar los agentes. Código {resp.status_code}')
        except Exception as e:
            return self._msg('Error de Conexión', str(e))

    def _msg(self, title, message):
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
