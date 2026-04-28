import logging
import requests

from odoo import models, fields, api

_logger = logging.getLogger(__name__)

META_API_VERSION = 'v25.0'

# Métricas disponibles para posts de página en Facebook
FB_POST_METRICS = (
    'post_impressions,'
    'post_impressions_unique,'
    'post_clicks,'
    'post_reactions_like_total,'
    'post_reactions_love_total,'
    'post_reactions_wow_total,'
    'post_reactions_haha_total'
)


class EstateFacebookStats(models.Model):
    """
    Estadísticas de Facebook por publicación vinculada a una propiedad.
    Se obtienen consultando la Meta Graph API con el fb_post_id guardado.
    """
    _name = 'estate.facebook.stats'
    _description = 'Estadísticas Facebook por Propiedad'
    _order = 'stats_date desc, id desc'
    _rec_name = 'property_id'

    property_id = fields.Many2one(
        'estate.property', string='Propiedad', required=True, ondelete='cascade')
    fb_post_id = fields.Char(string='Facebook Post ID', readonly=True)
    stats_date = fields.Datetime(
        string='Última Actualización', default=fields.Datetime.now, readonly=True)

    # ── Alcance e Impresiones ─────────────────────────────────────
    impressions = fields.Integer(
        string='Impresiones', readonly=True,
        help='Total de veces que el post fue mostrado (incluyendo múltiples vistas del mismo usuario).')
    reach = fields.Integer(
        string='Alcance Único', readonly=True,
        help='Número de personas únicas que vieron el post.')

    # ── Interacciones ────────────────────────────────────────────
    clicks = fields.Integer(
        string='Clics', readonly=True,
        help='Total de clics en el post (link, foto, nombre, etc.).')
    likes = fields.Integer(
        string='Me Gusta', readonly=True)
    loves = fields.Integer(
        string='Me Encanta', readonly=True)
    hahas = fields.Integer(
        string='Jajá', readonly=True)
    wows = fields.Integer(
        string='Asombro', readonly=True)
    total_reactions = fields.Integer(
        string='Total Reacciones', compute='_compute_totals', store=True,
        help='Suma de todas las reacciones: Me Gusta + Me Encanta + Jajá + Asombro.')
    shares = fields.Integer(
        string='Compartidos', readonly=True)

    # ── Métricas calculadas ───────────────────────────────────────
    engagement_rate = fields.Float(
        string='Tasa de Engagement (%)', compute='_compute_totals', store=True,
        digits=(5, 2),
        help='(Reacciones + Clics + Compartidos) / Alcance × 100.')
    ctr = fields.Float(
        string='CTR (%)', compute='_compute_totals', store=True,
        digits=(5, 2),
        help='Click-Through Rate: Clics / Impresiones × 100.')

    # ── Estado ────────────────────────────────────────────────────
    fetch_error = fields.Char(string='Error al obtener datos', readonly=True)

    @api.depends('likes', 'loves', 'hahas', 'wows', 'clicks', 'shares', 'reach', 'impressions')
    def _compute_totals(self):
        for rec in self:
            rec.total_reactions = (rec.likes or 0) + (rec.loves or 0) + (rec.hahas or 0) + (rec.wows or 0)
            total_interactions = rec.total_reactions + (rec.clicks or 0) + (rec.shares or 0)
            rec.engagement_rate = (total_interactions / rec.reach * 100) if rec.reach else 0.0
            rec.ctr = (rec.clicks / rec.impressions * 100) if rec.impressions else 0.0

    def action_refresh(self):
        """Actualiza las estadísticas desde la Meta Graph API."""
        for rec in self:
            rec._fetch_stats()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Facebook Stats',
                'message': f'Estadísticas actualizadas para {len(self)} publicaciones.',
                'type': 'success',
            },
        }

    def _fetch_stats(self):
        """Consulta la Graph API y guarda las métricas en este registro."""
        ICP = self.env['ir.config_parameter'].sudo()
        token = ICP.get_param('estate_social.facebook_page_token', '')
        if not token:
            self.fetch_error = 'No hay Page Access Token configurado (Ajustes → Redes Sociales).'
            return

        post_id = self.fb_post_id or (self.property_id.fb_post_id if self.property_id else '')
        if not post_id:
            self.fetch_error = 'La propiedad no tiene Facebook Post ID. Publica primero en Facebook.'
            return

        try:
            resp = requests.get(
                f'https://graph.facebook.com/{META_API_VERSION}/{post_id}/insights',
                params={
                    'metric': FB_POST_METRICS,
                    'access_token': token,
                },
                timeout=15,
            )
            data = resp.json()

            if resp.status_code != 200 or 'error' in data:
                err = data.get('error', {}).get('message', str(data))
                self.fetch_error = f'Error API: {err}'
                _logger.warning('Facebook stats error para %s: %s', post_id, err)
                return

            # Parsear métricas: la API retorna lista con {name, values: [{value: N}]}
            metric_map = {}
            for item in data.get('data', []):
                values = item.get('values', [{}])
                metric_map[item['name']] = values[0].get('value', 0) if values else 0

            # También buscar compartidos desde el endpoint de shares (campo diferente)
            shares_count = 0
            try:
                shares_resp = requests.get(
                    f'https://graph.facebook.com/{META_API_VERSION}/{post_id}',
                    params={'fields': 'shares', 'access_token': token},
                    timeout=10,
                )
                if shares_resp.status_code == 200:
                    shares_count = shares_resp.json().get('shares', {}).get('count', 0)
            except Exception:
                pass

            self.write({
                'fb_post_id': post_id,
                'impressions': metric_map.get('post_impressions', 0),
                'reach': metric_map.get('post_impressions_unique', 0),
                'clicks': metric_map.get('post_clicks', 0),
                'likes': metric_map.get('post_reactions_like_total', 0),
                'loves': metric_map.get('post_reactions_love_total', 0),
                'hahas': metric_map.get('post_reactions_haha_total', 0),
                'wows': metric_map.get('post_reactions_wow_total', 0),
                'shares': shares_count,
                'stats_date': fields.Datetime.now(),
                'fetch_error': False,
            })

        except Exception as e:
            self.fetch_error = f'Error de conexión: {e}'
            _logger.error('Error obteniendo Facebook stats: %s', e)

    @api.model
    def _cron_refresh_all_stats(self):
        """Cron diario: actualiza stats de todas las propiedades publicadas en Facebook."""
        all_stats = self.search([('property_id.fb_published', '=', True)])
        for rec in all_stats:
            try:
                rec._fetch_stats()
            except Exception as e:
                _logger.warning('Error actualizando FB stats de %s: %s', rec.property_id.name, e)
