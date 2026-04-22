import urllib.parse

from odoo import models


class EstatePropertySocial(models.Model):
    _inherit = 'estate.property'

    def action_share_facebook(self):
        """Generate Facebook share URL."""
        self.ensure_one()
        text = self._get_share_text()

        ICP = self.env['ir.config_parameter'].sudo()
        wp_url = ICP.get_param('estate_wp.url', '')

        if self.wp_post_id and wp_url:
            share_url = f"{wp_url}/?p={self.wp_post_id}"
            fb_url = f"https://www.facebook.com/sharer/sharer.php?u={urllib.parse.quote(share_url)}&quote={urllib.parse.quote(text)}"
        else:
            fb_url = f"https://www.facebook.com/sharer/sharer.php?quote={urllib.parse.quote(text)}"

        return {
            'type': 'ir.actions.act_url',
            'url': fb_url,
            'target': 'new',
        }

    def action_share_whatsapp(self):
        """Compartir propiedad por WhatsApp (difusión general)."""
        self.ensure_one()
        text = self._get_share_text()
        wa_url = f"https://wa.me/?text={urllib.parse.quote(text)}"
        return {'type': 'ir.actions.act_url', 'url': wa_url, 'target': 'new'}

    def action_whatsapp_business_contact(self):
        """
        Genera un link wa.me al número de WhatsApp Business de la inmobiliaria
        con texto pre-rellenado sobre esta propiedad.
        Los clientes hacen clic → inician conversación directa con el negocio.
        """
        self.ensure_one()
        ICP = self.env['ir.config_parameter'].sudo()
        business_number = ICP.get_param('estate_social.whatsapp_business_number', '')
        if not business_number:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'WhatsApp Business',
                    'message': 'Configure el número en Ajustes > Redes Sociales > Número WhatsApp Business.',
                    'type': 'warning',
                },
            }
        clean = ''.join(c for c in business_number if c.isdigit())
        msg = (
            f"Hola, vi la propiedad *{self.title}* "
            f"en {self.city or 'su catálogo'} "
            f"por ${self.price:,.2f} y me interesa información. "
            f"Referencia: {self.name}"
        )
        wa_url = f"https://wa.me/{clean}?text={urllib.parse.quote(msg)}"
        return {'type': 'ir.actions.act_url', 'url': wa_url, 'target': 'new'}

    def action_share_instagram(self):
        """
        Instagram no permite publicación directa desde terceros sin API aprobada.
        Este botón copia el texto listo para pegar en Instagram y abre la app/web.
        """
        self.ensure_one()
        caption = self._get_instagram_caption()
        # Retornar URL de Instagram + mostrar caption para copiar
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '📸 Instagram — Caption lista',
                'message': caption,
                'type': 'success',
                'sticky': True,
            },
        }

    def action_share_twitter(self):
        """Compartir en Twitter/X."""
        self.ensure_one()
        text = self._get_share_text()
        tw_url = f"https://twitter.com/intent/tweet?text={urllib.parse.quote(text)}"
        return {'type': 'ir.actions.act_url', 'url': tw_url, 'target': 'new'}

    def _strip_html(self, html_text):
        """Convierte HTML a texto plano limpio para redes sociales."""
        import re
        if not html_text:
            return ''
        # Remove HTML tags
        text = re.sub(r'<br\s*/?>', '\n', html_text)
        text = re.sub(r'</?(h[1-6]|p|div|li)[^>]*>', '\n', text)
        text = re.sub(r'</?(ul|ol)[^>]*>', '', text)
        text = re.sub(r'<[^>]+>', '', text)
        # Clean up whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = text.strip()
        # Decode HTML entities
        import html
        text = html.unescape(text)
        return text

    def _get_share_text(self):
        """Texto de compartir para WhatsApp, Facebook y Twitter con descripción comercial."""
        ICP = self.env['ir.config_parameter'].sudo()
        wp_url = ICP.get_param('estate_wp.url', '')
        business_number = ICP.get_param('estate_social.whatsapp_business_number', '')

        # Descripción comercial IA (prioridad) o descripción general
        desc_html = self.description or ''
        desc_text = self._strip_html(desc_html)

        # Si la descripción es muy larga, limitar para redes
        if len(desc_text) > 1500:
            desc_text = desc_text[:1500] + '...'

        link = f"\n🔗 {wp_url}/?p={self.wp_post_id}" if (self.wp_post_id and wp_url) else ''
        contact = f"\n📞 Contacto: wa.me/{business_number}" if business_number else ''

        if desc_text:
            # Publicar con la descripción comercial completa
            text = (
                f"{desc_text}\n"
                f"{link}"
                f"{contact}"
            )
        else:
            # Fallback: formato básico si no hay descripción
            estado_map = {
                'available': '✅ Disponible',
                'reserved': '🔒 Reservado',
                'sold': '🏆 Vendido',
                'rented': '🔑 Alquilado',
            }
            text = (
                f"🏠 *{self.title}*\n"
                f"📍 {self.city or 'Cuenca'}\n"
                f"💰 ${self.price:,.2f}\n"
                f"📐 {self.area} m²\n"
                f"🛏️ {self.bedrooms} hab | 🚿 {self.bathrooms} baños\n"
                f"{estado_map.get(self.state, '')}\n"
                f"🏷️ {self.property_type_id.name}"
                f"{link}"
                f"{contact}\n"
                f"✍️ ¡Contáctanos para más información!"
            )
        return text

    def _get_instagram_caption(self):
        """Caption optimizada para Instagram con descripción comercial y hashtags."""
        ICP = self.env['ir.config_parameter'].sudo()
        city = (self.city or 'Cuenca').lower().replace(' ', '')
        ptype = (self.property_type_id.name or 'propiedad').lower().replace(' ', '')
        business_number = ICP.get_param('estate_social.whatsapp_business_number', '')
        contact_line = f"💬 WhatsApp: wa.me/{business_number}" if business_number else "💬 Escríbenos para más info"

        # Descripción comercial IA (prioridad) o descripción general
        desc_html = self.description or ''
        desc_text = self._strip_html(desc_html)

        # Instagram permite 2200 chars — dejar espacio para hashtags (~200)
        if len(desc_text) > 1800:
            desc_text = desc_text[:1800] + '...'

        hashtags = (
            f"#{ptype} #{city} #inmobiliaria #bienesraices #realestate "
            f"#casaenventa #propiedades #ecuador #inversioninmobiliaria"
        )

        if desc_text:
            caption = (
                f"{desc_text}\n\n"
                f"{contact_line}\n"
                f"Ref: {self.name}\n\n"
                f"{hashtags}"
            )
        else:
            caption = (
                f"🏠 {self.title}\n\n"
                f"📍 {self.city or 'Cuenca'}\n"
                f"💰 ${self.price:,.2f}\n"
                f"📐 {self.area} m²  |  🛏️ {self.bedrooms} hab  |  🚿 {self.bathrooms} baños\n\n"
                f"{contact_line}\n"
                f"Ref: {self.name}\n\n"
                f"{hashtags}"
            )
        return caption

