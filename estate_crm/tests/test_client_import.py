# -*- coding: utf-8 -*-
"""Importador de clientes desde Excel: mapeo de campos reales, clasificación
por tipo (etiquetas), creación de oportunidades por Estado, y deduplicación."""
import base64
import io

from odoo.tests.common import TransactionCase, tagged


def _build_xlsx(headers, rows):
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return base64.b64encode(buf.getvalue())


@tagged('post_install', '-at_install', 'estate_client_import')
class TestClientImport(TransactionCase):

    HEADERS = ['Número de identificación', 'Nombre', 'Apellidos', 'Tipo De Cliente',
               'Correo Electrónico', 'Teléfono', 'Móvil', 'Ubicación', 'Estado',
               'Comentarios del cliente', 'Observaciones Adicionales', 'Recibe Correo',
               'Fecha Registro', 'Referido', 'Medio de captación', 'Etiqueta',
               'Inmuebles enlazados', 'Encargado Del Cliente']

    def _row(self, nombre, apellidos, movil='', email='', tipo='Cliente Comprador',
             estado='Captado', ubic='Cuenca Azuay', captacion='Fan page facebook',
             encargado='', idnum='', coment=''):
        return [idnum, nombre, apellidos, tipo, email, '', movil, ubic, estado,
                coment, '', 'No', '2024-01-01', '', captacion, '', '', encargado]

    def _import(self, rows, **kw):
        """Ejecuta la importación en la misma transacción del test.

        En producción corre en segundo plano (cron) y hace commits; aquí se
        llama a _do_import() directamente para no romper el rollback del test."""
        job = self.env['estate.client.import'].create(dict({
            'file': _build_xlsx(self.HEADERS, rows), 'filename': 'test.xlsx',
        }, **kw))
        job.result_log = job._do_import()
        job.state = 'done'
        return job

    def test_se_encola_para_segundo_plano(self):
        """Regresión: con miles de filas la importación no cabía en la petición
        HTTP y el navegador cortaba la conexión. Ahora solo se encola."""
        job = self.env['estate.client.import'].create({
            'file': _build_xlsx(self.HEADERS, [self._row('Cola', 'Test', movil='593950000001')]),
            'filename': 'test.xlsx',
        })
        self.assertEqual(job.state, 'draft')

        job.action_start()

        self.assertEqual(job.state, 'pending', "Debe quedar EN COLA, no ejecutarse al vuelo")
        self.assertFalse(
            self.env['res.partner'].search([('mobile', '=', '593950000001')]),
            "Todavía no debe haber importado nada: lo hace el cron")

    def test_el_cron_procesa_lo_encolado(self):
        job = self.env['estate.client.import'].create({
            'file': _build_xlsx(self.HEADERS, [self._row('Cron', 'Test', movil='593950000002')]),
            'filename': 'test.xlsx',
            'state': 'pending',
        })
        # _do_import es lo que ejecuta el cron (sin los commits, para el test)
        job.result_log = job._do_import()
        job.state = 'done'

        self.assertEqual(job.state, 'done')
        self.assertTrue(self.env['res.partner'].search([('mobile', '=', '593950000002')]))
        self.assertIn('Contactos creados: 1', job.result_log)

    def test_no_crea_actividades_ni_mensajes_por_lead(self):
        """La notificación por lead (mensaje + actividad) hacía la importación
        lentísima: se salta en importaciones masivas."""
        self._import([self._row('Rapido', 'Test', movil='593950000003',
                                tipo='Cliente Comprador')])
        p = self.env['res.partner'].search([('mobile', '=', '593950000003')], limit=1)
        lead = self.env['crm.lead'].search([('partner_id', '=', p.id)], limit=1)
        self.assertTrue(lead)
        self.assertFalse(lead.activity_ids,
                         "No debe crear la actividad de 'primer contacto' en cada lead")

    def test_llena_campos_reales_y_etiqueta_por_tipo(self):
        self._import([
            self._row('Ana', 'García', movil='593999111222', email='ana@test.com',
                      ubic='Cuenca Azuay', tipo='Cliente Comprador'),
        ])
        ana = self.env['res.partner'].search([('mobile', '=', '593999111222')], limit=1)
        self.assertEqual(ana.name, 'Ana García')
        self.assertEqual(ana.email, 'ana@test.com')
        self.assertEqual(ana.city, 'Cuenca')
        self.assertEqual(ana.state_id.name, 'Azuay', "Debe separar provincia de ciudad")
        # Etiquetada por su tipo (no un genérico 'Importado Wasi')
        self.assertIn('Cliente Comprador', ana.category_id.mapped('name'))

    def test_comentario_solo_texto_libre(self):
        self._import([self._row('Beto', 'Luna', movil='593900000001', coment='Cliente VIP')])
        p = self.env['res.partner'].search([('mobile', '=', '593900000001')], limit=1)
        # comment es un campo Html -> el texto va envuelto en <p>, pero SIN volcado de datos
        self.assertIn('Cliente VIP', str(p.comment or ''))
        self.assertNotIn('Importado', str(p.comment or ''))
        self.assertNotIn('Encargado', str(p.comment or ''))

    def test_comprador_crea_lead_en_etapa_por_estado(self):
        self._import([self._row('Caro', 'Ruiz', movil='593900000002',
                                tipo='Cliente Comprador', estado='Seguimiento')])
        p = self.env['res.partner'].search([('mobile', '=', '593900000002')], limit=1)
        lead = self.env['crm.lead'].search([('partner_id', '=', p.id)], limit=1)
        self.assertTrue(lead, "Un comprador debe generar oportunidad")
        self.assertEqual(lead.stage_id, self.env.ref('estate_crm.stage_lead3b_estate_seguimiento'))

    def test_propietario_no_crea_lead_y_se_marca_owner(self):
        self._import([self._row('Don', 'Pedro', movil='593900000003', tipo='Propietario')])
        p = self.env['res.partner'].search([('mobile', '=', '593900000003')], limit=1)
        self.assertTrue(p.is_property_owner)
        self.assertFalse(self.env['crm.lead'].search([('partner_id', '=', p.id)]),
                         "Un propietario no debe generar oportunidad de compra")

    def test_perdido_va_a_la_columna_perdido_y_se_ve(self):
        """El comprador Perdido entra en la etapa 'Perdido', VISIBLE en el embudo
        (no archivado), pero sigue contando como perdido."""
        self._import([self._row('Eva', 'Mora', movil='593900000004',
                                tipo='Cliente Comprador', estado='Perdido')])
        p = self.env['res.partner'].search([('mobile', '=', '593900000004')], limit=1)
        lead = self.env['crm.lead'].search([('partner_id', '=', p.id)], limit=1)
        self.assertTrue(lead, "Por defecto los perdidos SÍ se importan")
        self.assertTrue(lead.active, "No debe quedar archivado/escondido")
        self.assertEqual(lead.stage_id, self.env.ref('estate_crm.stage_lead_perdido'))
        self.assertEqual(lead.won_status, 'lost', "Sigue contando como perdido")
        self.assertTrue(lead.lost_reason_id, "Debe llevar su motivo de pérdida")

    def test_perdido_puede_omitirse(self):
        """Si se desactiva la opción, el perdido queda solo como contacto."""
        self._import([self._row('Ivo', 'Sol', movil='593900000005',
                                tipo='Cliente Comprador', estado='Perdido')],
                     import_lost=False)
        p = self.env['res.partner'].search([('mobile', '=', '593900000005')], limit=1)
        self.assertTrue(p, "El contacto sí se crea")
        self.assertFalse(
            self.env['crm.lead'].with_context(active_test=False).search(
                [('partner_id', '=', p.id)]),
            "Sin la opción, no se genera oportunidad para el perdido")

    def test_empareja_asesores_con_nombre_distinto(self):
        """El Excel escribe el asesor distinto a como está en Odoo:
        - tilde:   'Robert Mirabá' (Excel) vs 'Robert Miraba' (usuario)
        - 2º nombre: 'Carlos Payan' (Excel) vs 'Carlos Eduardo Payan' (usuario)
        Deben emparejar igual, para que el lead no quede sin asignar."""
        miraba = self.env['res.users'].create({
            'name': 'Robert Miraba', 'login': 'robert_miraba_imp',
            'email': 'robert_imp@test.com'})
        payan = self.env['res.users'].create({
            'name': 'Carlos Eduardo Payan', 'login': 'carlos_payan_imp',
            'email': 'payan_imp@test.com'})

        self._import([
            self._row('Cli', 'Uno', movil='593910000001', encargado='Robert Mirabá'),
            self._row('Cli', 'Dos', movil='593910000002', encargado='Carlos Payan'),
        ])

        p1 = self.env['res.partner'].search([('mobile', '=', '593910000001')], limit=1)
        p2 = self.env['res.partner'].search([('mobile', '=', '593910000002')], limit=1)
        lead1 = self.env['crm.lead'].search([('partner_id', '=', p1.id)], limit=1)
        lead2 = self.env['crm.lead'].search([('partner_id', '=', p2.id)], limit=1)

        self.assertEqual(lead1.user_id, miraba, "La tilde no debe impedir el emparejamiento")
        self.assertEqual(lead2.user_id, payan, "El segundo nombre tampoco")

    def test_no_asigna_asesor_si_es_ambiguo(self):
        """Si el nombre del Excel encaja con VARIOS usuarios, no se arriesga."""
        self.env['res.users'].create({
            'name': 'Ana Perez Uno', 'login': 'ana_uno_imp', 'email': 'a1@test.com'})
        self.env['res.users'].create({
            'name': 'Ana Perez Dos', 'login': 'ana_dos_imp', 'email': 'a2@test.com'})

        self._import([self._row('Cli', 'Tres', movil='593910000003', encargado='Ana Perez')])

        p = self.env['res.partner'].search([('mobile', '=', '593910000003')], limit=1)
        lead = self.env['crm.lead'].search([('partner_id', '=', p.id)], limit=1)
        self.assertFalse(lead.user_id,
                         "Ante la duda, mejor sin asignar que asignar al equivocado")

    def test_estados_que_van_a_cierre(self):
        """Regresión: 'Cierre' salía vacío porque estos estados del Excel no
        estaban mapeados y caían en 'Recepción'."""
        cierre = self.env.ref('estate_crm.stage_lead7_estate_cierre')
        for i, estado in enumerate(['Cierre', 'Vendido por Inmobi', 'Vendido Externo']):
            movil = f'59392000000{i}'
            self._import([self._row('Ganado', f'Test{i}', movil=movil,
                                    tipo='Cliente Comprador', estado=estado)])
            p = self.env['res.partner'].search([('mobile', '=', movil)], limit=1)
            lead = self.env['crm.lead'].search([('partner_id', '=', p.id)], limit=1)
            self.assertEqual(lead.stage_id, cierre,
                              f'El estado "{estado}" debe ir a la etapa Cierre')

    def test_estados_con_variantes_de_escritura(self):
        """'Proceso de Cierre', 'Necesidad' y las tildes deben mapear igual."""
        casos = {
            'Proceso de Cierre': 'stage_lead4_estate_papeles',
            'Necesidad': 'stage_lead2b_estate_con_necesidad',
            'COMISIÓN': 'stage_pv_comision',   # tilde + mayúsculas
            'Seña': 'stage_pv_sena',
        }
        for i, (estado, xmlid) in enumerate(casos.items()):
            movil = f'59393000000{i}'
            self._import([self._row('Var', f'Test{i}', movil=movil,
                                    tipo='Cliente Comprador', estado=estado)])
            p = self.env['res.partner'].search([('mobile', '=', movil)], limit=1)
            lead = self.env['crm.lead'].search([('partner_id', '=', p.id)], limit=1)
            self.assertEqual(lead.stage_id, self.env.ref(f'estate_crm.{xmlid}'),
                              f'"{estado}" debe mapear a {xmlid}')

    def test_avisa_de_los_estados_que_no_reconoce(self):
        wiz = self._import([self._row('Raro', 'Test', movil='593940000001',
                                      tipo='Cliente Comprador', estado='Estado Inventado')])
        self.assertIn('no reconozco', wiz.result_log)
        self.assertIn('estado inventado', wiz.result_log.lower())

    def test_fila_sin_contacto_se_dedupe_por_nombre(self):
        """Filas SIN celular/correo/cédula: se deduplican por nombre. (Regresión:
        antes fallaban con 'Cannot convert res.partner.company_type to SQL'.)"""
        rows = [self._row('Sin', 'Contacto', movil='', email='')]
        w1 = self._import(rows)
        self.assertIn('Errores: 0', w1.result_log)
        n = self.env['res.partner'].search_count([('name', '=', 'Sin Contacto')])
        self.assertEqual(n, 1)
        w2 = self._import(rows)  # reimportar
        self.assertIn('Errores: 0', w2.result_log)
        self.assertEqual(self.env['res.partner'].search_count([('name', '=', 'Sin Contacto')]), 1,
                         "No debe duplicar la fila sin datos de contacto")

    def test_reimportar_actualiza_no_duplica(self):
        rows = [self._row('Nara', 'Vaca', movil='593900000006', tipo='Cliente Comprador')]
        self._import(rows)
        n_partners = self.env['res.partner'].search_count([('mobile', '=', '593900000006')])
        p = self.env['res.partner'].search([('mobile', '=', '593900000006')], limit=1)
        n_leads = self.env['crm.lead'].search_count([('partner_id', '=', p.id)])
        self._import(rows)  # segunda vez
        self.assertEqual(self.env['res.partner'].search_count([('mobile', '=', '593900000006')]),
                         n_partners, "No debe duplicar contactos")
        self.assertEqual(self.env['crm.lead'].search_count([('partner_id', '=', p.id)]),
                         n_leads, "No debe duplicar oportunidades")

    def test_vendedor_va_a_etapa_segun_estado_y_vendedores_queda_vacia(self):
        """Un Cliente Vendedor se encauza a la etapa que corresponde a su Estado
        en Wasi/Excel, en lugar de enviarse a la etapa Vendedores (que debe estar vacía)."""
        self._import([
            self._row('Juan', 'Vendedor', movil='593900000010',
                      tipo='Cliente Vendedor', estado='Seña'),
            self._row('María', 'Vendedora', movil='593900000011',
                      tipo='Cliente Vendedor', estado='Seguimiento')
        ])
        p1 = self.env['res.partner'].search([('mobile', '=', '593900000010')], limit=1)
        p2 = self.env['res.partner'].search([('mobile', '=', '593900000011')], limit=1)
        lead1 = self.env['crm.lead'].search([('partner_id', '=', p1.id)], limit=1)
        lead2 = self.env['crm.lead'].search([('partner_id', '=', p2.id)], limit=1)

        self.assertEqual(lead1.stage_id, self.env.ref('estate_crm.stage_pv_sena'),
                         "Vendedor con estado Seña debe ir a la etapa Seña del embudo postventa")
        self.assertEqual(lead1.team_id, self.env.ref('estate_crm.crm_team_postventa'),
                         "Trámite de postventa debe tener equipo Postventa")
        self.assertEqual(lead2.stage_id, self.env.ref('estate_crm.stage_lead3b_estate_seguimiento'),
                         "Vendedor con estado Seguimiento debe ir a Seguimiento")

        vendedores_stage = self.env.ref('estate_crm.stage_lead_vendedores')
        stuck_count = self.env['crm.lead'].search_count([('stage_id', '=', vendedores_stage.id)])
        self.assertEqual(stuck_count, 0, "La etapa Vendedores debe quedar completamente vacía")

    def test_reimportar_actualiza_y_vacia_etapa_vendedores(self):
        """Si ya existían leads retenidos en la etapa Vendedores por importaciones previas,
        al reimportar se actualizan/reubican a su etapa real y Vendedores queda vacía."""
        vendedores_stage = self.env.ref('estate_crm.stage_lead_vendedores')
        p = self.env['res.partner'].create({'name': 'Carlos Retenido', 'mobile': '593900000012'})
        crm_tag = self.env['crm.tag'].search([('name', '=', 'Wasi')], limit=1) or self.env['crm.tag'].create({'name': 'Wasi'})
        lead = self.env['crm.lead'].create({
            'name': 'Carlos Retenido',
            'partner_id': p.id,
            'stage_id': vendedores_stage.id,
            'tag_ids': [(4, crm_tag.id)]
        })
        self.assertEqual(lead.stage_id, vendedores_stage)

        w = self._import([self._row('Carlos', 'Retenido', movil='593900000012',
                                    tipo='Cliente Vendedor', estado='Minuta')])
        self.assertEqual(lead.stage_id, self.env.ref('estate_crm.stage_pv_minuta'),
                         "El lead retenido debe actualizarse a Minuta en el reimport")
        self.assertIn('Vendedores', w.result_log)
        self.assertEqual(self.env['crm.lead'].search_count([('stage_id', '=', vendedores_stage.id)]), 0,
                         "La etapa Vendedores debe quedar vacía")

    def test_no_retrocede_etapa_con_filas_duplicadas_o_reimport(self):
        """Si en el Excel hay filas duplicadas (ej. caso Marcelo Zhinin: 'En Proceso Cierre'
        y luego 'Nuevo') o si se reimporta el Excel sobre un lead ya avanzado, no debe
        retroceder su etapa en el embudo."""
        papeles = self.env.ref('estate_crm.stage_lead4_estate_papeles') # seq=5
        nuevo = self.env.ref('estate_crm.stage_lead1_estate_nuevo') # seq=1

        # Simulamos las 2 filas de Marcelo Zhinin en el Excel
        self._import([
            self._row('Marcelo', 'Zhinin', movil='593992535865',
                      tipo='Cliente Comprador', estado='En Proceso Cierre'),
            self._row('Marcelo', 'Zhinin', movil='593992535865',
                      tipo='Cliente Comprador', estado='Nuevo')
        ])

        p = self.env['res.partner'].search([('mobile', '=', '593992535865')], limit=1)
        lead = self.env['crm.lead'].search([('partner_id', '=', p.id)], limit=1)
        self.assertEqual(lead.stage_id, papeles,
                         "La fila 'Nuevo' no debe haber retrocedido la oportunidad desde 'En Proceso Cierre'")
