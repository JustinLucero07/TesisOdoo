# -*- coding: utf-8 -*-
import base64
import functools
import os
import re

from markupsafe import Markup

from odoo import models, fields, api

_FICHA_FACES = [
    ('Ficha Serif', 600, 'CormorantGaramond-600.ttf'),
    ('Ficha Serif', 700, 'CormorantGaramond-700.ttf'),
    ('Ficha Sans', 400, 'Jost-400.ttf'),
    ('Ficha Sans', 600, 'Jost-600.ttf'),
]


@functools.lru_cache(maxsize=1)
def _ficha_fonts_css():
    """CSS con las tipografías de la ficha embebidas en base64.

    Se incrustan en el propio HTML del reporte porque wkhtmltopdf no
    descarga rutas relativas ni usa los bundles de assets; así la ficha
    conserva la tipografía tanto en local como en el servidor."""
    fonts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'fonts')
    faces = []
    for family, weight, filename in _FICHA_FACES:
        path = os.path.join(fonts_dir, filename)
        try:
            with open(path, 'rb') as fh:
                b64 = base64.b64encode(fh.read()).decode()
        except OSError:
            continue  # sin la fuente, el diseño cae a la serif del sistema
        faces.append(
            "@font-face{font-family:'%s';font-style:normal;font-weight:%d;"
            "src:url(data:font/truetype;base64,%s) format('truetype');}"
            % (family, weight, b64)
        )
    return Markup(''.join(faces))


def _ficha_excerpt(html, limit=430):
    """Párrafo comercial para la ficha, en texto plano.

    Quita el HTML, descarta el titular en mayúsculas con el que suelen
    empezar las descripciones generadas, y corta en el último punto para
    que el texto termine en una frase completa (no a media palabra)."""
    if not html:
        return ''
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text).strip()

    # "DEPARTAMENTO EN VENTA – AV. 12 DE OCTUBRE – ... Inmobi presenta..."
    # El titular va en mayúsculas: se corta en la primera palabra normal.
    encabezado = re.match(r'^(?:[^a-záéíóúñ]{15,})(?=[A-ZÁÉÍÓÚÑ][a-záéíóúñ])', text)
    if encabezado:
        text = text[encabezado.end():].strip()

    if len(text) <= limit:
        return text
    recorte = text[:limit]
    fin = max(recorte.rfind('. '), recorte.rfind('? '), recorte.rfind('! '))
    if fin > limit // 3:                      # hay una frase completa utilizable
        return recorte[:fin + 1]
    return recorte.rsplit(' ', 1)[0].rstrip('.,;:') + '…'


class EstateFichaWizard(models.TransientModel):
    _name = 'estate.ficha.wizard'
    _description = 'Imprimir Ficha de Propiedad (elegir diseño)'

    property_id = fields.Many2one(
        'estate.property', string='Propiedad', required=True,
        default=lambda self: self.env.context.get('active_id'))
    design = fields.Selection([
        ('1', 'Diseño 1 · Portada vertical (foto grande arriba)'),
        ('2', 'Diseño 2 · Minimalista (encabezado limpio, mosaico)'),
        ('3', 'Diseño 3 · Portada a sangre (foto de fondo completa)'),
    ], string='Diseño de la ficha', default='1', required=True)
    show_contact = fields.Boolean(
        string='Incluir datos del asesor (contacto)', default=True,
        help='Si se desmarca, la ficha se genera sin los datos de contacto del asesor.')

    def action_print(self):
        self.ensure_one()
        return self.env.ref('estate_reports.action_report_ficha_inmobi').report_action(
            self.property_id,
            data={
                'design': self.design,
                'show_contact': self.show_contact,
                # Se incluye el id aquí porque, al lanzarse desde un asistente,
                # el cliente web no siempre reenvía los docids al reporte.
                'property_id': self.property_id.id,
            },
        )


class ReportFichaInmobi(models.AbstractModel):
    _name = 'report.estate_reports.report_ficha_inmobi'
    _description = 'Ficha Inmobi (3 diseños)'

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}
        # Si el cliente web no reenvió los docids (caso típico al lanzar el
        # reporte desde un asistente), se recuperan del propio data o del
        # contexto, para que la ficha nunca salga en blanco.
        if not docids:
            if data.get('property_id'):
                docids = [data['property_id']]
            else:
                docids = self.env.context.get('active_ids', [])
        docs = self.env['estate.property'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'estate.property',
            'docs': docs,
            'design': data.get('design', '1'),
            'show_contact': data.get('show_contact', True),
            'desc_corta': {d.id: _ficha_excerpt(d.description) for d in docs},
            'fonts_css': _ficha_fonts_css(),
            # Se precalcula aquí (y no con t-set en una plantilla compartida)
            # porque QWeb aísla el contexto de los t-call: las variables
            # definidas dentro no llegan a la plantilla que lo invoca.
            'ficha': {d.id: self._ficha_data(d) for d in docs},
        }

    def _ficha_data(self, prop):
        """Datos ya formateados que consumen las tres plantillas."""
        es_venta = prop.offer_type == 'sale'
        precio = prop.price if es_venta else prop.rental_price
        hero = prop.image_main or (prop.image_ids[0].image if prop.image_ids else False)
        galeria = [i.image for i in prop.image_ids if i.image and i.image != hero][:3]
        ciudad = (prop.city or '') + ((', ' + prop.state_id.name) if prop.state_id else '')
        partner = prop.user_id.partner_id
        return {
            'es_venta': es_venta,
            'op': 'En venta' if es_venta else 'En arriendo',
            'precio_fmt': '{:,.0f}'.format(precio or 0).replace(',', '.'),
            'hero': hero,
            'gal': galeria,
            'gal_ids': [i.id for i in prop.image_ids if i.image and i.image != hero][:3],
            'ciudad': ciudad,
            'tel': partner.mobile or partner.phone or self.env.company.phone or '',
            'email_asesor': partner.email or '',
            'area': '{:g}'.format(prop.area or 0),
            'banos': '{:g}'.format(prop.bathrooms or 0),
            'avm_fmt': ('{:,.0f}'.format(prop.avm_estimated_price).replace(',', '.')
                        if prop.avm_estimated_price else ''),
        }
