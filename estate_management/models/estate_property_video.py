from odoo import fields, models


class EstatePropertyVideo(models.Model):
    """Videos de la propiedad.

    Van aparte de estate.property.image a propósito: la galería de fotos la
    consumen WordPress, las publicaciones en redes, la ficha PDF, la hoja de
    captación, los reportes y el agente IA, y ninguno sabe qué hacer con un
    video. Así los videos se quedan solo en Odoo y no viajan a la web.

    El video no se copia a un campo binario: se reaprovecha el adjunto que
    subió el navegador, que ya trae el tipo de archivo correcto y no se
    duplica en disco, y se sirve con /web/content, que permite adelantar y
    retroceder en el reproductor.
    """
    _name = 'estate.property.video'
    _description = 'Video de Propiedad'
    _order = 'sequence, id'

    name = fields.Char(string='Nombre', required=True, default='Video')
    sequence = fields.Integer(string='Secuencia', default=10)
    property_id = fields.Many2one(
        'estate.property', string='Propiedad',
        required=True, ondelete='cascade', index=True)
    # El adjunto se reasigna a este registro (res_model/res_id): así Odoo lo
    # borra solo al borrar el video, sin tener que hacerlo a mano.
    attachment_id = fields.Many2one(
        'ir.attachment', string='Archivo', required=True, ondelete='restrict')
    mimetype = fields.Char(related='attachment_id.mimetype', string='Tipo')
    file_size_mb = fields.Float(
        string='Tamaño (MB)', compute='_compute_file_size_mb', digits=(10, 1))
    video_url = fields.Char(compute='_compute_video_url')

    def _compute_file_size_mb(self):
        for rec in self:
            rec.file_size_mb = (rec.attachment_id.file_size or 0) / (1024 * 1024)

    def _compute_video_url(self):
        for rec in self:
            rec.video_url = (
                '/web/content/%d' % rec.attachment_id.id if rec.attachment_id else False)

    def action_download_video(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%d?download=true' % self.attachment_id.id,
            'target': 'self',
        }
