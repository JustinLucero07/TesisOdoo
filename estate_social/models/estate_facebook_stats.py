import json
import logging
import requests

from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

META_API_VERSION = 'v25.0'

FB_INSIGHTS_METRICS = (
    'post_impressions,'
    'post_impressions_unique,'
    'post_clicks,'
    'post_impressions_fan_unique,'
    'post_impressions_organic_unique,'
    'post_impressions_paid_unique,'
    'post_impressions_viral_unique,'
    'post_clicks_by_type,'
    'post_impressions_by_age_gender_unique'
)

FB_POST_FIELDS = (
    'reactions.type(LIKE).limit(0).summary(total_count).as(r_likes),'
    'reactions.type(LOVE).limit(0).summary(total_count).as(r_loves),'
    'reactions.type(HAHA).limit(0).summary(total_count).as(r_hahas),'
    'reactions.type(WOW).limit(0).summary(total_count).as(r_wows),'
    'reactions.type(SAD).limit(0).summary(total_count).as(r_sads),'
    'reactions.type(ANGRY).limit(0).summary(total_count).as(r_angries),'
    'comments.summary(total_count),'
    'shares'
)

AGE_GROUPS = ['18-24', '25-34', '35-44', '45-54', '55-64', '65+']


class EstateFacebookStats(models.Model):
    _name = 'estate.facebook.stats'
    _description = 'Estadísticas Facebook por Publicación'
    _order = 'stats_date desc, id desc'
    _rec_name = 'fb_post_id'

    property_id = fields.Many2one(
        'estate.property', string='Propiedad', required=False, ondelete='cascade')
    fb_post_id = fields.Char(string='Facebook Post ID')
    fb_permalink = fields.Char(string='Enlace al Post', readonly=True)
    fb_message = fields.Text(string='Mensaje del Post', readonly=True)
    stats_date = fields.Datetime(
        string='Última Actualización', default=fields.Datetime.now, readonly=True)

    # ── Alcance e Impresiones ──────────────────────────────────────────────────
    impressions = fields.Integer(string='Visualizaciones', readonly=True)
    reach = fields.Integer(string='Espectadores', readonly=True)

    # ── Interacciones ──────────────────────────────────────────────────────────
    clicks = fields.Integer(string='Clics', readonly=True)
    link_clicks = fields.Integer(string='Clics en el enlace', readonly=True)
    likes = fields.Integer(string='Me Gusta', readonly=True)
    loves = fields.Integer(string='Me Encanta', readonly=True)
    hahas = fields.Integer(string='Jajá', readonly=True)
    wows = fields.Integer(string='Asombro', readonly=True)
    sads = fields.Integer(string='Triste', readonly=True)
    angries = fields.Integer(string='Enojado', readonly=True)
    comments = fields.Integer(string='Comentarios', readonly=True)
    shares = fields.Integer(string='Compartidos', readonly=True)

    # ── Audiencia ─────────────────────────────────────────────────────────────
    fan_reach = fields.Integer(string='Seguidores que vieron', readonly=True)
    non_fan_reach = fields.Integer(string='No seguidores que vieron', readonly=True)

    # ── Cómo te encuentran ───────────────────────────────────────────────────
    organic_reach = fields.Integer(string='Alcance orgánico', readonly=True)
    paid_reach = fields.Integer(string='Alcance pagado', readonly=True)
    viral_reach = fields.Integer(string='Alcance viral', readonly=True)

    # ── Demografía: JSON crudo {"M.25-34": 50, "F.25-34": 30, ...} ───────────
    gender_age_data = fields.Char(string='Datos demográficos (JSON)', readonly=True)

    # ── Calculados ────────────────────────────────────────────────────────────
    total_reactions = fields.Integer(
        string='Total Reacciones', compute='_compute_totals', store=True)
    total_interactions = fields.Integer(
        string='Total Interacciones', compute='_compute_totals', store=True)
    engagement_rate = fields.Float(
        string='Engagement (%)', compute='_compute_totals', store=True, digits=(5, 2))
    ctr = fields.Float(
        string='CTR (%)', compute='_compute_totals', store=True, digits=(5, 2))
    history_count = fields.Integer(
        string='Snapshots', compute='_compute_history_count')
    dashboard_json = fields.Char(
        string='Datos del dashboard',
        compute='_compute_dashboard_json',
        help='Agregado JSON para el widget OWL del formulario.')

    # ── Estado ────────────────────────────────────────────────────────────────
    fetch_error = fields.Char(string='Error al obtener datos', readonly=True)

    @api.depends('likes', 'loves', 'hahas', 'wows', 'sads', 'angries',
                 'clicks', 'comments', 'shares', 'reach', 'impressions')
    def _compute_totals(self):
        for rec in self:
            rec.total_reactions = (
                (rec.likes or 0) + (rec.loves or 0) + (rec.hahas or 0) +
                (rec.wows or 0) + (rec.sads or 0) + (rec.angries or 0)
            )
            total = rec.total_reactions + (rec.clicks or 0) + (rec.comments or 0) + (rec.shares or 0)
            rec.total_interactions = total
            rec.engagement_rate = (total / rec.reach * 100) if rec.reach else 0.0
            rec.ctr = (rec.clicks / rec.impressions * 100) if rec.impressions else 0.0

    def _compute_history_count(self):
        History = self.env['estate.facebook.stats.history']
        for rec in self:
            rec.history_count = History.search_count([('stats_id', '=', rec.id)])

    @api.depends('impressions', 'reach', 'fan_reach', 'non_fan_reach',
                 'organic_reach', 'paid_reach', 'viral_reach', 'link_clicks',
                 'likes', 'loves', 'hahas', 'wows', 'sads', 'angries',
                 'comments', 'shares', 'clicks', 'gender_age_data', 'stats_date')
    def _compute_dashboard_json(self):
        for rec in self:
            # Parsear demografía cruda
            demo = {}
            if rec.gender_age_data:
                try:
                    raw = json.loads(rec.gender_age_data)
                    for age in AGE_GROUPS:
                        demo[age] = {
                            'M': int(raw.get(f'M.{age}', 0) or 0),
                            'F': int(raw.get(f'F.{age}', 0) or 0),
                            'U': int(raw.get(f'U.{age}', 0) or 0),
                        }
                except Exception:
                    demo = {age: {'M': 0, 'F': 0, 'U': 0} for age in AGE_GROUPS}
            else:
                demo = {age: {'M': 0, 'F': 0, 'U': 0} for age in AGE_GROUPS}

            # Snapshots de historial para gráfico de evolución
            history = self.env['estate.facebook.stats.history'].search(
                [('stats_id', '=', rec.id)], order='snapshot_date asc')
            evolution = [{
                'date': h.snapshot_date.strftime('%Y-%m-%d %H:%M') if h.snapshot_date else '',
                'impressions': h.impressions,
                'reach': h.reach,
                'interactions': h.total_interactions,
                'reactions': h.total_reactions,
                'clicks': h.clicks,
            } for h in history]

            rec.dashboard_json = json.dumps({
                'summary': {
                    'impressions':       rec.impressions,
                    'reach':             rec.reach,
                    'interactions':      rec.total_interactions,
                    'reactions':         rec.total_reactions,
                    'comments':          rec.comments,
                    'shares':            rec.shares,
                    'clicks':            rec.clicks,
                    'link_clicks':       rec.link_clicks,
                    'engagement_rate':   round(rec.engagement_rate, 2),
                    'ctr':               round(rec.ctr, 2),
                },
                'reactions_by_type': {
                    'likes':   rec.likes,
                    'loves':   rec.loves,
                    'hahas':   rec.hahas,
                    'wows':    rec.wows,
                    'sads':    rec.sads,
                    'angries': rec.angries,
                },
                'audience': {
                    'fan':     rec.fan_reach,
                    'non_fan': rec.non_fan_reach,
                },
                'traffic_source': {
                    'organic': rec.organic_reach,
                    'paid':    rec.paid_reach,
                    'viral':   rec.viral_reach,
                },
                'demographics': demo,
                'evolution': evolution,
            })

    def action_refresh(self):
        for rec in self:
            rec._fetch_stats()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Facebook Insights',
                'message': f'Estadísticas actualizadas para {len(self)} publicaciones.',
                'type': 'success',
            },
        }

    def action_view_history(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Evolución — {self.fb_post_id}',
            'res_model': 'estate.facebook.stats.history',
            'view_mode': 'graph,list',
            'domain': [('stats_id', '=', self.id)],
        }

    def _fetch_stats(self):
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
            # ── Reacciones, comentarios, compartidos ──────────────────────────
            post_resp = requests.get(
                f'https://graph.facebook.com/{META_API_VERSION}/{post_id}',
                params={'fields': FB_POST_FIELDS, 'access_token': token},
                timeout=15,
            )
            post_data = post_resp.json()

            if post_resp.status_code != 200 or 'error' in post_data:
                err = post_data.get('error', {}).get('message', str(post_data))
                self.fetch_error = f'Error API: {err}'
                _logger.warning('Facebook post fields error para %s: %s', post_id, err)
                return

            likes    = post_data.get('r_likes',   {}).get('summary', {}).get('total_count', 0)
            loves    = post_data.get('r_loves',   {}).get('summary', {}).get('total_count', 0)
            hahas    = post_data.get('r_hahas',   {}).get('summary', {}).get('total_count', 0)
            wows     = post_data.get('r_wows',    {}).get('summary', {}).get('total_count', 0)
            sads     = post_data.get('r_sads',    {}).get('summary', {}).get('total_count', 0)
            angries  = post_data.get('r_angries', {}).get('summary', {}).get('total_count', 0)
            shares   = post_data.get('shares',    {}).get('count', 0)
            comments = post_data.get('comments',  {}).get('summary', {}).get('total_count', 0)

            # ── Insights (requieren read_insights) ────────────────────────────
            impressions = reach = clicks = link_clicks = 0
            fan_reach = non_fan_reach = 0
            organic_reach = paid_reach = viral_reach = 0
            gender_age_raw = {}

            ins_resp = requests.get(
                f'https://graph.facebook.com/{META_API_VERSION}/{post_id}/insights',
                params={'metric': FB_INSIGHTS_METRICS, 'period': 'lifetime', 'access_token': token},
                timeout=15,
            )
            if ins_resp.status_code == 200:
                for item in ins_resp.json().get('data', []):
                    name = item.get('name', '')
                    values = item.get('values') or [{}]
                    val = values[-1].get('value', 0)

                    if name == 'post_impressions':
                        impressions = val if isinstance(val, int) else 0
                    elif name == 'post_impressions_unique':
                        reach = val if isinstance(val, int) else 0
                    elif name == 'post_clicks':
                        clicks = val if isinstance(val, int) else 0
                    elif name == 'post_impressions_fan_unique':
                        fan_reach = val if isinstance(val, int) else 0
                    elif name == 'post_impressions_organic_unique':
                        organic_reach = val if isinstance(val, int) else 0
                    elif name == 'post_impressions_paid_unique':
                        paid_reach = val if isinstance(val, int) else 0
                    elif name == 'post_impressions_viral_unique':
                        viral_reach = val if isinstance(val, int) else 0
                    elif name == 'post_clicks_by_type' and isinstance(val, dict):
                        link_clicks = int(val.get('link clicks', 0) or 0)
                    elif name == 'post_impressions_by_age_gender_unique' and isinstance(val, dict):
                        gender_age_raw = {k: int(v or 0) for k, v in val.items()}

                if reach and fan_reach:
                    non_fan_reach = max(reach - fan_reach, 0)
            else:
                _logger.info(
                    'Insights no disponibles para %s — agrega read_insights al token', post_id)

            self.write({
                'fb_post_id':       post_id,
                'impressions':      impressions,
                'reach':            reach,
                'clicks':           clicks,
                'link_clicks':      link_clicks,
                'likes':            likes,
                'loves':            loves,
                'hahas':            hahas,
                'wows':             wows,
                'sads':             sads,
                'angries':          angries,
                'comments':         comments,
                'shares':           shares,
                'fan_reach':        fan_reach,
                'non_fan_reach':    non_fan_reach,
                'organic_reach':    organic_reach,
                'paid_reach':       paid_reach,
                'viral_reach':      viral_reach,
                'gender_age_data':  json.dumps(gender_age_raw) if gender_age_raw else False,
                'stats_date':       fields.Datetime.now(),
                'fetch_error':      False,
            })

            # ── Snapshot de historial ─────────────────────────────────────────
            total_r = likes + loves + hahas + wows + sads + angries
            total_i = total_r + clicks + comments + shares
            self.env['estate.facebook.stats.history'].create({
                'stats_id':           self.id,
                'snapshot_date':      fields.Datetime.now(),
                'impressions':        impressions,
                'reach':              reach,
                'clicks':             clicks,
                'total_reactions':    total_r,
                'comments':           comments,
                'shares':             shares,
                'total_interactions': total_i,
                'engagement_rate':    (total_i / reach * 100) if reach else 0.0,
            })

        except Exception as e:
            self.fetch_error = f'Error de conexión: {e}'
            _logger.error('Error obteniendo Facebook stats: %s', e)

    @api.model
    def action_import_from_facebook(self, limit=10):
        ICP = self.env['ir.config_parameter'].sudo()
        token = ICP.get_param('estate_social.facebook_page_token', '')
        page_id = ICP.get_param('estate_social.facebook_page_id', '')

        if not token:
            raise UserError('Configure el Page Access Token en Ajustes → Redes Sociales.')
        if not page_id:
            raise UserError('Configure el Page ID de Facebook en Ajustes → Redes Sociales.')

        try:
            resp = requests.get(
                f'https://graph.facebook.com/{META_API_VERSION}/{page_id}/posts',
                params={
                    'fields': 'id,message,created_time,permalink_url,full_picture',
                    'limit': limit,
                    'access_token': token,
                },
                timeout=20,
            )
            data = resp.json()
        except Exception as e:
            raise UserError(f'Error de conexión con Facebook: {e}')

        if resp.status_code != 200 or 'error' in data:
            raise UserError(
                f'Error Facebook API: {data.get("error", {}).get("message", str(data))}')

        posts = data.get('data', [])
        if not posts:
            raise UserError('No se encontraron publicaciones en tu Página de Facebook.')

        created = updated = 0
        for post in posts:
            post_id = post.get('id', '')
            if not post_id:
                continue

            property_rec = self.env['estate.property'].search(
                [('fb_post_id', '=', post_id)], limit=1)
            existing = self.search([('fb_post_id', '=', post_id)], limit=1)
            vals = {
                'fb_post_id':   post_id,
                'fb_message':   (post.get('message') or '')[:500],
                'fb_permalink': post.get('permalink_url', ''),
            }
            if property_rec:
                vals['property_id'] = property_rec.id

            if existing:
                existing.write(vals)
                existing._fetch_stats()
                updated += 1
            else:
                rec = self.create(vals)
                rec._fetch_stats()
                created += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Importación Facebook completada',
                'message': (
                    f'{created} nuevas publicaciones importadas'
                    f'{", " + str(updated) + " actualizadas" if updated else ""}.'
                ),
                'type': 'success',
                'sticky': True,
            },
        }

    @api.model
    def _cron_refresh_all_stats(self):
        for rec in self.search([]):
            try:
                rec._fetch_stats()
            except Exception as e:
                _logger.warning('Error actualizando FB stats de %s: %s',
                                rec.property_id.name if rec.property_id else rec.fb_post_id, e)


class EstateFacebookStatsHistory(models.Model):
    _name = 'estate.facebook.stats.history'
    _description = 'Historial de Estadísticas Facebook'
    _order = 'snapshot_date asc'

    stats_id = fields.Many2one(
        'estate.facebook.stats', string='Publicación', required=True, ondelete='cascade')
    property_id = fields.Many2one(
        'estate.property', related='stats_id.property_id', store=True, string='Propiedad')
    fb_post_id = fields.Char(related='stats_id.fb_post_id', store=True, string='Post ID')
    snapshot_date = fields.Datetime(string='Fecha', required=True)

    impressions = fields.Integer(string='Visualizaciones')
    reach = fields.Integer(string='Espectadores')
    clicks = fields.Integer(string='Clics')
    total_reactions = fields.Integer(string='Reacciones')
    comments = fields.Integer(string='Comentarios')
    shares = fields.Integer(string='Compartidos')
    total_interactions = fields.Integer(string='Interacciones')
    engagement_rate = fields.Float(string='Engagement (%)', digits=(5, 2))
