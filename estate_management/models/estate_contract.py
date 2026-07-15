import base64
import io
import logging
import re

from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class EstateContract(models.Model):
    _name = 'estate.contract'
    _description = 'Contrato Inmobiliario'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc, id desc'

    name = fields.Char(
        string='Referencia', readonly=True, copy=False,
        default='Nuevo')

    # Trazabilidad: origen del contrato
    offer_id = fields.Many2one(
        'estate.property.offer', string='Oferta de Origen', readonly=True,
        help='Oferta aceptada que generó este contrato.')
    sale_order_id = fields.Many2one(
        'sale.order', string='Orden de Venta', readonly=True,
        help='Orden de venta de Odoo vinculada a este contrato.')
    property_id = fields.Many2one(
        'estate.property', string='Propiedad', required=True, tracking=True, index=True)
    partner_id = fields.Many2one(
        'res.partner', string='Cliente', required=True, tracking=True, index=True)
    user_id = fields.Many2one(
        'res.users', string='Agente Responsable',
        default=lambda self: self.env.user, tracking=True)

    contract_type = fields.Selection([
        ('exclusive_owner', 'Corretaje Con Exclusividad (Propietario)'),
        ('exclusive_proxy', 'Corretaje Con Exclusividad (Apoderado)'),
        ('non_exclusive_owner', 'Corretaje Sin Exclusividad (Propietario)'),
        ('non_exclusive_proxy', 'Corretaje Sin Exclusividad (Apoderado)'),
        ('no_contract', 'Sin Contrato'),
        ('sale', 'Compraventa (General)'),
        ('rent', 'Arriendo (General)'),
        ('exclusive', 'Exclusividad (General)'),
    ], string='Tipo de Contrato', required=True, default='exclusive_owner', tracking=True)

    proxy_partner_id = fields.Many2one('res.partner', string='Apoderado / Representante', tracking=True)
    proxy_name = fields.Char(string='Nombre Apoderado', compute='_compute_proxy_data', store=True, readonly=False)
    proxy_vat = fields.Char(string='Cédula / RUC Apoderado', compute='_compute_proxy_data', store=True, readonly=False)
    commission_percentage = fields.Float(string='Porcentaje Honorarios (%)', default=5.0, tracking=True)

    @api.depends('proxy_partner_id')
    def _compute_proxy_data(self):
        for rec in self:
            if rec.proxy_partner_id:
                rec.proxy_name = rec.proxy_partner_id.name or ''
                rec.proxy_vat = rec.proxy_partner_id.vat or ''

    @api.onchange('property_id')
    def _onchange_property_proxy(self):
        if self.property_id:
            if self.property_id.proxy_id and not self.proxy_partner_id:
                self.proxy_partner_id = self.property_id.proxy_id
            if self.property_id.price and not self.amount:
                self.amount = self.property_id.price

    date_start = fields.Date(string='Fecha de Inicio', required=True,
                             default=fields.Date.today, tracking=True)
    date_end = fields.Date(string='Fecha de Vencimiento', tracking=True)
    amount = fields.Float(string='Monto del Contrato', tracking=True)
    currency_id = fields.Many2one(
        'res.currency', string='Moneda',
        default=lambda self: self.env.company.currency_id)

    state = fields.Selection([
        ('draft',     'Borrador'),
        ('active',    'Activo'),
        ('suspended', 'Suspendido'),
        ('renewing',  'En Renovación'),
        ('renewed',   'Renovado'),
        ('expired',   'Vencido'),
        ('cancelled', 'Cancelado'),
    ], string='Estado', default='draft', tracking=True, required=True)

    parent_contract_id = fields.Many2one(
        'estate.contract', string='Contrato Padre', readonly=True,
        help='Si este contrato es una renovación, apunta al original.')
    child_contract_ids = fields.One2many(
        'estate.contract', 'parent_contract_id', string='Contratos Hijos (Renovaciones)')

    notes = fields.Html(string='Notas / Cláusulas')
    payment_ids = fields.One2many(
        'estate.payment', 'contract_id', string='Pagos')
    
    customer_signature = fields.Binary(string='Firma del Cliente', copy=False, attachment=True)
    signature_date = fields.Datetime(string='Fecha de Firma', readonly=True)
    earnest_money_filename = fields.Char(string='Nombre del Archivo de Arras')
    earnest_money_contract = fields.Binary(string='Contrato de Arras', attachment=True,
                                          help='Documento escaneado o PDF del Contrato de Arras firmado.')
    signed_contract = fields.Binary(string='Contrato Firmado', attachment=True,
                                    help='Documento escaneado o PDF del contrato final firmado por ambas partes.')
    signed_contract_filename = fields.Char(string='Nombre del Contrato Firmado')
    earnest_is_pdf = fields.Boolean(compute='_compute_contract_is_pdf')
    signed_is_pdf = fields.Boolean(compute='_compute_contract_is_pdf')

    @api.depends('earnest_money_filename', 'signed_contract_filename')
    def _compute_contract_is_pdf(self):
        for rec in self:
            rec.earnest_is_pdf = bool(rec.earnest_money_filename and rec.earnest_money_filename.lower().endswith('.pdf'))
            rec.signed_is_pdf = bool(rec.signed_contract_filename and rec.signed_contract_filename.lower().endswith('.pdf'))

    payment_count = fields.Integer(
        string='# Pagos', compute='_compute_payment_count')
    total_paid = fields.Float(
        string='Total Pagado', compute='_compute_payment_count')

    invoice_count = fields.Integer(
        string='Facturas', compute='_compute_invoice_count')

    @api.depends('payment_ids.invoice_id')
    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = len(rec.payment_ids.mapped('invoice_id'))

    # ------------------------------------------------------------------
    # Validaciones de integridad de datos
    # ------------------------------------------------------------------

    @api.constrains('amount')
    def _check_amount(self):
        for rec in self:
            if rec.amount < 0:
                raise UserError('El monto del contrato no puede ser negativo.')

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for rec in self:
            if rec.date_end and rec.date_start and rec.date_end < rec.date_start:
                raise UserError('La fecha de vencimiento no puede ser anterior a la fecha de inicio.')

    @api.onchange('amount')
    def _onchange_contract_amount_warn(self):
        if self.amount is not False and self.amount < 0:
            return {'warning': {
                'title': 'Monto inválido',
                'message': 'El monto del contrato no puede ser negativo.',
            }}

    @api.onchange('date_start', 'date_end')
    def _onchange_contract_dates_warn(self):
        if self.date_end and self.date_start and self.date_end < self.date_start:
            return {'warning': {
                'title': 'Fechas incoherentes',
                'message': 'La fecha de vencimiento no puede ser anterior a la fecha de inicio.',
            }}

    def action_view_invoices(self):
        self.ensure_one()
        invoice_ids = self.payment_ids.mapped('invoice_id').ids
        return {
            'type': 'ir.actions.act_window',
            'name': f'Facturas — {self.name}',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', invoice_ids)],
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code('estate.contract') or 'Nuevo'
        contracts = super().create(vals_list)
        for contract in contracts:
            if contract.partner_id:
                contract.partner_id._apply_estate_category('estate_management.partner_category_client')
            # Sincronizar fecha de vencimiento con la propiedad
            if contract.date_end and contract.property_id:
                contract.property_id.sudo().contract_end_date = contract.date_end
        return contracts

    def write(self, vals):
        res = super().write(vals)
        # Si cambia la fecha de vencimiento, actualizar en la propiedad vinculada
        if 'date_end' in vals:
            for rec in self:
                if rec.property_id and vals['date_end']:
                    rec.property_id.sudo().contract_end_date = vals['date_end']
        return res

    def unlink(self):
        _BLOCKED = ('active', 'suspended', 'renewing', 'renewed')
        blocked = self.filtered(lambda c: c.state in _BLOCKED)
        if blocked:
            names = ', '.join(blocked.mapped('name'))
            raise UserError(
                f"No se puede eliminar un contrato en estado activo o en proceso: {names}.\n\n"
                "Cancele el contrato primero antes de eliminarlo."
            )
        return super().unlink()

    @api.depends('name', 'property_id', 'partner_id')
    def _compute_display_name(self):
        for rec in self:
            prop_name = rec.property_id.title if rec.property_id else ''
            client = rec.partner_id.name if rec.partner_id else ''
            if prop_name or client:
                rec.display_name = f"{rec.name} - {prop_name} ({client})"
            else:
                rec.display_name = rec.name

    @api.depends('payment_ids', 'payment_ids.state', 'payment_ids.amount')
    def _compute_payment_count(self):
        for rec in self:
            paid_payments = rec.payment_ids.filtered(lambda p: p.state == 'paid')
            rec.payment_count = len(rec.payment_ids)
            rec.total_paid = sum(paid_payments.mapped('amount'))

    def _advance_related_lead(self, xmlid):
        """Avanza el lead vinculado a este contrato a la etapa indicada."""
        for rec in self:
            # Buscar por oferta de origen, luego por partner+propiedad
            lead = None
            if rec.offer_id and rec.offer_id.lead_id:
                lead = rec.offer_id.lead_id
            if not lead and rec.partner_id:
                lead = self.env['crm.lead'].sudo().search([
                    ('partner_id', '=', rec.partner_id.id),
                    ('stage_id.is_won', '=', False),
                ], limit=1)
            if lead:
                lead._advance_lead_to_stage(xmlid)

    _VALID_STATE_TRANSITIONS = {
        'draft':     ['active', 'cancelled'],
        'active':    ['suspended', 'renewing', 'expired', 'cancelled'],
        'suspended': ['active', 'cancelled', 'expired'],
        'renewing':  ['renewed', 'active', 'cancelled'],
        'renewed':   [],  # estado terminal, ver child_contract_ids
        'expired':   ['draft', 'renewing'],
        'cancelled': ['draft'],
    }

    def _check_state_transition(self, new_state):
        for rec in self:
            allowed = self._VALID_STATE_TRANSITIONS.get(rec.state, [])
            if new_state not in allowed:
                raise UserError(
                    f'No se puede cambiar el contrato "{rec.name}" '
                    f'de "{rec.state}" a "{new_state}". '
                    f'Transiciones permitidas: {", ".join(allowed) or "ninguna"}.'
                )

    def action_activate(self):
        self._check_state_transition('active')
        for rec in self:
            rec.state = 'active'
            # Coherencia del flujo: al activar el contrato, la propiedad refleja
            # el cierre (Compraventa -> Vendida; Arriendo -> Arrendada).
            if rec.property_id:
                if rec.contract_type == 'sale' and rec.property_id.state != 'sold':
                    vals = {'state': 'sold'}
                    if rec.partner_id and not rec.property_id.buyer_id:
                        vals['buyer_id'] = rec.partner_id.id
                    rec.property_id.write(vals)
                    rec.property_id.message_post(
                        body=f"Propiedad marcada como VENDIDA al activar el contrato {rec.name}.")
                elif rec.contract_type == 'rent' and rec.property_id.state != 'rented':
                    rec.property_id.write({'state': 'rented', 'offer_type': 'rent'})
                    rec.property_id.message_post(
                        body=f"Propiedad marcada como ARRENDADA al activar el contrato {rec.name}.")
            if rec.partner_id.email:
                template = self.env.ref(
                    'estate_management.mail_template_contract_activated', raise_if_not_found=False)
                if template:
                    template.send_mail(rec.id, force_send=True)
        self._advance_related_lead('estate_crm.stage_lead7_estate_cierre')

    def action_cancel(self):
        self._check_state_transition('cancelled')
        self.write({'state': 'cancelled'})

    def action_set_expired(self):
        self._check_state_transition('expired')
        self.write({'state': 'expired'})

    def action_reset_draft(self):
        self._check_state_transition('draft')
        self.write({'state': 'draft'})

    # ── Cláusulas asistidas por IA ───────────────────────────────────────────
    def action_ai_draft_clauses(self):
        """Usa la IA (Gemini/OpenAI) para REDACTAR o MEJORAR las cláusulas del
        contrato a partir de sus datos. No reemplaza al abogado: deja una
        propuesta editable en el campo 'Notas / Cláusulas'."""
        self.ensure_one()
        Mixin = self.env['estate.genai.mixin']
        if not Mixin._genai_is_active():
            raise UserError(
                'Configura primero el Asistente IA (Gemini u OpenAI) en Ajustes '
                'para poder redactar cláusulas con IA.')
        prop = self.property_id
        tipo = dict(self._fields['contract_type'].selection).get(self.contract_type, 'inmobiliario')
        vendedor = (prop.owner_id.name if prop and prop.owner_id else self.env.company.name)
        prompt = (
            "Actúa como abogado inmobiliario en Ecuador. Redacta o mejora las "
            f"CLÁUSULAS de un contrato de {tipo}. Usa lenguaje jurídico claro.\n\n"
            "Datos del contrato:\n"
            f"- Propiedad: {(prop.title or prop.name) if prop else '-'} "
            f"({prop.city if prop else '-'})\n"
            f"- Vendedor/Arrendador: {vendedor}\n"
            f"- Comprador/Arrendatario: {self.partner_id.name or '-'}\n"
            f"- Monto: ${self.amount:,.2f}\n"
            f"- Vigencia: {self.date_start or '-'} a {self.date_end or 'indefinida'}\n\n"
            "Cláusulas actuales (mejóralas si existen; si no, créalas):\n"
            f"{self.notes or '(ninguna)'}\n\n"
            "Devuelve SOLO las cláusulas numeradas (PRIMERA, SEGUNDA, ...) en HTML "
            "simple con etiquetas <p>, profesionales y específicas a estos datos. "
            "No incluyas encabezados, firmas ni explicaciones.")
        raw = Mixin._genai_generate(prompt, temperature=0.4)
        if not raw:
            raise UserError('La IA no devolvió contenido. Intenta de nuevo.')
        clean = Mixin._genai_strip_fences(raw) if hasattr(Mixin, '_genai_strip_fences') else raw
        self.notes = clean
        self.message_post(body='Cláusulas redactadas/mejoradas con IA (revisar y ajustar).')
        return True

    # ── Generación desde plantilla Word (.docx con marcadores) ───────────────
    @api.model
    def _num2words_es(self, number):
        """Convierte un número a texto en palabras en español."""
        try:
            number = int(round(float(number)))
        except (ValueError, TypeError):
            return ""
        if number == 0:
            return "CERO"
        
        unidades = ["", "UNO", "DOS", "TRES", "CUATRO", "CINCO", "SEIS", "SIETE", "OCHO", "NUEVE", 
                    "DIEZ", "ONCE", "DOCE", "TRECE", "CATORCE", "QUINCE", "DIECISÉIS", "DIECISIETE", "DIECIOCHO", "DIECINUEVE"]
        decenas = ["", "", "VEINTE", "TREINTA", "CUARENTA", "CINCUENTA", "SESENTA", "SETENTA", "OCHENTA", "NOVENTA"]
        centenas = ["", "CIENTO", "DOSCIENTOS", "TRESCIENTOS", "CUATROCIENTOS", "QUINIENTOS", "SEISCIENTOS", "SETECIENTOS", "OCHOCIENTOS", "NOVECIENTOS"]

        def _convert_group(n):
            if n == 100:
                return "CIEN"
            res = ""
            c = n // 100
            d = (n % 100) // 10
            u = n % 10
            if c > 0:
                res += centenas[c] + " "
            if n % 100 < 20 and n % 100 > 0:
                res += unidades[n % 100]
            else:
                if d > 0:
                    if d == 2 and u > 0:
                        res += "VEINTI" + unidades[u]
                        return res.strip()
                    else:
                        res += decenas[d]
                        if u > 0:
                            res += " Y " + unidades[u]
                elif u > 0:
                    res += unidades[u]
            return res.strip()

        if number < 0:
            return "MENOS " + self._num2words_es(abs(number))
        if number < 1000:
            return _convert_group(number)
        if number < 1000000:
            miles = number // 1000
            resto = number % 1000
            prefix = "MIL" if miles == 1 else _convert_group(miles) + " MIL"
            return prefix + (" " + _convert_group(resto) if resto > 0 else "")
        if number < 1000000000:
            millones = number // 1000000
            resto = number % 1000000
            prefix = "UN MILLÓN" if millones == 1 else _convert_group(millones) + " MILLONES"
            return prefix + (" " + self._num2words_es(resto) if resto > 0 else "")
        return str(number)

    def _docx_context(self):
        """Diccionario de marcadores disponibles en la plantilla Word."""
        self.ensure_one()

        def _f(val, dots):
            s = str(val).strip() if val is not None and val is not False else ''
            if s and s not in ('soltero/a / casado/a', 'El Valle / Yanuncay', 'S/N', '010101010101', 'False'):
                return s
            return dots

        def _f_firma(val):
            s = str(val).strip() if val is not None and val is not False else ''
            if s and s not in ('soltero/a / casado/a', 'El Valle / Yanuncay', 'S/N', '010101010101', 'False'):
                return s
            return ''

        prop = self.property_id
        tipo = dict(self._fields['contract_type'].selection).get(self.contract_type, '')
        clausulas = re.sub(r'<[^>]+>', '', self.notes or '').strip()  # quita HTML
        
        # Cálculo de plazo en días y fechas en español
        plazo_dias = 180
        if self.date_start and self.date_end:
            plazo_dias = (self.date_end - self.date_start).days or 180
            
        meses_es = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
        dt_ref = self.date_start or fields.Date.today()
        dia_str = str(dt_ref.day) if self.date_start else ''
        mes_str = (meses_es[dt_ref.month - 1] if 1 <= dt_ref.month <= 12 else str(dt_ref.month)) if self.date_start else ''
        anio_str = str(dt_ref.year) if self.date_start else ''
        
        precio_val = self.amount or (prop.price if prop else 0.0)
        precio_letras = self._num2words_es(precio_val) if precio_val else ''
        honorarios_letras = self._num2words_es(self.commission_percentage) if self.commission_percentage else ''
        
        ciudad_val = (prop.city if prop else '') or (self.env.company.city or '')
        sector_val = prop.sector if prop else ''
        calle_val = prop.street if prop else ''
        numero_val = prop.street_number if prop else ''
        catastral_val = prop.cadastral_code if prop else ''
        propietario_val = (prop.owner_id.name if prop and prop.owner_id else '')
        apoderado_val = self.proxy_name or propietario_val

        ms_dict = {
            'single': 'soltero/a',
            'married': 'casado/a',
            'divorced': 'divorciado/a',
            'widowed': 'viudo/a',
            'cohabiting': 'en unión libre',
        }
        ms_raw = getattr(self.partner_id, 'marital_status', '') or ''
        ms_val = ms_dict.get(ms_raw, ms_raw)
        
        vat_cliente = self.partner_id.vat or getattr(self.partner_id, 'id_number', '') or ''
        vat_proxy = self.proxy_vat or (getattr(self.proxy_partner_id, 'vat', '') if self.proxy_partner_id else '') or ''

        return {
            'empresa': self.env.company.name or '',
            'contrato': self.name or '',
            'tipo_contrato': tipo,
            'cliente': _f(self.partner_id.name, '…………………………………………………………………………………………………'),
            'cedula_cliente': _f(vat_cliente, '………………………………………………………….'),
            'cedula_cliente_firma': _f_firma(vat_cliente),
            'estado_civil': _f(ms_val, '…………………………………….'),
            'propietario': _f(propietario_val, '…………………………………………………………………………………………………'),
            'apoderado': _f(apoderado_val, '…………………………………………………………………………………………………'),
            'cedula_apoderado': _f(vat_proxy, '………………………………………………………….'),
            'cedula_apoderado_firma': _f_firma(vat_proxy),
            'propiedad': (prop.title or prop.name) if prop else '',
            'direccion': ', '.join(filter(None, [prop.street, prop.city])) if prop else '',
            'ciudad': _f(ciudad_val, '……………………'),
            'sector': _f(sector_val, '………………….…..'),
            'calle': _f(calle_val, '………………………………………………………………………………..……'),
            'numero': _f(numero_val, '…………'),
            'clave_catastral': _f(catastral_val, '………………………………………'),
            'plazo_dias': _f(str(plazo_dias) if (self.date_start and self.date_end) else '', '………'),
            'precio': _f(f"{precio_val:,.2f}" if precio_val else '', '..………………………'),
            'precio_letras': _f(precio_letras, '………………………………………………………………………………………………………………………..'),
            'honorarios': _f(f"{self.commission_percentage:g}" if self.commission_percentage else '', '……'),
            'honorarios_letras': _f(honorarios_letras, '……………..'),
            'dia': _f(dia_str, '……'),
            'mes': _f(mes_str, '…………………..'),
            'anio': _f(anio_str, '…………'),
            'fecha_inicio': fields.Date.to_string(self.date_start) or '',
            'fecha_fin': fields.Date.to_string(self.date_end) or '',
            'vendedor': _f(propietario_val, '…………………………………………………………………………………………………'),
            'asesor': self.user_id.name or '',
            'clausulas': clausulas,
        }

    def action_generate_docx(self):
        """Rellena la plantilla Word con los datos de este contrato y devuelve el documento .docx para descargar."""
        self.ensure_one()
        try:
            from docxtpl import DocxTemplate
        except ImportError:
            raise UserError('Falta la librería "docxtpl" en el servidor (pip install docxtpl).')
        
        company = self.env.company
        tpl_data = False
        tpl_filename = False
        
        tpl_map = {
            'exclusive_owner': ('estate_tpl_exclusive_owner', 'tpl_exclusive_owner.docx'),
            'exclusive_proxy': ('estate_tpl_exclusive_proxy', 'tpl_exclusive_proxy.docx'),
            'non_exclusive_owner': ('estate_tpl_non_exclusive_owner', 'tpl_non_exclusive_owner.docx'),
            'non_exclusive_proxy': ('estate_tpl_non_exclusive_proxy', 'tpl_non_exclusive_proxy.docx'),
        }
        
        if self.contract_type in tpl_map:
            field_name, file_name = tpl_map[self.contract_type]
            tpl_data = getattr(company, field_name, False)
            tpl_filename = file_name
        
        if not tpl_data and company.estate_docx_template:
            tpl_data = company.estate_docx_template
        
        tpl_file_obj = None
        if tpl_data:
            tpl_file_obj = io.BytesIO(base64.b64decode(tpl_data))
        elif tpl_filename:
            import os
            import odoo.modules.module as module
            mod_path = module.get_module_path('estate_management')
            full_path = os.path.join(mod_path, 'data', 'templates', tpl_filename)
            if os.path.exists(full_path):
                tpl_file_obj = full_path
        
        if not tpl_file_obj:
            raise UserError(
                'No hay plantilla Word configurada ni pre-cargada para este tipo de contrato. '
                'Súbela en Ajustes → Inmobiliaria → Plantillas de Contratos Word (.docx).')
        
        tpl = DocxTemplate(tpl_file_obj)
        tpl.render(self._docx_context())

        # Postprocesar para que las rayitas de llenado a mano (ej: ………………………) queden en negrita False,
        # mientras que los datos autocompletados desde Odoo sí se conservan en negrita True.
        for p in getattr(tpl, 'paragraphs', []):
            for r in p.runs:
                if r.bold and r.text and set(r.text.strip()) <= {'.', '…', ' ', '·'}:
                    r.bold = False
        for t in getattr(tpl, 'tables', []):
            for row in t.rows:
                for cell in row.cells:
                    for p in cell.paragraphs:
                        for r in p.runs:
                            if r.bold and r.text and set(r.text.strip()) <= {'.', '…', ' ', '·'}:
                                r.bold = False

        out = io.BytesIO()
        tpl.save(out)
        fname = ("Contrato_%s_%s.docx" % (self.contract_type or 'SN', self.name or 'SN')).replace('/', '-')
        attachment = self.env['ir.attachment'].create({
            'name': fname,
            'datas': base64.b64encode(out.getvalue()),
            'res_model': 'estate.contract',
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'new',
        }

    def action_suspend(self):
        """Suspende un contrato activo (impago, juicio, disputa)."""
        self._check_state_transition('suspended')
        for rec in self:
            rec.state = 'suspended'
            rec.message_post(body='⏸ Contrato suspendido. Pagos y vencimiento detenidos hasta reactivación.')

    def action_resume_active(self):
        """Reactiva un contrato suspendido."""
        self._check_state_transition('active')
        for rec in self:
            rec.state = 'active'
            rec.message_post(body='▶ Contrato reactivado.')

    def action_start_renewal(self):
        """Marca el contrato actual como 'en renovación'. Útil para contratos
        que están en proceso de prorrogarse antes del vencimiento."""
        self._check_state_transition('renewing')
        for rec in self:
            rec.state = 'renewing'
            rec.message_post(body='Contrato en proceso de renovación.')

    def action_create_renewal(self):
        """Crea un contrato hijo (renovación) y marca el actual como renovado."""
        self.ensure_one()
        if self.state not in ('renewing', 'active', 'expired'):
            raise UserError('Solo se puede renovar un contrato Activo, En Renovación o Vencido.')
        new_contract = self.copy({
            'name': 'Nuevo',
            'state': 'draft',
            'parent_contract_id': self.id,
            'date_start': fields.Date.today(),
            'date_end': False,
            'offer_id': False,
        })
        # Marcar este contrato como renovado
        self._VALID_STATE_TRANSITIONS['renewing'].append('renewed')  # permitir transición
        self._VALID_STATE_TRANSITIONS['active'].append('renewed')
        self._VALID_STATE_TRANSITIONS['expired'].append('renewed')
        self.write({'state': 'renewed'})
        self.message_post(
            body=f'Renovado mediante el nuevo contrato <b>{new_contract.name}</b>.')
        return {
            'type': 'ir.actions.act_window',
            'name': f'Renovación de {self.name}',
            'res_model': 'estate.contract',
            'view_mode': 'form',
            'res_id': new_contract.id,
        }

    def action_view_offer(self):
        """Abre la oferta original que generó este contrato."""
        self.ensure_one()
        if not self.offer_id:
            raise UserError('Este contrato no tiene oferta de origen registrada.')
        return {
            'type': 'ir.actions.act_window',
            'name': f'Oferta {self.offer_id.name}',
            'res_model': 'estate.property.offer',
            'view_mode': 'form',
            'res_id': self.offer_id.id,
        }

    def action_view_payments(self):
        """Smart-button: ver pagos del contrato."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Pagos — {self.name}',
            'res_model': 'estate.payment',
            'view_mode': 'list,form',
            'domain': [('contract_id', '=', self.id)],
            'context': {'default_contract_id': self.id},
        }

    @api.model
    def _migrate_binary_to_documents(self):
        """Convierte campos Binary heredados (earnest_money_contract, signed_contract,
        customer_signature) en registros de estate.document.
        Idempotente: skip si ya existe un documento del mismo tipo para el contrato.
        """
        Document = self.env['estate.document'].sudo()
        DocType  = self.env['estate.document.type'].sudo()
        if 'estate.document' not in self.env or not DocType.search_count([]):
            _logger.info('Migración omitida: estate_document no instalado o sin tipos.')
            return 0

        type_signed   = DocType.search([('code', '=', 'contract_signed')], limit=1)
        type_earnest  = DocType.search([('code', '=', 'earnest_money')],   limit=1)

        migrated = 0
        contracts = self.search([
            '|', '|',
            ('signed_contract', '!=', False),
            ('earnest_money_contract', '!=', False),
            ('customer_signature', '!=', False),
        ])
        for contract in contracts:
            common = {
                'contract_id': contract.id,
                'property_id': contract.property_id.id,
                'partner_id': contract.partner_id.id,
                'state': 'received',
                'confidentiality': 'restricted',
            }
            # Contrato firmado
            if contract.signed_contract and type_signed:
                exists = Document.search_count([
                    ('contract_id', '=', contract.id),
                    ('type_id', '=', type_signed.id),
                    ('file', '!=', False),
                ])
                if not exists:
                    Document.create({
                        **common,
                        'type_id': type_signed.id,
                        'name': f'Contrato firmado - {contract.name}',
                        'file': contract.signed_contract,
                        'filename': contract.signed_contract_filename or 'contrato.pdf',
                    })
                    migrated += 1
            # Arras
            if contract.earnest_money_contract and type_earnest:
                exists = Document.search_count([
                    ('contract_id', '=', contract.id),
                    ('type_id', '=', type_earnest.id),
                    ('file', '!=', False),
                ])
                if not exists:
                    Document.create({
                        **common,
                        'type_id': type_earnest.id,
                        'name': f'Arras - {contract.name}',
                        'file': contract.earnest_money_contract,
                        'filename': contract.earnest_money_filename or 'arras.pdf',
                    })
                    migrated += 1
        _logger.info('Migración Binary→estate.document completada: %d documentos creados.', migrated)
        return migrated

    @api.model
    def _cron_generate_rent_invoices(self):
        """Cron mensual: genera facturas de renta para contratos de arriendo activos."""
        today = fields.Date.today()
        month_start = today.replace(day=1)
        active_rent = self.search([
            ('contract_type', '=', 'rent'),
            ('state', '=', 'active'),
            ('date_end', '>=', today),
        ])
        for contract in active_rent:
            # Verificar que no se haya generado factura este mes para este contrato
            already_invoiced = self.env['account.move'].search_count([
                ('property_id', '=', contract.property_id.id),
                ('move_type', '=', 'out_invoice'),
                ('estate_transaction_type', '=', 'rent'),
                ('invoice_date', '>=', month_start),
            ])
            if not already_invoiced:
                try:
                    contract.action_generate_rent_invoice()
                except Exception as e:
                    _logger.warning("Error generando factura de alquiler para %s: %s", contract.name, e)
