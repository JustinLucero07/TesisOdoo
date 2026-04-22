from odoo import models, fields, api
from odoo.exceptions import UserError

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    target_property_id = fields.Many2one('estate.property', string='Propiedad de Interés')
    client_budget = fields.Float(string='Presupuesto del Cliente', tracking=True)
    match_percentage = fields.Integer(string='Match con Propiedad (%)', compute='_compute_match_percentage', store=True)

    # --- Canal de captación ---
    lead_source = fields.Selection([
        ('website',   '🌐 Sitio Web'),
        ('wordpress', '📰 WordPress/Houzez'),
        ('whatsapp',  '💬 WhatsApp'),
        ('instagram', '📸 Instagram'),
        ('facebook',  '📘 Facebook'),
        ('google',    '🔍 Google Business'),
        ('referral',  '🤝 Referido'),
        ('phone',     '📞 Llamada Telefónica'),
        ('walk_in',   '🚶 Visita Directa'),
        ('portal',    '👤 Portal del Cliente'),
        ('ai_agent',  '🤖 Agente IA'),
        ('other',     '📌 Otro'),
    ], string='Fuente del Lead', default='website', tracking=True,
       help='Canal por el que llegó este prospecto')

    referral_partner_id = fields.Many2one(
        'res.partner', string='Referido por', tracking=True,
        help='Cliente que refirió este prospecto. Se le notificará al cerrar la venta.')

    # --- Preferencias del cliente ---
    preferred_property_type_id = fields.Many2one(
        'estate.property.type', string='Tipo de Propiedad Buscada')
    preferred_city = fields.Char(
        string='Ciudad Preferida')
    preferred_bedrooms = fields.Integer(
        string='Habitaciones Mínimas')
    preferred_min_area = fields.Float(
        string='Área Mínima (m²)')
    preferred_max_area = fields.Float(
        string='Área Máxima (m²)')

    lead_score = fields.Selection([
        ('low', 'Básico (C)'),
        ('medium', 'Cualificado (B)'),
        ('high', 'Prioritario (A)')
    ], string='Puntuación del Lead', compute='_compute_lead_scoring', store=True, tracking=True)

    lead_temperature = fields.Selection([
        ('cold', 'Frío'),
        ('warm', 'Tibio'),
        ('hot', 'Caliente'),
        ('boiling', '¡Hirviendo!')
    ], string='Temperatura del Lead', compute='_compute_lead_scoring', store=True)

    expected_revenue = fields.Float(string='Comisión Planificada', compute='_compute_financials', store=True)
    expected_commission = fields.Float(string='Comisión Esperada', compute='_compute_financials', store=True)
    
    is_hot_lead = fields.Boolean(string='Prospecto "Caliente"', compute='_compute_lead_scoring', store=True)
    is_golden_opportunity = fields.Boolean(string='Oportunidad de Oro', compute='_compute_lead_scoring', store=True)
    
    lead_velocity_days = fields.Integer(string='Velocidad del Lead (Días)', compute='_compute_lead_velocity', store=True)
    
    smart_negotiation_tips = fields.Text(string='Tips de Negociación IA', compute='_compute_negotiation_strategy')
    
    closing_difficulty = fields.Selection([
        ('easy', 'Fácil'),
        ('moderate', 'Moderada'),
        ('hard', 'Difícil')
    ], string='Dificultad de Cierre', compute='_compute_negotiation_strategy')

    completed_visits_count = fields.Integer(
        string='Visitas Realizadas', compute='_compute_completed_visits', store=True,
        help='Número de visitas completadas con este cliente.')
    response_velocity_hours = fields.Float(
        string='Velocidad de Respuesta (h)', compute='_compute_response_velocity', store=True,
        help='Horas entre la creación del lead y la primera actividad. Menor = más urgente.')
    last_activity_days = fields.Integer(
        string='Días sin Actividad', compute='_compute_last_activity_days',
        help='Días desde la última actividad. Si supera 14, el lead se enfría automáticamente.')

    # --- Ofertas vinculadas al lead ---
    offer_ids = fields.One2many('estate.property.offer', 'lead_id', string='Ofertas')
    offer_count = fields.Integer(string='N° Ofertas', compute='_compute_offer_count')

    # --- Contratos vinculados ---
    interaction_count = fields.Integer(string='Cantidad de Interacciones', compute='_compute_interaction_count')
    interaction_ids = fields.One2many(
        'estate.client.interaction', 'lead_id', string='Interacciones')
    contract_count = fields.Integer(string='Contratos', compute='_compute_contract_count')

    # --- Órdenes de venta vinculadas ---
    sale_order_count = fields.Integer(string='Órdenes de Venta', compute='_compute_sale_order_count')

    # --- Documentos privados (campo declarado en estate_document, aquí solo el count) ---
    estate_document_count = fields.Integer(string='Documentos', compute='_compute_estate_doc_count')

    # --- Mapa de la propiedad seleccionada (related) ---
    property_map_url = fields.Char(string='Mapa de la Propiedad', related='target_property_id.map_url', readonly=True)
    property_latitude = fields.Float(related='target_property_id.latitude', readonly=True)
    property_longitude = fields.Float(related='target_property_id.longitude', readonly=True)

    def _compute_offer_count(self):
        for lead in self:
            lead.offer_count = len(lead.offer_ids)

    def _compute_interaction_count(self):
        Interaction = self.env['estate.client.interaction']
        for lead in self:
            lead.interaction_count = Interaction.search_count([('lead_id', '=', lead.id)])

    def action_view_lead_interactions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Interacciones — {self.name}',
            'res_model': 'estate.client.interaction',
            'view_mode': 'list,form',
            'domain': [('lead_id', '=', self.id)],
            'context': {
                'default_lead_id': self.id,
                'default_partner_id': self.partner_id.id if self.partner_id else False,
                'default_property_id': self.target_property_id.id if self.target_property_id else False,
            },
        }

    def _compute_contract_count(self):
        Contract = self.env['estate.contract']
        for lead in self:
            domain = []
            if lead.partner_id and lead.target_property_id:
                domain = [('partner_id', '=', lead.partner_id.id),
                          ('property_id', '=', lead.target_property_id.id)]
            elif lead.partner_id:
                domain = [('partner_id', '=', lead.partner_id.id)]
            lead.contract_count = Contract.search_count(domain) if domain else 0

    def _compute_sale_order_count(self):
        SaleOrder = self.env['sale.order']
        for lead in self:
            lead.sale_order_count = SaleOrder.search_count([('lead_id', '=', lead.id)])

    def action_view_lead_contracts(self):
        self.ensure_one()
        domain = []
        if self.partner_id and self.target_property_id:
            domain = [('partner_id', '=', self.partner_id.id),
                      ('property_id', '=', self.target_property_id.id)]
        elif self.partner_id:
            domain = [('partner_id', '=', self.partner_id.id)]
        return {
            'type': 'ir.actions.act_window',
            'name': f'Contratos — {self.partner_id.name or self.name}',
            'res_model': 'estate.contract',
            'view_mode': 'list,form',
            'domain': domain,
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_property_id': self.target_property_id.id if self.target_property_id else False,
            },
        }

    def action_view_lead_sale_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Órdenes de Venta — {self.partner_id.name or self.name}',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [('lead_id', '=', self.id)],
            'context': {
                'default_lead_id': self.id,
                'default_partner_id': self.partner_id.id,
                'default_property_id': self.target_property_id.id if self.target_property_id else False,
            },
        }

    def action_create_sale_order_from_lead(self):
        """Crea una orden de venta desde el lead CRM con datos pre-llenados."""
        self.ensure_one()
        if not self.partner_id:
            raise UserError('El lead necesita un Contacto (Cliente) para crear la orden de venta.')
        order_vals = {
            'partner_id': self.partner_id.id,
            'lead_id': self.id,
        }
        if self.target_property_id:
            order_vals['property_id'] = self.target_property_id.id
            order_vals['estate_transaction_type'] = (
                'sale' if self.target_property_id.offer_type == 'sale' else 'rent')
            if self.target_property_id.product_id:
                order_vals['order_line'] = [(0, 0, {
                    'product_id': self.target_property_id.product_id.id,
                    'name': self.target_property_id.title,
                    'price_unit': self.target_property_id.price,
                    'product_uom_qty': 1,
                })]
        order = self.env['sale.order'].create(order_vals)
        self.message_post(
            body=f'🛒 Orden de venta <b>{order.name}</b> creada desde este lead.')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Orden de Venta',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': order.id,
        }

    def _compute_estate_doc_count(self):
        for lead in self:
            if 'document_ids' in lead._fields:
                lead.estate_document_count = len(lead.document_ids)
            else:
                lead.estate_document_count = 0

    def action_view_lead_offers(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Ofertas — {self.partner_id.name or self.contact_name or self.name}',
            'res_model': 'estate.property.offer',
            'view_mode': 'list,form',
            'domain': [('lead_id', '=', self.id)],
            'context': {
                'default_lead_id': self.id,
                'default_property_id': self.target_property_id.id,
                'default_partner_id': self.partner_id.id,
            },
        }

    def action_create_offer_from_lead(self):
        """Crea una oferta desde el lead pre-llenando propiedad y cliente."""
        self.ensure_one()
        if not self.target_property_id:
            raise UserError('Asigna una Propiedad de Interés antes de crear la oferta.')
        if not self.partner_id:
            raise UserError('El lead necesita un Contacto (Cliente) para crear la oferta.')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Nueva Oferta',
            'res_model': 'estate.property.offer',
            'view_mode': 'form',
            'context': {
                'default_lead_id': self.id,
                'default_property_id': self.target_property_id.id,
                'default_partner_id': self.partner_id.id,
                'default_user_id': self.user_id.id,
            },
        }

    def action_view_documents(self):
        """Abre los documentos internos privados del lead."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Documentos — {self.partner_id.name or self.name}',
            'res_model': 'estate.document',
            'view_mode': 'list,form',
            'domain': [('lead_id', '=', self.id)],
            'context': {'default_lead_id': self.id},
        }

    @api.depends('client_budget', 'target_property_id.price', 'probability',
                 'email_from', 'phone', 'match_percentage',
                 'completed_visits_count', 'response_velocity_hours')
    def _compute_lead_scoring(self):
        for lead in self:
            score_points = 0

            # Budget match (0-40 pts)
            if lead.match_percentage >= 80:
                score_points += 40
            elif lead.match_percentage >= 50:
                score_points += 20

            # Contact completeness (0-30 pts)
            if lead.email_from:
                score_points += 15
            if lead.phone:
                score_points += 15

            # Budget size (0-30 pts)
            if lead.client_budget > 100000:
                score_points += 30
            elif lead.client_budget > 50000:
                score_points += 15

            # Response velocity: respondió en < 2h = +15 pts
            if lead.response_velocity_hours < 2.0:
                score_points += 15
            elif lead.response_velocity_hours < 24.0:
                score_points += 5

            # Visitas completadas: +8 pts c/u, máx 24
            score_points += min(lead.completed_visits_count * 8, 24)

            # Comprador anterior: +20 pts
            if lead.partner_id:
                past_purchase = self.env['estate.property'].sudo().search_count([
                    ('buyer_id', '=', lead.partner_id.id),
                    ('state', '=', 'sold'),
                ])
                if past_purchase > 0:
                    score_points += 20

            lead.is_hot_lead = score_points >= 60
            lead.is_golden_opportunity = score_points >= 85

            if score_points >= 80:
                lead.lead_score = 'high'
                lead.lead_temperature = 'boiling'
            elif score_points >= 50:
                lead.lead_score = 'medium'
                lead.lead_temperature = 'hot'
            elif score_points >= 25:
                lead.lead_score = 'low'
                lead.lead_temperature = 'warm'
            else:
                lead.lead_score = 'low'
                lead.lead_temperature = 'cold'

    def _notify_high_score_lead(self):
        """Envía notificación push via Odoo bus al asesor responsable cuando el lead alcanza puntuación alta."""
        for lead in self:
            responsible = lead.user_id or self.env.user
            if not responsible.partner_id:
                continue
            prop_name = lead.target_property_id.title if lead.target_property_id else ''
            client_name = lead.partner_id.name or lead.contact_name or lead.name
            message = (
                f'🔥 Lead de alto score: {client_name}'
                + (f' → {prop_name}' if prop_name else '')
                + f' ({lead.match_percentage}% match, presupuesto ${lead.client_budget:,.0f})'
            )
            self.env['bus.bus']._sendone(
                responsible.partner_id,
                'simple_notification',
                {
                    'title': '⭐ Oportunidad de Oro detectada',
                    'message': message,
                    'sticky': True,
                    'type': 'warning',
                },
            )

    def write(self, vals):
        # Capturar estado anterior de is_golden_opportunity para detectar el cambio
        old_golden = {lead.id: lead.is_golden_opportunity for lead in self}
        result = super().write(vals)
        # Notificar solo leads que acaban de convertirse en "golden"
        newly_golden = self.filtered(
            lambda l: l.is_golden_opportunity and not old_golden.get(l.id, True)
        )
        if newly_golden:
            newly_golden._notify_high_score_lead()
        return result

    @api.depends('client_budget', 'probability')
    def _compute_financials(self):
        for lead in self:
            comm = (lead.client_budget * 0.05) if lead.client_budget else 0.0
            lead.expected_commission = comm
            lead.expected_revenue = comm * (lead.probability / 100.0)

    @api.depends('create_date', 'date_closed', 'active')
    def _compute_lead_velocity(self):
        from datetime import date
        for lead in self:
            start = lead.create_date.date() if lead.create_date else date.today()
            end = lead.date_closed.date() if lead.date_closed else date.today()
            lead.lead_velocity_days = (end - start).days

    # _compute_completed_visits vive en estate_calendar/models/crm_lead.py
    # (R2 fix — eliminada implementación base vacía que sobreescribía la real)

    @api.depends('create_date', 'activity_ids')
    def _compute_response_velocity(self):
        for lead in self:
            if lead.create_date and lead.activity_ids:
                first_activity = min(lead.activity_ids, key=lambda a: a.create_date)
                delta = first_activity.create_date - lead.create_date
                lead.response_velocity_hours = delta.total_seconds() / 3600.0
            else:
                lead.response_velocity_hours = 999.0

    def _compute_last_activity_days(self):
        today = fields.Date.today()
        for lead in self:
            if lead.activity_ids:
                latest = max(lead.activity_ids, key=lambda a: a.create_date)
                lead.last_activity_days = (today - latest.create_date.date()).days
            elif lead.create_date:
                lead.last_activity_days = (today - lead.create_date.date()).days
            else:
                lead.last_activity_days = 0

    @api.depends('match_percentage', 'lead_temperature', 'client_budget')
    def _compute_negotiation_strategy(self):
        for lead in self:
            if lead.match_percentage >= 90:
                lead.closing_difficulty = 'easy'
                lead.smart_negotiation_tips = "Cierre inmediato sugerido. El presupuesto coincide perfectamente con el inmueble."
            elif lead.match_percentage >= 60:
                lead.closing_difficulty = 'moderate'
                lead.smart_negotiation_tips = "Enfoque en financiamiento. El cliente tiene interés pero el presupuesto es ajustado."
            else:
                lead.closing_difficulty = 'hard'
                lead.smart_negotiation_tips = "Requiere seguimiento intensivo o cambio de propiedad objetivo."

    @api.depends('client_budget', 'target_property_id.price',
                 'preferred_property_type_id', 'preferred_city',
                 'preferred_bedrooms', 'preferred_min_area', 'preferred_max_area')
    def _compute_match_percentage(self):
        for lead in self:
            prop = lead.target_property_id
            if not prop or not lead.client_budget or prop.price <= 0:
                lead.match_percentage = 0
                continue

            score = 0

            # Presupuesto (50 pts)
            ratio = lead.client_budget / prop.price
            if ratio >= 1.0:
                score += 50
            elif ratio >= 0.90:
                score += 40
            elif ratio >= 0.75:
                score += 25
            elif ratio >= 0.50:
                score += 10

            # Tipo de propiedad (20 pts)
            if lead.preferred_property_type_id and prop.property_type_id:
                if lead.preferred_property_type_id == prop.property_type_id:
                    score += 20

            # Ciudad (20 pts)
            ref_city = (lead.preferred_city or lead.city or '').strip().lower()
            prop_city = (prop.city or '').strip().lower()
            if ref_city and prop_city and ref_city == prop_city:
                score += 20

            # Habitaciones (10 pts)
            if lead.preferred_bedrooms and prop.bedrooms:
                if prop.bedrooms >= lead.preferred_bedrooms:
                    score += 10
                elif prop.bedrooms == lead.preferred_bedrooms - 1:
                    score += 5

            lead.match_percentage = min(score, 100)

    def action_ai_matchmaker(self):
        for lead in self:
            if not lead.client_budget:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Error AI Matchmaker',
                        'message': 'Defina el Presupuesto del Cliente guiado por el CRM antes de buscar.',
                        'type': 'danger',
                    }
                }
            
            domain = [('state', '=', 'available'), ('price', '>', 0)]
            if lead.preferred_city:
                domain.append(('city', 'ilike', lead.preferred_city))
            elif lead.city:
                domain.append(('city', 'ilike', lead.city))
            if lead.preferred_property_type_id:
                domain.append(('property_type_id', '=', lead.preferred_property_type_id.id))
            properties = self.env['estate.property'].search(domain)

            best_match = None
            best_score = -1

            for prop in properties:
                score = 0
                # Presupuesto (50%)
                ratio = lead.client_budget / prop.price
                if ratio >= 1.0:
                    score += 50
                elif ratio >= 0.90:
                    score += 40
                elif ratio >= 0.75:
                    score += 25
                elif ratio >= 0.50:
                    score += 10
                # Tipo (20%)
                if lead.preferred_property_type_id and prop.property_type_id == lead.preferred_property_type_id:
                    score += 20
                # Habitaciones (10%)
                if lead.preferred_bedrooms and prop.bedrooms >= lead.preferred_bedrooms:
                    score += 10
                if score > best_score:
                    best_score = score
                    best_match = prop
            
            if best_match:
                lead.target_property_id = best_match.id
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': ' AI Matchmaker',
                        'message': f'¡Match encontrado con {int(best_score)}% de compatibilidad! Asignando propiedad {best_match.title or "S/N"}.',
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'AI Matchmaker',
                        'message': 'No hay propiedades compatibles en el catálogo activo en este momento.',
                        'type': 'warning',
                    }
                }

    def action_send_whatsapp(self):
        """Open WhatsApp chat with pre-filled property message."""
        self.ensure_one()
        import urllib.parse
        number = self.phone or (self.partner_id.phone if self.partner_id else '')
        if not number:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'WhatsApp Error',
                    'message': 'El cliente no tiene un número configurado.',
                    'type': 'danger',
                }
            }
        clean_number = "".join(filter(str.isdigit, number))
        prop_name = self.target_property_id.title if self.target_property_id else 'un inmueble'
        msg = f"Hola {self.partner_id.name or self.contact_name or 'cliente'}, le contacto de Elite Inmobiliaria por su interés en {prop_name}."
        url = f"https://wa.me/{clean_number}?text={urllib.parse.quote(msg)}"
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }

    def action_reserve_property_from_lead(self):
        """Marca la propiedad vinculada como RESERVADA y actualiza el lead."""
        self.ensure_one()
        if not self.target_property_id:
            raise UserError('Asigna una Propiedad de Interés antes de reservar.')
        prop = self.target_property_id
        if prop.state not in ('available',):
            raise UserError(
                f'La propiedad "{prop.title}" no está disponible '
                f'(estado actual: {dict(prop._fields["state"].selection).get(prop.state)}).'
            )
        prop.action_set_reserved()
        if not prop.buyer_id and self.partner_id:
            prop.buyer_id = self.partner_id
        self.message_post(
            body=f'🔒 Propiedad <strong>{prop.title}</strong> marcada como <strong>Reservada</strong> desde esta oportunidad.'
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Propiedad Reservada',
                'message': f'"{prop.title}" ha sido reservada exitosamente.',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_print_quotation(self):
        """Genera el PDF de cotización inmobiliaria para este lead."""
        self.ensure_one()
        return self.env.ref('estate_crm.action_report_crm_quotation').report_action(self)

    def action_send_quotation_email(self):
        """Abre el compositor de email con la cotización PDF adjunta."""
        self.ensure_one()
        report = self.env.ref('estate_crm.action_report_crm_quotation')
        ctx = {
            'default_model': 'crm.lead',
            'default_res_ids': self.ids,
            'default_composition_mode': 'comment',
            'default_partner_ids': self.partner_id.ids if self.partner_id else [],
            'default_subject': f'Cotización Inmobiliaria — {self.name}',
            'default_body': (
                f'<p>Estimado/a {self.partner_id.name or self.contact_name or "Cliente"},</p>'
                f'<p>Adjunto encontrará la cotización inmobiliaria para la propiedad de su interés.</p>'
                f'<p>Quedamos a su disposición para cualquier consulta.</p>'
                f'<p>Saludos cordiales,<br/><strong>{self.user_id.name}</strong></p>'
            ),
            'report_action_id': report.id,
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }

    def action_create_invoice_from_lead(self):
        """Genera la factura de venta directamente desde la oportunidad del CRM."""
        self.ensure_one()
        if not self.target_property_id:
            raise UserError('Asigna una Propiedad de Interés al lead antes de generar la factura.')
        if not self.partner_id:
            raise UserError('El lead necesita un Contacto (Cliente) para poder facturar.')
        prop = self.target_property_id
        if not prop.buyer_id:
            prop.buyer_id = self.partner_id
        return prop.action_create_invoice()

    def _advance_lead_to_stage(self, stage_xmlid):
        """Avanza el lead a la etapa indicada, solo si la etapa actual tiene menor secuencia.
        Nunca retrocede el lead. Si la etapa no existe, no hace nada.
        """
        stage = self.env.ref(stage_xmlid, raise_if_not_found=False)
        if not stage:
            return
        for lead in self:
            if not lead.stage_id or lead.stage_id.sequence < stage.sequence:
                lead.stage_id = stage.id

    def action_schedule_meeting(self):
        """One-step visit scheduling: pre-fills the calendar event with property details."""
        self.ensure_one()
        action = super().action_schedule_meeting()
        ctx = dict(action.get('context', {}))
        # Pre-fill lead_id so the event auto-avanza el stage al guardarse
        ctx['default_lead_id'] = self.id
        if self.target_property_id:
            prop = self.target_property_id
            ctx.update({
                'default_property_id': prop.id,
                'default_name': f"Visita: {prop.title or prop.name} — {self.partner_id.name or self.contact_name or 'Cliente'}",
                'default_location': ', '.join(filter(None, [prop.street, prop.city])),
                'default_duration': 1.0,
            })
        action['context'] = ctx
        return action



    @api.model
    def _cron_proactive_matchmaking(self):
        """Busca cruces entre propiedades disponibles y leads activos y notifica al vendedor."""
        leads = self.search([('type', '=', 'lead'), ('stage_id.is_won', '=', False), ('probability', '>', 0)])
        for lead in leads:
            # Skip if no budget
            if not lead.client_budget or lead.client_budget == 0:
                continue
                
            domain = [
                ('state', '=', 'available'),
                ('price', '<=', lead.client_budget * 1.05), # Up to 5% stretch budget
                ('price', '>=', lead.client_budget * 0.70)
            ]
            if lead.city:
                domain.append(('city', 'ilike', lead.city))
                
            matches = self.env['estate.property'].search(domain, limit=3)
            
            # Para no molestar con la misma propiedad, revisar si ya se la enviamos por notas o actividades
            if matches:
                for match in matches:
                    # Check if an activity already exists for this match
                    existing_activity = self.env['mail.activity'].search([
                        ('res_model', '=', 'crm.lead'),
                        ('res_id', '=', lead.id),
                        ('summary', 'ilike', match.name)
                    ])
                    if not existing_activity:
                        self.env['mail.activity'].create({
                            'res_id': lead.id,
                            'res_model_id': self.env['ir.model']._get_id('crm.lead'),
                            'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                            'summary': f"Matchmaking Oportunidad: {match.name} - {match.title}",
                            'note': f"La IA ha detectado una coincidencia. La propiedad {match.title} en {match.city} está a la venta por ${match.price:,.2f}, encajando en el presupuesto del Lead (${lead.client_budget:,.2f}). Considere agendar visita.",
                            'user_id': lead.user_id.id if lead.user_id else self.env.user.id,
                        })


    @api.model
    def _cron_cool_down_inactive_leads(self):
        """Degrada la temperatura de leads sin actividad por 14+ días."""
        leads = self.search([
            ('type', '=', 'lead'),
            ('stage_id.is_won', '=', False),
            ('probability', '>', 0),
            ('lead_temperature', 'in', ['boiling', 'hot']),
        ])
        for lead in leads:
            if lead.last_activity_days >= 14:
                if lead.lead_temperature == 'boiling':
                    lead.lead_temperature = 'hot'
                    lead.message_post(body='🥶 Temperatura degradada automáticamente: Hirviendo → Caliente (sin actividad por 14+ días).')
                elif lead.lead_temperature == 'hot':
                    lead.lead_temperature = 'warm'
                    lead.message_post(body='❄️ Temperatura degradada automáticamente: Caliente → Tibio (sin actividad por 14+ días).')


    @api.model
    def _cron_drip_followup(self):
        """Mejora 4: Secuencia drip automática — crea actividades a los 2, 7 y 14 días."""
        from datetime import timedelta
        today = fields.Date.today()
        leads = self.search([
            ('type', '=', 'lead'),
            ('stage_id.is_won', '=', False),
            ('probability', '>', 0),
            ('active', '=', True),
        ])
        drip_steps = [
            (2, '📩 Seguimiento Día 2', 'Contactar al cliente para confirmar su interés y resolver dudas iniciales.'),
            (7, '📞 Seguimiento Día 7', 'Segunda llamada: explorar objeciones y proponer visita si no se ha concretado.'),
            (14, '🚨 Seguimiento Día 14 — Último intento', 'Ultimo intento de recuperación: ofrecer alternativas o cerrar el lead.'),
        ]
        for lead in leads:
            if not lead.create_date:
                continue
            days_old = (today - lead.create_date.date()).days
            for threshold, summary, note in drip_steps:
                if days_old == threshold:
                    existing = self.env['mail.activity'].search([
                        ('res_model', '=', 'crm.lead'),
                        ('res_id', '=', lead.id),
                        ('summary', '=', summary),
                    ], limit=1)
                    if not existing:
                        self.env['mail.activity'].sudo().create({
                            'res_id': lead.id,
                            'res_model_id': self.env['ir.model'].sudo()._get_id('crm.lead'),
                            'activity_type_id': self.env.ref('mail.mail_activity_data_call').id,
                            'summary': summary,
                            'note': note,
                            'date_deadline': today,
                            'user_id': lead.user_id.id if lead.user_id else self.env.uid,
                        })

    @api.model
    def _cron_hot_lead_no_response_alert(self):
        """Mejora 8: Alerta si un lead HIRVIENDO lleva 48h sin actividad."""
        from datetime import timedelta, datetime
        now = fields.Datetime.now()
        cutoff = now - timedelta(hours=48)
        hot_leads = self.search([
            ('lead_temperature', '=', 'boiling'),
            ('stage_id.is_won', '=', False),
            ('active', '=', True),
        ])
        for lead in hot_leads:
            latest_activity = self.env['mail.activity'].search([
                ('res_model', '=', 'crm.lead'),
                ('res_id', '=', lead.id),
            ], order='create_date desc', limit=1)
            last_touch = latest_activity.create_date if latest_activity else lead.create_date
            if last_touch and last_touch < cutoff:
                existing = self.env['mail.activity'].search([
                    ('res_model', '=', 'crm.lead'),
                    ('res_id', '=', lead.id),
                    ('summary', 'ilike', 'Lead HIRVIENDO sin respuesta'),
                ], limit=1)
                if not existing:
                    self.env['mail.activity'].sudo().create({
                        'res_id': lead.id,
                        'res_model_id': self.env['ir.model'].sudo()._get_id('crm.lead'),
                        'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                        'summary': f'🔥 Lead HIRVIENDO sin respuesta (48h+)',
                        'note': (
                            f'El lead "{lead.partner_id.name or lead.contact_name or "Cliente"}" '
                            f'tiene temperatura HIRVIENDO pero no ha tenido actividad en 48+ horas. '
                            f'Contactar URGENTE antes de que se enfríe.'
                        ),
                        'date_deadline': fields.Date.today(),
                        'user_id': lead.user_id.id if lead.user_id else self.env.uid,
                    })


    @api.model
    def _cron_notify_referrers(self):
        """Detecta leads ganados con referido y notifica al referidor + crea actividad."""
        won_with_referral = self.search([
            ('stage_id.is_won', '=', True),
            ('referral_partner_id', '!=', False),
            ('active', '=', True),
        ])
        for lead in won_with_referral:
            # Verificar que no hayamos notificado antes (buscamos nota en chatter)
            existing = self.env['mail.message'].search([
                ('res_id', '=', lead.id),
                ('model', '=', 'crm.lead'),
                ('body', 'ilike', 'Referidor notificado'),
            ], limit=1)
            if existing:
                continue
            referrer = lead.referral_partner_id
            lead.message_post(
                body=(
                    f'🤝 <b>Referidor notificado:</b> {referrer.name} refirió este cliente. '
                    f'Recordar reconocimiento o beneficio del programa de referidos.'
                )
            )
            # Crear actividad para el agente
            lead.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=f'🎁 Reconocimiento a referidor: {referrer.name}',
                note=(
                    f'La venta de "{lead.name}" fue referida por <b>{referrer.name}</b>. '
                    f'Contactar para agradecer y entregar el beneficio del programa de referidos.'
                ),
                user_id=lead.user_id.id or self.env.uid,
            )


    @api.model_create_multi
    def create(self, vals_list):
        leads = super().create(vals_list)
        for lead in leads:
            self._notify_team_new_lead(lead)
        return leads

    def _notify_team_new_lead(self, lead):
        """Notificación interna al asesor asignado y al canal del equipo."""
        source_label = dict(self._fields['lead_source'].selection).get(lead.lead_source or 'other', 'Desconocido')
        msg = (
            f'🔔 <b>Nuevo lead recibido</b> vía <b>{source_label}</b>.<br/>'
            f'<b>Cliente:</b> {lead.partner_id.name or lead.contact_name or "Sin nombre"}<br/>'
            f'<b>Presupuesto:</b> ${lead.client_budget:,.0f}<br/>'
            f'<b>Ciudad preferida:</b> {lead.preferred_city or "No especificada"}'
        )
        lead.message_post(body=msg, message_type='comment', subtype_xmlid='mail.mt_note')
        # Crear actividad de seguimiento inicial para el asesor
        if lead.user_id:
            lead.activity_schedule(
                'mail.mail_activity_data_todo',
                summary='Primer contacto con nuevo lead',
                note=f'Lead recibido vía {source_label}. Realizar primer contacto en las próximas 2 horas.',
                user_id=lead.user_id.id,
            )


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    property_id = fields.Many2one('estate.property', string='Inmueble relacionado')
