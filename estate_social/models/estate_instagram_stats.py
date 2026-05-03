import logging

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.addons.estate_management.tools.http_retry import request_with_retry

_logger = logging.getLogger(__name__)

META_API_VERSION = 'v25.0'

# Métricas disponibles para posts de imagen/video en Instagram Business
IG_MEDIA_METRICS = 'impressions,reach,likes,comments,shares,saved,total_interactions'


class EstateInstagramStats(models.Model):
    """
    Estadísticas de Instagram por publicación vinculada a una propiedad.
    Se obtienen consultando la Meta Graph API con el ig_post_id guardado.
    """
    _name = 'estate.instagram.stats'
    _description = 'Estadísticas Instagram por Propiedad'
    _order = 'stats_date desc, id desc'
    _rec_name = 'property_id'

    property_id = fields.Many2one(
        'estate.property', string='Propiedad', required=True, ondelete='cascade')
    ig_post_id = fields.Char(string='Instagram Post ID', readonly=True)
    stats_date = fields.Datetime(
        string='Última Actualización', default=fields.Datetime.now, readonly=True)

    # ── Métricas principales ──────────────────────────────────────
    impressions = fields.Integer(
        string='Impresiones', readonly=True,
        help='Número total de veces que el post fue visto (incluye múltiples vistas del mismo usuario).')
    reach = fields.Integer(
        string='Alcance', readonly=True,
        help='Número de cuentas únicas que vieron el post al menos una vez.')
    likes = fields.Integer(
        string='Me gusta', readonly=True,
        help='Número de likes en la publicación.')
    comments = fields.Integer(
        string='Comentarios', readonly=True,
        help='Número de comentarios en la publicación.')
    shares = fields.Integer(
        string='Compartidos', readonly=True,
        help='Número de veces que el post fue compartido vía DM o Stories.')
    saves = fields.Integer(
        string='Guardados', readonly=True,
        help='Número de veces que los usuarios guardaron el post en su colección.')
    total_interactions = fields.Integer(
        string='Interacciones Totales', readonly=True,
        help='Suma de likes + comentarios + compartidos + guardados.')

    # ── Métricas calculadas ───────────────────────────────────────
    engagement_rate = fields.Float(
        string='Tasa de Engagement (%)', compute='_compute_engagement', store=True, digits=(5, 2),
        help='(Interacciones totales / Alcance) × 100. Mide qué tan relevante fue el post para quienes lo vieron.')
    reach_rate = fields.Float(
        string='Tasa de Alcance (%)', compute='_compute_engagement', store=True, digits=(5, 2),
        help='(Alcance / Impresiones) × 100. Mayor % indica menos re-visualizaciones del mismo usuario.')

    # ── Estado ────────────────────────────────────────────────────
    fetch_error = fields.Char(string='Error al obtener datos', readonly=True)

    @api.depends('total_interactions', 'reach', 'impressions')
    def _compute_engagement(self):
        for rec in self:
            if rec.reach and rec.reach > 0:
                rec.engagement_rate = (rec.total_interactions / rec.reach) * 100
            else:
                rec.engagement_rate = 0.0
            if rec.impressions and rec.impressions > 0:
                rec.reach_rate = (rec.reach / rec.impressions) * 100
            else:
                rec.reach_rate = 0.0

    def action_refresh(self):
        """Actualiza las estadísticas desde la Meta Graph API."""
        for rec in self:
            rec._fetch_stats()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Instagram Stats',
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

        post_id = self.ig_post_id or (self.property_id.ig_post_id if self.property_id else '')
        if not post_id:
            self.fetch_error = 'La propiedad no tiene un Instagram Post ID. Publica primero en Instagram.'
            return

        try:
            resp = request_with_retry(
                'GET',
                f'https://graph.facebook.com/{META_API_VERSION}/{post_id}/insights',
                params={
                    'metric': IG_MEDIA_METRICS,
                    'access_token': token,
                },
                timeout=15, retries=3,
            )
            data = resp.json()

            if resp.status_code != 200 or 'error' in data:
                err = data.get('error', {}).get('message', str(data))
                self.fetch_error = f'Error API: {err}'
                _logger.warning('Instagram stats error para %s: %s', post_id, err)
                return

            # Parsear las métricas devueltas
            metric_map = {item['name']: item.get('values', [{}])[0].get('value', 0)
                          for item in data.get('data', [])}

            self.write({
                'ig_post_id': post_id,
                'impressions': metric_map.get('impressions', 0),
                'reach': metric_map.get('reach', 0),
                'likes': metric_map.get('likes', 0),
                'comments': metric_map.get('comments', 0),
                'shares': metric_map.get('shares', 0),
                'saves': metric_map.get('saved', 0),
                'total_interactions': metric_map.get('total_interactions',
                    metric_map.get('likes', 0) + metric_map.get('comments', 0) +
                    metric_map.get('shares', 0) + metric_map.get('saved', 0)),
                'stats_date': fields.Datetime.now(),
                'fetch_error': False,
            })
        except Exception as e:
            self.fetch_error = f'Error de conexión: {e}'
            _logger.error('Error obteniendo Instagram stats: %s', e)

    @api.model
    def _cron_refresh_all_stats(self):
        """Cron diario: actualiza stats de todas las propiedades publicadas en Instagram."""
        all_stats = self.search([('property_id.ig_published', '=', True)])
        for rec in all_stats:
            try:
                rec._fetch_stats()
            except Exception as e:
                _logger.warning('Error actualizando stats de %s: %s', rec.property_id.name, e)
