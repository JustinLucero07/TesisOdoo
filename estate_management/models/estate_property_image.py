import base64
import io
import re
import zipfile

from odoo import models, fields, api
from odoo.exceptions import UserError


class EstatePropertyImage(models.Model):
    _name = 'estate.property.image'
    _description = 'Imagen de Propiedad'
    _order = 'sequence, id'

    name = fields.Char(string='Nombre', default='Imagen')
    sequence = fields.Integer(string='Secuencia', default=10)
    image = fields.Binary(string='Imagen', required=True, attachment=True)
    property_id = fields.Many2one(
        'estate.property', string='Propiedad',
        required=True, ondelete='cascade')

    @api.model_create_multi
    def create(self, vals_list):
        for i, vals in enumerate(vals_list):
            if not vals.get('name') or vals.get('name') == 'Imagen':
                # Auto-numerar: busca cuántas imágenes tiene la propiedad
                prop_id = vals.get('property_id')
                if prop_id:
                    count = self.search_count([('property_id', '=', prop_id)])
                    vals['name'] = f'Imagen {count + i + 1}'
                else:
                    vals['name'] = f'Imagen {i + 1}'
        return super().create(vals_list)

    # ── Descarga ────────────────────────────────────────────────────────────
    def _safe_filename(self, indice=None):
        """Nombre de archivo usable: sin acentos raros ni barras."""
        self.ensure_one()
        base = self.name or 'imagen'
        base = re.sub(r'[^\w\s.-]', '', base).strip().replace(' ', '_') or 'imagen'
        if indice is not None:
            base = '%02d_%s' % (indice, base)
        return base if base.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')) else base + '.jpg'

    def action_download_image(self):
        """Descarga esta sola foto."""
        self.ensure_one()
        if not self.image:
            raise UserError('Esta imagen no tiene archivo.')
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/estate.property.image/%d/image/%s?download=true'
                   % (self.id, self._safe_filename()),
            'target': 'self',
        }

    def action_download_selection(self):
        """Empaqueta en un ZIP las fotos marcadas en la lista."""
        imagenes = self.filtered('image')
        if not imagenes:
            raise UserError('Selecciona al menos una imagen con archivo.')
        if len(imagenes) == 1:
            return imagenes.action_download_image()
        return imagenes._build_zip_download()

    def _build_zip_download(self, nombre_zip=None):
        """Arma el ZIP y lo entrega por descarga."""
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as z:
            usados = set()
            for i, img in enumerate(self.filtered('image'), start=1):
                nombre = img._safe_filename(indice=i)
                while nombre in usados:
                    nombre = '%d_%s' % (i, nombre)
                usados.add(nombre)
                z.writestr(nombre, base64.b64decode(img.image))

        propiedad = self[:1].property_id
        if not nombre_zip:
            base = re.sub(r'[^\w\s-]', '', propiedad.title or propiedad.name or 'fotos')
            nombre_zip = (base.strip().replace(' ', '_') or 'fotos') + '.zip'

        descarga = self.env['estate.property.image.download'].create({
            'zip_file': base64.b64encode(buffer.getvalue()),
            'zip_filename': nombre_zip,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/estate.property.image.download/%d/zip_file/%s?download=true'
                   % (descarga.id, nombre_zip),
            'target': 'self',
        }


class EstatePropertyImageDownload(models.TransientModel):
    """Sostiene el ZIP el tiempo justo para que el navegador lo descargue."""
    _name = 'estate.property.image.download'
    _description = 'Descarga de fotos de la propiedad'

    zip_file = fields.Binary(string='Archivo ZIP', attachment=True)
    zip_filename = fields.Char(string='Nombre del archivo')
