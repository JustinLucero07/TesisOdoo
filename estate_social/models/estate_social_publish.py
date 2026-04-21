import base64
import json
import logging
import requests

from odoo import models, fields
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

META_API_VERSION = 'v25.0'


class EstatePropertyPublish(models.Model):
    _inherit = 'estate.property'

    fb_post_id = fields.Char(string='Facebook Post ID', readonly=True, copy=False)
    fb_published = fields.Boolean(string='Publicado en Facebook', default=False, copy=False)
    ig_post_id = fields.Char(string='Instagram Post ID', readonly=True, copy=False)
    ig_published = fields.Boolean(string='Publicado en Instagram', default=False, copy=False)

    def _get_meta_config(self):
        ICP = self.env['ir.config_parameter'].sudo()
        return {
            'page_id': ICP.get_param('estate_social.facebook_page_id', ''),
            'page_token': ICP.get_param('estate_social.facebook_page_token', ''),
            'ig_account_id': ICP.get_param('estate_social.instagram_account_id', ''),
        }

    @staticmethod
    def _decode_image(binary_val):
        """
        Devuelve (raw_bytes, mime_type, extension).
        En Odoo 19 los campos Binary devuelven bytes que contienen base64.
        Detecta si la imagen es PNG o JPEG por los magic bytes.
        """
        raw = base64.b64decode(binary_val)
        if raw[:8] == b'\x89PNG\r\n\x1a\n':
            return raw, 'image/png', 'png'
        if raw[:2] == b'\xff\xd8':
            return raw, 'image/jpeg', 'jpg'
        if raw[:6] in (b'GIF87a', b'GIF89a'):
            return raw, 'image/gif', 'gif'
        if raw[:4] == b'RIFF' and raw[8:12] == b'WEBP':
            return raw, 'image/webp', 'webp'
        # Fallback: JPEG
        return raw, 'image/jpeg', 'jpg'

    def action_publish_facebook(self):
        """
        Publica la propiedad en la página de Facebook via Graph API.

        Lógica de imágenes:
          - Varias imágenes (main + galería): álbum — sube cada foto con
            published=false y luego crea el post con todas adjuntas.
          - Solo image_main: sube esa foto directamente con la descripción.
          - Sin imágenes: publica texto + link de WordPress.
        """
        self.ensure_one()
        cfg = self._get_meta_config()
        if not cfg['page_id'] or not cfg['page_token']:
            raise UserError('Configura el Page ID y Page Token de Facebook en Ajustes → Redes Sociales.')

        caption = self._get_share_text()
        page_id = cfg['page_id']
        token   = cfg['page_token']

        # ── Recopilar imágenes (máximo 10) ────────────────────────────────────
        raw_images = []
        if self.image_main:
            raw_images.append(self.image_main)
        for img_rec in self.image_ids[:9]:
            if img_rec.image:
                raw_images.append(img_rec.image)

        try:
            if len(raw_images) > 1:
                # ── Álbum: subir cada foto sin publicar, luego crear el post ──
                photo_ids = []
                for idx, img_b64 in enumerate(raw_images):
                    img_bytes, mime, ext = self._decode_image(img_b64)
                    resp = requests.post(
                        f'https://graph.facebook.com/{META_API_VERSION}/{page_id}/photos',
                        data={'published': 'false', 'access_token': token},
                        files={'source': (f'propiedad_{idx+1}.{ext}', img_bytes, mime)},
                        timeout=60,
                    )
                    r = resp.json()
                    if resp.status_code in (200, 201) and r.get('id'):
                        photo_ids.append(r['id'])
                    else:
                        _logger.warning('FB foto %d error (%s): %s', idx + 1, resp.status_code, r)

                if not photo_ids:
                    raise UserError('No se pudieron subir las imágenes a Facebook. Revisa el token de la página.')

                attached = {
                    f'attached_media[{i}]': json.dumps({'media_fbid': pid})
                    for i, pid in enumerate(photo_ids)
                }
                resp_post = requests.post(
                    f'https://graph.facebook.com/{META_API_VERSION}/{page_id}/feed',
                    data={'message': caption, 'access_token': token, **attached},
                    timeout=30,
                )
                result = resp_post.json()
                post_id = result.get('id')

            elif len(raw_images) == 1:
                # ── Una foto: subir sin publicar y crear el post en el feed ────
                img_bytes, mime, ext = self._decode_image(raw_images[0])
                resp = requests.post(
                    f'https://graph.facebook.com/{META_API_VERSION}/{page_id}/photos',
                    data={'published': 'false', 'access_token': token},
                    files={'source': (f'propiedad.{ext}', img_bytes, mime)},
                    timeout=60,
                )
                r = resp.json()
                if resp.status_code not in (200, 201) or not r.get('id'):
                    err = r.get('error', {}).get('message', str(r))
                    raise UserError(f'No se pudo subir la imagen a Facebook: {err}')
                resp_post = requests.post(
                    f'https://graph.facebook.com/{META_API_VERSION}/{page_id}/feed',
                    data={
                        'message': caption,
                        'access_token': token,
                        'attached_media[0]': json.dumps({'media_fbid': r['id']}),
                    },
                    timeout=30,
                )
                result = resp_post.json()
                post_id = result.get('id')

            else:
                # ── Sin imágenes: texto + link ─────────────────────────────────
                ICP = self.env['ir.config_parameter'].sudo()
                wp_url = ICP.get_param('estate_wp.url', '')
                link = f"{wp_url.rstrip('/')}/?p={self.wp_post_id}" if (self.wp_post_id and wp_url) else ''
                post_data = {'message': caption, 'access_token': token}
                if link:
                    post_data['link'] = link
                resp = requests.post(
                    f'https://graph.facebook.com/{META_API_VERSION}/{page_id}/feed',
                    data=post_data, timeout=30,
                )
                result = resp.json()
                post_id = result.get('id')

        except UserError:
            raise
        except Exception as e:
            raise UserError(f'Error de conexión con Facebook: {e}')

        if post_id:
            self.write({'fb_post_id': post_id, 'fb_published': True})
            n = len(raw_images)
            img_txt = f' con {n} imagen{"es" if n > 1 else ""}' if n else ''
            self.message_post(body=f'Publicado en Facebook{img_txt}. Post ID: <b>{post_id}</b>')
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Facebook',
                    'message': f'Propiedad publicada en Facebook{img_txt}.',
                    'type': 'success',
                },
            }
        else:
            error_msg = result.get('error', {}).get('message', str(result))
            raise UserError(f'Error de Facebook: {error_msg}')

    def action_publish_instagram(self):
        """
        Publica la propiedad en Instagram Business via Graph API.
        Requiere una URL pública de la imagen (WordPress o base_url del servidor).
        """
        self.ensure_one()
        cfg = self._get_meta_config()
        if not cfg['ig_account_id'] or not cfg['page_token']:
            raise UserError('Configura el Instagram Account ID y Page Token en Ajustes → Redes Sociales.')

        # Obtener URL pública de la imagen
        image_url = self._get_public_image_url()
        if not image_url:
            raise UserError(
                'No se encontró una URL pública para la imagen.\n'
                'Publica la propiedad en WordPress primero, o configura la URL del servidor en Ajustes.'
            )

        caption = self._get_instagram_caption()

        try:
            # Paso 1: Crear contenedor de media
            resp1 = requests.post(
                f'https://graph.facebook.com/{META_API_VERSION}/{cfg["ig_account_id"]}/media',
                data={
                    'image_url': image_url,
                    'caption': caption,
                    'access_token': cfg['page_token'],
                },
                timeout=30,
            )
            r1 = resp1.json()
            if resp1.status_code != 200 or not r1.get('id'):
                error_msg = r1.get('error', {}).get('message', str(r1))
                raise UserError(f'Error creando media en Instagram: {error_msg}')

            creation_id = r1['id']

            # Paso 2: Publicar el contenedor
            resp2 = requests.post(
                f'https://graph.facebook.com/{META_API_VERSION}/{cfg["ig_account_id"]}/media_publish',
                data={
                    'creation_id': creation_id,
                    'access_token': cfg['page_token'],
                },
                timeout=30,
            )
            r2 = resp2.json()
            if resp2.status_code == 200 and r2.get('id'):
                self.write({'ig_post_id': r2['id'], 'ig_published': True})
                self.message_post(body=f'Propiedad publicada en Instagram. Post ID: <b>{r2["id"]}</b>')
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Instagram',
                        'message': 'Propiedad publicada correctamente en Instagram.',
                        'type': 'success',
                    },
                }
            else:
                error_msg = r2.get('error', {}).get('message', str(r2))
                raise UserError(f'Error publicando en Instagram: {error_msg}')

        except UserError:
            raise
        except Exception as e:
            raise UserError(f'Error de conexión con Instagram: {e}')

    def _get_public_image_url(self):
        """
        Retorna una URL pública directa de la imagen.
        Prioridad:
          1) Imagen featured del post de WordPress (si ya está publicado)
          2) Sube la imagen temporalmente a WordPress Media y devuelve su URL
        """
        ICP = self.env['ir.config_parameter'].sudo()
        wp_url = ICP.get_param('estate_wp.url', '').rstrip('/')
        wp_username = ICP.get_param('estate_wp.username', '')
        wp_password = ICP.get_param('estate_wp.app_password', '')
        wp_method = ICP.get_param('estate_wp.auth_method', 'basic')
        wp_token = ICP.get_param('estate_wp.jwt_token', '')

        if not wp_url or not wp_username:
            return ''

        auth = None
        extra_headers = {}
        if wp_method == 'jwt' and wp_token:
            extra_headers['Authorization'] = f'Bearer {wp_token}'
        else:
            auth = (wp_username, wp_password)

        # Opción 1: la propiedad ya está publicada en WordPress → usar su imagen featured
        if self.wp_post_id:
            try:
                wp_post_type = ICP.get_param('estate_wp.post_type', 'property')
                resp = requests.get(
                    f"{wp_url}/wp-json/wp/v2/{wp_post_type}/{self.wp_post_id}",
                    params={'_fields': 'featured_media'},
                    auth=auth, headers=extra_headers, timeout=10,
                )
                if resp.status_code == 200:
                    media_id = resp.json().get('featured_media')
                    if media_id:
                        resp2 = requests.get(
                            f"{wp_url}/wp-json/wp/v2/media/{media_id}",
                            params={'_fields': 'source_url'},
                            auth=auth, headers=extra_headers, timeout=10,
                        )
                        if resp2.status_code == 200:
                            source_url = resp2.json().get('source_url', '')
                            if source_url:
                                _logger.info('Imagen Instagram desde WordPress post: %s', source_url)
                                return source_url
            except Exception as e:
                _logger.warning('Error obteniendo imagen featured de WordPress: %s', e)

        # Opción 2: subir la imagen directamente a WordPress Media Library
        if self.image_main:
            try:
                image_data = base64.b64decode(self.image_main)
                filename = f"inmobi_{self.name.replace('/', '-')}.jpg"
                upload_headers = {
                    'Content-Disposition': f'attachment; filename="{filename}"',
                    'Content-Type': 'image/jpeg',
                    **extra_headers,
                }
                resp = requests.post(
                    f"{wp_url}/wp-json/wp/v2/media",
                    headers=upload_headers,
                    data=image_data,
                    auth=auth,
                    timeout=30,
                )
                if resp.status_code in (200, 201):
                    source_url = resp.json().get('source_url', '')
                    if source_url:
                        _logger.info('Imagen Instagram subida a WordPress Media: %s', source_url)
                        return source_url
                else:
                    _logger.warning('Error subiendo imagen a WordPress: %s %s',
                                    resp.status_code, resp.text[:200])
            except Exception as e:
                _logger.warning('Error subiendo imagen a WordPress Media: %s', e)

        return ''

    def action_unpublish_facebook(self):
        """Elimina el post de Facebook y marca como no publicado."""
        self.ensure_one()
        if not self.fb_post_id:
            raise UserError('No hay post de Facebook vinculado.')
        cfg = self._get_meta_config()
        try:
            resp = requests.delete(
                f'https://graph.facebook.com/{META_API_VERSION}/{self.fb_post_id}',
                params={'access_token': cfg['page_token']},
                timeout=30,
            )
            result = resp.json()
            if result.get('success'):
                self.write({'fb_post_id': False, 'fb_published': False})
                self.message_post(body='Post de Facebook eliminado.')
            else:
                raise UserError(f'No se pudo eliminar: {result}')
        except UserError:
            raise
        except Exception as e:
            raise UserError(f'Error: {e}')
