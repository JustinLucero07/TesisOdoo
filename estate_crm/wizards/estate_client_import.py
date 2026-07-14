# -*- coding: utf-8 -*-
"""Importador de clientes desde el Excel exportado de Wasi.

Lee el .xlsx SIN openpyxl (parseo directo del ZIP/XML) porque el export de
Wasi trae un `pageSetup` que openpyxl no puede parsear. Llena los campos
reales del contacto, clasifica con etiquetas según el "Tipo De Cliente", y
para los compradores crea una oportunidad en el CRM en la etapa que
corresponde a su "Estado" en Wasi. Es idempotente: reimportar actualiza en
vez de duplicar."""
import base64
import io
import logging
import re
import unicodedata
import zipfile
from collections import Counter
from xml.etree import ElementTree as ET

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

_NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'

# Encabezados del export de Wasi (se emparejan por nombre, sin distinguir
# mayúsculas ni espacios, así que aunque cambie el orden funciona).
COL = {
    'nombre': 'nombre', 'apellidos': 'apellidos', 'tipo': 'tipo de cliente',
    'email': 'correo electrónico', 'tel': 'teléfono', 'movil': 'móvil',
    'ubic': 'ubicación', 'estado': 'estado', 'coment': 'comentarios del cliente',
    'obs': 'observaciones adicionales', 'fecha': 'fecha registro',
    'referido': 'referido', 'captacion': 'medio de captación',
    'inmuebles': 'inmuebles enlazados', 'encargado': 'encargado del cliente',
    'id': 'número de identificación',
}

# Estado (Wasi) -> etapa (xmlid de estate_crm).
# OJO: las claves van SIN TILDES y en minúscula; la búsqueda se hace con
# _deaccent(), así que "Comisión"/"comision"/"COMISION" caen en la misma.
STAGE_BY_ESTADO = {
    # --- Embudo comercial ("Proceso de Ventas") ---
    'nuevo': 'stage_lead1_estate_nuevo',
    'recepcion': 'stage_lead1_estate_nuevo',
    'captado': 'stage_lead1_estate_nuevo',
    'buscando': 'stage_lead1_estate_nuevo',
    'seguimiento': 'stage_lead3b_estate_seguimiento',
    'necesidades': 'stage_lead2b_estate_con_necesidad',
    'necesidad': 'stage_lead2b_estate_con_necesidad',
    'en proceso cierre': 'stage_lead4_estate_papeles',
    'proceso de cierre': 'stage_lead4_estate_papeles',
    'en proceso de cierre': 'stage_lead4_estate_papeles',
    # Negocios ganados -> etapa puente "Cierre"
    'cierre': 'stage_lead7_estate_cierre',
    'vendido externo': 'stage_lead7_estate_cierre',
    'vendido por inmobi': 'stage_lead7_estate_cierre',
    'vendido': 'stage_lead7_estate_cierre',
    # --- Embudo postventa ("Ventas Cerradas"): ya están en el trámite ---
    'sena': 'stage_pv_sena',
    'financiamiento': 'stage_pv_financiamiento',
    'minuta': 'stage_pv_minuta',
    'transferencia de dominio': 'stage_pv_transferencia',
    'pago de impuestos': 'stage_pv_impuestos',
    'escritura': 'stage_pv_escritura',
    'registro propiedad': 'stage_pv_registro',
    'desembolso banco': 'stage_pv_desembolso',
    'encuesta': 'stage_pv_encuesta',
    'comision': 'stage_pv_comision',
}
# Etapas que pertenecen al equipo Postventa (el lead debe ir a ese equipo)
POSTVENTA_STAGES = {
    'stage_pv_sena', 'stage_pv_financiamiento', 'stage_pv_minuta',
    'stage_pv_transferencia', 'stage_pv_impuestos', 'stage_pv_escritura',
    'stage_pv_registro', 'stage_pv_desembolso', 'stage_pv_encuesta',
    'stage_pv_comision',
}
# "Perdido" no es etapa: se usa el mecanismo nativo de Odoo (archivar con motivo)
LOST_ESTADOS = {'perdido', 'dejo de vender', 'descartado', 'no interesado'}
# Etapa para los clientes de tipo vendedor
STAGE_VENDEDORES = 'stage_lead_vendedores'

# Medio de captación (Wasi) -> código de fuente ya existente en el catálogo
SOURCE_CODE_BY_CAPTACION = {
    'fan page facebook': 'facebook', 'facebook': 'facebook',
    'instagram': 'instagram', 'tik tok': 'other', 'tiktok': 'other',
    'portal inmobiliario': 'portal', 'portal inmobliario': 'portal',
    'oficina': 'walk_in', 'letrero': 'other',
}


def _norm(s):
    return (s or '').strip().lower()


def _deaccent(s):
    """Minúsculas y sin tildes, para emparejar nombres de asesores aunque el
    Excel los escriba distinto ('Robert Mirabá' vs el usuario 'Robert Miraba')."""
    txt = unicodedata.normalize('NFKD', (s or '').strip().lower())
    return ' '.join(''.join(c for c in txt if not unicodedata.combining(c)).split())


def _digits(value):
    return re.sub(r'\D', '', str(value or ''))


class EstateClientImport(models.Model):
    """Importación de clientes. NO es un asistente volátil: es un registro que
    persiste, porque el proceso corre EN SEGUNDO PLANO (vía cron).

    Con miles de filas la importación no cabe en una petición HTTP: el navegador
    corta la conexión ("se perdió la conexión") y la migración quedaba a medias.
    Ahora al pulsar Importar solo se encola; el cron la ejecuta y aquí queda el
    resultado."""
    _name = 'estate.client.import'
    _description = 'Importar Clientes desde Excel (Wasi)'
    _order = 'id desc'

    name = fields.Char(string='Importación', compute='_compute_name', store=True)
    file = fields.Binary(string='Archivo Excel (.xlsx)', required=True, attachment=True)
    filename = fields.Char(string='Nombre del archivo')
    create_leads = fields.Boolean(
        string='Crear oportunidades en el CRM', default=True,
        help='Para los clientes compradores, crea una oportunidad en el CRM en la '
             'etapa que corresponde a su Estado en Wasi.')
    import_lost = fields.Boolean(
        string='Incluir perdidos', default=True,
        help='Los clientes en estado "Perdido" generan su oportunidad en la etapa '
             'PERDIDO con su motivo. Desactívalo si prefieres que queden solo como '
             'contacto.')
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('pending', 'En cola'),
        ('running', 'Procesando...'),
        ('done', 'Terminada'),
        ('failed', 'Falló'),
    ], default='draft', string='Estado', readonly=True)
    result_log = fields.Text(string='Resultado', readonly=True)
    started_at = fields.Datetime(string='Inicio', readonly=True)
    finished_at = fields.Datetime(string='Fin', readonly=True)

    @api.depends('filename', 'create_date')
    def _compute_name(self):
        for rec in self:
            fecha = fields.Datetime.to_string(rec.create_date)[:16] if rec.create_date else ''
            rec.name = f'{rec.filename or "Excel"} — {fecha}'

    # --------------------------------------------------------- encolar / cron
    def action_start(self):
        """Encola la importación y despierta al cron para que la procese ya."""
        self.ensure_one()
        if not self.file:
            raise UserError('Sube primero el archivo Excel.')
        self.write({'state': 'pending', 'result_log': False})
        cron = self.env.ref('estate_crm.ir_cron_client_import', raise_if_not_found=False)
        if cron:
            cron.sudo()._trigger()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Importación en cola',
                'message': ('Se está procesando en segundo plano. Puedes seguir '
                            'trabajando: al terminar verás el resultado en '
                            'CRM → Configuración → Importar Clientes.'),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }

    @api.model
    def _cron_run_imports(self):
        """Procesa las importaciones encoladas, una por una."""
        for job in self.search([('state', '=', 'pending')], order='id asc', limit=5):
            job.action_run()

    # ------------------------------------------------------------------ parse
    def _parse_xlsx(self, blob):
        try:
            z = zipfile.ZipFile(io.BytesIO(blob))
        except Exception:
            raise UserError('El archivo no es un .xlsx válido. Sube el Excel exportado de Wasi.')

        shared = []
        if 'xl/sharedStrings.xml' in z.namelist():
            t = ET.fromstring(z.read('xl/sharedStrings.xml'))
            for si in t.findall(f'{_NS}si'):
                shared.append(''.join(node.text or '' for node in si.iter(f'{_NS}t')))

        sheet_path = 'xl/worksheets/sheet1.xml'
        if sheet_path not in z.namelist():
            sheets = sorted(n for n in z.namelist() if n.startswith('xl/worksheets/sheet'))
            if not sheets:
                raise UserError('El Excel no contiene hojas de datos.')
            sheet_path = sheets[0]

        t = ET.fromstring(z.read(sheet_path))
        data = t.find(f'{_NS}sheetData')
        if data is None:
            return [], []

        def col_index(ref):
            m = re.match(r'([A-Z]+)', ref or 'A')
            s = 0
            for c in m.group(1):
                s = s * 26 + (ord(c) - 64)
            return s - 1

        rows = []
        for row in data.findall(f'{_NS}row'):
            cells = {}
            for c in row.findall(f'{_NS}c'):
                ci = col_index(c.get('r'))
                ctype = c.get('t')
                if ctype == 'inlineStr':
                    is_el = c.find(f'{_NS}is')
                    if is_el is not None:
                        cells[ci] = ''.join(node.text or '' for node in is_el.iter(f'{_NS}t'))
                    continue
                v = c.find(f'{_NS}v')
                if v is None:
                    continue
                cells[ci] = shared[int(v.text)] if ctype == 's' else v.text
            rows.append(cells)

        if not rows:
            return [], []
        hdr = rows[0]
        width = (max(hdr) + 1) if hdr else 0
        headers = [_norm(hdr.get(i, '')) for i in range(width)]
        return headers, rows[1:]

    # --------------------------------------------------------------- caches
    def _build_caches(self):
        Source = self.env['estate.crm.lead.source'].sudo()
        Users = self.env['res.users'].sudo()
        Tag = self.env['res.partner.category'].sudo()

        # Provincias de Ecuador para separar ciudad/provincia de "Ubicación"
        states = self.env['res.country.state'].sudo().search(
            [('country_id.code', '=', 'EC')])
        prov_by_name = {_norm(s.name): s for s in states}
        ec = self.env['res.country'].sudo().search([('code', '=', 'EC')], limit=1)

        # Etapas
        stages = {}
        for xmlid in set(STAGE_BY_ESTADO.values()) | {STAGE_VENDEDORES}:
            rec = self.env.ref(f'estate_crm.{xmlid}', raise_if_not_found=False)
            if rec:
                stages[xmlid] = rec
        stage_default = self.env.ref('estate_crm.stage_lead1_estate_nuevo', raise_if_not_found=False)
        postventa_team = self.env.ref('estate_crm.crm_team_postventa', raise_if_not_found=False)
        lost_reason = self.env.ref('estate_crm.lost_reason_no_contact', raise_if_not_found=False)
        lost_stage = self.env.ref('estate_crm.stage_lead_perdido', raise_if_not_found=False)

        return {
            'postventa_team': postventa_team, 'lost_reason': lost_reason,
            'lost_stage': lost_stage,
            # Usuarios internos, para emparejar al "Encargado del cliente"
            'all_users': Users.search([('share', '=', False), ('active', '=', True)]),
            'Source': Source, 'Users': Users, 'Tag': Tag,
            'prov_by_name': prov_by_name, 'country_ec': ec,
            'stages': stages, 'stage_default': stage_default,
            'source_cache': {}, 'advisor_cache': {}, 'tag_cache': {},
            'crm_tag': self._get_or_create_crm_tag(),
            # Etiqueta de la importación vieja, para quitarla al reimportar limpio
            'legacy_tag': Tag.search([('name', '=', 'Importado Wasi')], limit=1),
        }

    def _get_or_create_crm_tag(self):
        Tag = self.env['crm.tag'].sudo()
        tag = Tag.search([('name', '=', 'Wasi')], limit=1)
        return tag or Tag.create({'name': 'Wasi'})

    def _resolve_advisor(self, cx, name):
        key = _norm(name)
        if not key:
            return False
        if key in cx['advisor_cache']:
            return cx['advisor_cache'][key]

        user = cx['Users'].browse()
        wanted = _deaccent(name)
        # 1) Coincidencia exacta ignorando tildes y mayúsculas
        #    ("Robert Mirabá" del Excel -> usuario "Robert Miraba")
        for candidate in cx['all_users']:
            if _deaccent(candidate.name) == wanted:
                user = candidate
                break
        # 2) Por palabras: todas las del Excel están en el nombre del usuario
        #    ("Carlos Payan" -> usuario "Carlos Eduardo Payan"). Solo se acepta
        #    si hay UN único candidato, para no asignar al asesor equivocado.
        if not user:
            tokens = set(wanted.split())
            matches = [
                c for c in cx['all_users']
                if tokens and tokens.issubset(set(_deaccent(c.name).split()))
            ]
            if len(matches) == 1:
                user = matches[0]

        cx['advisor_cache'][key] = user or False
        return cx['advisor_cache'][key]

    def _resolve_source(self, cx, captacion):
        key = _norm(captacion)
        if not key:
            return False
        if key in cx['source_cache']:
            return cx['source_cache'][key]
        src = False
        code = SOURCE_CODE_BY_CAPTACION.get(key)
        if code:
            src = cx['Source'].search([('code', '=', code)], limit=1)
        if not src:
            src = cx['Source'].search([('name', '=ilike', captacion.strip())], limit=1)
        if not src:
            src = cx['Source'].create({'name': captacion.strip()})
        cx['source_cache'][key] = src.id
        return src.id

    def _resolve_type_tags(self, cx, tipo):
        """Una etiqueta de contacto por cada tipo (ej. 'Cliente Comprador')."""
        tag_ids = []
        for part in (tipo or '').split(','):
            label = part.strip()
            if not label:
                continue
            key = _norm(label)
            if key not in cx['tag_cache']:
                t = cx['Tag'].search([('name', '=ilike', label)], limit=1)
                if not t:
                    t = cx['Tag'].create({'name': label})
                cx['tag_cache'][key] = t.id
            tag_ids.append(cx['tag_cache'][key])
        return tag_ids

    def _split_location(self, cx, ubic):
        """'Cuenca Azuay' -> (city='Cuenca', state=Azuay)."""
        loc = (ubic or '').strip()
        if not loc:
            return loc, False
        low = _norm(loc)
        for pname in sorted(cx['prov_by_name'], key=len, reverse=True):
            if low.endswith(pname):
                city = loc[: len(loc) - len(pname)].strip(' ,')
                return (city or loc), cx['prov_by_name'][pname]
        return loc, False

    # ----------------------------------------------------------------- import
    def action_run(self):
        """Ejecuta la importación. La llama el cron (segundo plano)."""
        self.ensure_one()
        self.write({'state': 'running', 'started_at': fields.Datetime.now()})
        self.env.cr.commit()  # que se vea "Procesando..." desde ya
        try:
            log = self._do_import()
            self.write({'state': 'done', 'result_log': log,
                        'finished_at': fields.Datetime.now()})
        except Exception as e:
            self.env.cr.rollback()
            _logger.exception('Importación de clientes falló')
            self.write({'state': 'failed', 'result_log': f'ERROR: {e}',
                        'finished_at': fields.Datetime.now()})
        self.env.cr.commit()
        return True

    def _do_import(self):
        self.ensure_one()
        if not self.file:
            raise UserError('Sube primero el archivo Excel.')
        headers, rows = self._parse_xlsx(base64.b64decode(self.file))
        if not headers:
            raise UserError('No se pudieron leer los encabezados del Excel.')

        idx = {h: i for i, h in enumerate(headers)}

        def get(cells, key):
            i = idx.get(COL[key])
            if i is None:
                return ''
            val = cells.get(i)
            return (str(val).strip() if val not in (None, '') else '')

        # Contexto de importación masiva: sin seguimiento en el chatter, sin
        # suscriptores y sin la notificación/actividad por cada lead. Sin esto,
        # 2.400 leads generaban decenas de miles de escrituras y la importación
        # tardaba una eternidad.
        env = self.env(context=dict(
            self.env.context,
            tracking_disable=True,
            mail_create_nolog=True,
            mail_create_nosubscribe=True,
            mail_notrack=True,
            skip_lead_notification=True,
        ))
        Partner = env['res.partner'].sudo()
        Lead = env['crm.lead'].sudo()
        cx = self._build_caches()

        p_created = p_updated = leads_created = skipped_empty = errors = 0
        advisors_found, advisors_missing = set(), set()
        unmapped_estados = Counter()
        error_samples = []

        total = len(rows)
        for n, cells in enumerate(rows, start=2):
            # Guardar avance cada 200 filas: si algo se cae, no se pierde todo,
            # y la transacción no crece sin control.
            if n % 200 == 0:
                env.cr.commit()
                _logger.info('Importación de clientes: %s/%s filas procesadas',
                             n - 1, total)
            if not any(v not in (None, '') for v in cells.values()):
                continue
            try:
                nombre, apellidos = get(cells, 'nombre'), get(cells, 'apellidos')
                name = f'{nombre} {apellidos}'.strip()
                movil, tel = get(cells, 'movil'), get(cells, 'tel')
                email = get(cells, 'email').lower() or False
                idnum = get(cells, 'id')
                if not (name or movil or tel or email):
                    skipped_empty += 1
                    continue

                tipo = get(cells, 'tipo')
                tipo_low = _norm(tipo)
                is_buyer = 'comprador' in tipo_low or 'buscando' in tipo_low
                is_owner = 'propietario' in tipo_low or 'arrendador' in tipo_low
                # Cliente vendedor -> va a la etapa "Vendedores" del embudo comercial
                is_seller = 'vendedor' in tipo_low and not is_buyer

                encargado = get(cells, 'encargado')
                advisor = self._resolve_advisor(cx, encargado)
                if encargado:
                    (advisors_found if advisor else advisors_missing).add(encargado)

                city, state = self._split_location(cx, get(cells, 'ubic'))
                # Comentario: SOLO el texto libre real (no volcamos la clasificación)
                notas = [x for x in (get(cells, 'coment'), get(cells, 'obs')) if x]
                comment = '\n'.join(notas) or False

                # --- Deduplicación del contacto ---
                partner = Partner.browse()
                if idnum:
                    partner = Partner.search([('id_number', '=', idnum)], limit=1)
                if not partner and movil:
                    partner = Partner.search(
                        ['|', ('mobile', '=', movil), ('phone', '=', movil)], limit=1)
                if not partner and email:
                    partner = Partner.search([('email', '=', email)], limit=1)
                # Último recurso para filas SIN celular/correo/cédula: por nombre,
                # para que reimportar no las duplique.
                if not partner and not (movil or email or idnum) and name:
                    # OJO: company_type es calculado y NO almacenado -> no se puede
                    # buscar por él. Se filtra por is_company (sí almacenado).
                    partner = Partner.search(
                        [('name', '=', name), ('is_company', '=', False)], limit=1)

                type_tag_ids = self._resolve_type_tags(cx, tipo)
                # Campos "identidad" (no se pisan si el contacto ya los tiene)
                ident = {}
                if movil:
                    ident['mobile'] = movil
                if tel:
                    ident['phone'] = tel
                if email:
                    ident['email'] = email
                if idnum:
                    ident['id_number'] = idnum
                # Campos "autoritativos" del Excel (SÍ se (sobre)escriben, para
                # corregir importaciones viejas con datos volcados en notas)
                auth = {'comment': comment}
                if city:
                    auth['city'] = city
                if state:
                    auth['state_id'] = state.id
                if cx['country_ec']:
                    auth['country_id'] = cx['country_ec'].id
                if advisor:
                    auth['user_id'] = advisor.id
                if is_owner:
                    auth['is_property_owner'] = True

                if partner:
                    upd = dict(auth)
                    # identidad: solo si está vacía en el contacto actual
                    for k, v in ident.items():
                        if not partner[k]:
                            upd[k] = v
                    tag_cmds = [(4, tid) for tid in type_tag_ids]
                    if cx['legacy_tag']:  # limpiar etiqueta vieja "Importado Wasi"
                        tag_cmds.append((3, cx['legacy_tag'].id))
                    upd['category_id'] = tag_cmds
                    upd['customer_rank'] = 1
                    partner.write(upd)
                    p_updated += 1
                else:
                    partner = Partner.create(dict(
                        ident, **auth,
                        name=name or (movil or email or 'Cliente'),
                        company_type='person', customer_rank=1,
                        category_id=[(4, tid) for tid in type_tag_ids],
                    ))
                    p_created += 1

                # --- Oportunidad CRM: compradores y clientes vendedores ---
                if self.create_leads and (is_buyer or is_seller):
                    # Sin tildes, para que "Comisión"/"comision" caigan igual
                    estado = _deaccent(get(cells, 'estado'))
                    is_lost = estado in LOST_ESTADOS
                    if is_lost and not self.import_lost:
                        continue

                    lead = Lead.with_context(active_test=False).search([
                        ('partner_id', '=', partner.id),
                        ('tag_ids', 'in', cx['crm_tag'].id),
                    ], limit=1)

                    # Los vendedores van siempre a la etapa "Vendedores";
                    # los compradores, a la etapa que corresponde a su Estado.
                    if is_seller:
                        stage_xmlid = STAGE_VENDEDORES
                    else:
                        stage_xmlid = STAGE_BY_ESTADO.get(estado)
                        if not stage_xmlid and estado and not is_lost:
                            # Estado que no reconocemos: se avisa en el resultado
                            # para no dejarlo pasar en silencio.
                            unmapped_estados[estado] += 1
                    stage = cx['stages'].get(stage_xmlid) or cx['stage_default']
                    lvals = {
                        'name': f'{name}' or 'Interés',
                        'type': 'opportunity',
                        'partner_id': partner.id,
                        'contact_name': name or False,
                        'email_from': email or False,
                        'phone': tel or movil or False,
                        'stage_id': stage.id if stage else False,
                        'tag_ids': [(4, cx['crm_tag'].id)],
                        # Si no se identificó al asesor, el lead queda SIN asignar
                        # (si no, Odoo se lo pondría por defecto a quien importa).
                        'user_id': advisor.id if advisor else False,
                    }
                    # Si su Estado ya es un trámite de "Ventas Cerradas",
                    # el negocio entra directo al equipo Postventa.
                    if stage_xmlid in POSTVENTA_STAGES and cx['postventa_team']:
                        lvals['team_id'] = cx['postventa_team'].id
                    src_id = self._resolve_source(cx, get(cells, 'captacion'))
                    if src_id:
                        lvals['lead_source_id'] = src_id
                    inmuebles = get(cells, 'inmuebles')
                    if inmuebles:
                        lvals['description'] = f'Inmuebles enlazados (Wasi): {inmuebles}'
                    if is_lost:
                        # Van a la etapa "Perdido" (visible en su columna), con
                        # probabilidad 0 y su motivo: cuentan como perdidos en
                        # los reportes sin quedar escondidos/archivados.
                        if cx['lost_stage']:
                            lvals['stage_id'] = cx['lost_stage'].id
                        lvals['probability'] = 0
                        if cx['lost_reason']:
                            lvals['lost_reason_id'] = cx['lost_reason'].id

                    if lead:
                        lead.write(lvals)
                    else:
                        Lead.create(lvals)
                        leads_created += 1
            except Exception as e:
                errors += 1
                if len(error_samples) < 5:
                    error_samples.append(f'  fila {n}: {e}')
                _logger.warning('Import cliente fila %s falló: %s', n, e)

        log = [
            f'Filas de datos leídas: {len(rows)}',
            f'Contactos creados: {p_created}',
            f'Contactos actualizados (ya existían): {p_updated}',
            f'Oportunidades CRM creadas: {leads_created}',
            f'Omitidos por vacío: {skipped_empty}',
            f'Errores: {errors}',
        ]
        if advisors_found:
            log.append('\nAsesores emparejados con usuarios de Odoo: '
                       + ', '.join(sorted(advisors_found)))
        if advisors_missing:
            log.append('Asesores SIN usuario en Odoo (leads quedaron sin asignar): '
                       + ', '.join(sorted(advisors_missing)))
        if unmapped_estados:
            detalle = ', '.join(f'"{e}" ({n})' for e, n in unmapped_estados.most_common())
            log.append('\nEstados del Excel que no reconozco (esos leads quedaron en '
                       '"Recepción"): ' + detalle)
        log.append('\nLos contactos quedaron etiquetados por su tipo (Comprador, '
                   'Propietario, ...) y las oportunidades con la etiqueta "Wasi".')
        if error_samples:
            log.append('\nPrimeros errores:\n' + '\n'.join(error_samples))

        return '\n'.join(log)
