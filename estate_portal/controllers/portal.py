# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.http import request

class EstateCustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id
        
        # Count properties owned by the current logged-in user
        if 'property_count' in counters:
            property_count = request.env['estate.property'].sudo().search_count([
                ('owner_id', '=', partner.id)
            ])
            values['property_count'] = property_count
            
        if 'contract_count' in counters:
            contract_count = request.env['estate.contract'].sudo().search_count([
                ('partner_id', '=', partner.id)
            ])
            values['contract_count'] = contract_count
            
        return values

    # --- PROPERTIES ---
    @http.route(['/my/properties', '/my/properties/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_properties(self, page=1, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        PropertyArea = request.env['estate.property'].sudo()

        domain = [('owner_id', '=', partner.id)]
        
        # count for pager
        property_count = PropertyArea.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/properties",
            url_args={'sortby': sortby},
            total=property_count,
            page=page,
            step=self._items_per_page
        )
        
        # content according to pager and archive selected
        properties = PropertyArea.search(domain, limit=self._items_per_page, offset=pager['offset'])
        
        values.update({
            'properties': properties,
            'page_name': 'property',
            'pager': pager,
            'default_url': '/my/properties',
        })
        return request.render("estate_portal.portal_my_properties", values)

    @http.route(['/my/property/<int:property_id>'], type='http', auth="user", website=True)
    def portal_my_property_detail(self, property_id, **kw):
        property_obj = request.env['estate.property'].sudo().browse(property_id)
        
        if property_obj.owner_id != request.env.user.partner_id:
            return request.redirect('/my')
            
        # Get visits (calendar events) related to this property
        visits = request.env['calendar.event'].sudo().search([
            ('property_id', '=', property_id),
            ('visit_state', '!=', False)
        ], order='start desc')

        # Market benchmark for this property type + city
        market_domain = [
            ('state', '=', 'sold'),
            ('property_type_id', '=', property_obj.property_type_id.id),
            ('days_on_market', '>', 0),
        ]
        if property_obj.city:
            market_domain.append(('city', 'ilike', property_obj.city))
        market_comps = request.env['estate.property'].sudo().search(market_domain, limit=30)
        market_avg_days = 0
        market_avg_price = 0.0
        if market_comps:
            market_avg_days = int(sum(market_comps.mapped('days_on_market')) / len(market_comps))
            market_avg_price = sum(market_comps.mapped('price')) / len(market_comps)

        values = self._prepare_portal_layout_values()
        values.update({
            'property': property_obj,
            'visits': visits,
            'page_name': 'property_detail',
            'market_avg_days': market_avg_days,
            'market_avg_price': market_avg_price,
            'market_sample_size': len(market_comps),
        })
        return request.render("estate_portal.portal_property_page", values)

    # --- CONTRACTS ---
    @http.route(['/my/contracts', '/my/contracts/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_contracts(self, page=1, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        Contract = request.env['estate.contract'].sudo()

        domain = [('partner_id', '=', partner.id)]
        contract_count = Contract.search_count(domain)
        pager = portal_pager(
            url="/my/contracts",
            total=contract_count,
            page=page,
            step=self._items_per_page
        )
        contracts = Contract.search(domain, limit=self._items_per_page, offset=pager['offset'])
        
        values.update({
            'contracts': contracts,
            'page_name': 'contract',
            'pager': pager,
            'default_url': '/my/contracts',
        })
        return request.render("estate_portal.portal_my_contracts", values)

    @http.route(['/my/contract/<int:contract_id>'], type='http', auth="user", website=True)
    def portal_my_contract_detail(self, contract_id, **kw):
        contract = request.env['estate.contract'].sudo().browse(contract_id)
        from odoo import fields
        if contract.partner_id != request.env.user.partner_id:
            return request.redirect('/my')

        values = self._prepare_portal_layout_values()
        values.update({
            'contract': contract,
            'page_name': 'contract_detail',
            'success': kw.get('success'),
        })
        return request.render("estate_portal.portal_contract_page", values)

    @http.route(['/my/compare'], type='http', auth="user", website=True)
    def portal_compare_properties(self, ids=None, **kw):
        """Compara hasta 3 propiedades del propietario lado a lado."""
        partner = request.env.user.partner_id
        property_ids = []
        if ids:
            try:
                property_ids = [int(x) for x in ids.split(',') if x.strip()][:3]
            except (ValueError, AttributeError):
                property_ids = []

        properties = request.env['estate.property'].sudo().browse(property_ids).filtered(
            lambda p: p.owner_id == partner
        )

        avg_data = {}
        for prop in properties:
            domain = [
                ('state', '=', 'sold'),
                ('property_type_id', '=', prop.property_type_id.id),
                ('days_on_market', '>', 0),
            ]
            comparables = request.env['estate.property'].sudo().search(domain, limit=20)
            if comparables:
                avg_data[prop.id] = {
                    'avg_days': int(sum(comparables.mapped('days_on_market')) / len(comparables)),
                    'avg_price': sum(comparables.mapped('price')) / len(comparables),
                }
            else:
                avg_data[prop.id] = {'avg_days': 0, 'avg_price': 0.0}

        all_properties = request.env['estate.property'].sudo().search([
            ('owner_id', '=', partner.id)
        ])

        values = self._prepare_portal_layout_values()
        values.update({
            'properties': properties,
            'all_properties': all_properties,
            'avg_data': avg_data,
            'selected_ids': ','.join(str(p.id) for p in properties),
            'page_name': 'compare',
        })
        return request.render("estate_portal.portal_compare_properties", values)

    @http.route(['/my/contract/<int:contract_id>/sign'], type='http', auth="user", methods=['POST'], website=True, csrf=False)
    def portal_contract_sign(self, contract_id, signature=None, **kw):
        contract = request.env['estate.contract'].sudo().browse(contract_id)
        from odoo import fields
        if contract.partner_id != request.env.user.partner_id:
            return request.redirect('/my')

        if signature:
            # signature comes as data:image/png;base64,...
            if ',' in signature:
                signature = signature.split(',')[1]
            
            contract.sudo().write({
                'customer_signature': signature,
                'signature_date': fields.Datetime.now(),
            })
            # Log activity
            contract.message_post(body=_("Contrato firmado digitalmente por el cliente desde el portal."))

        return request.redirect(f'/my/contract/{contract_id}?success=1')

    # --- PROGRAMA DE REFERIDOS ---

    @http.route(['/my/referral'], type='http', auth='user', website=True)
    def portal_referral(self, **kw):
        """Página del programa de referidos."""
        partner = request.env.user.partner_id
        # Leads que este partner refirió
        referred_leads = request.env['crm.lead'].sudo().search([
            ('referral_partner_id', '=', partner.id),
        ], order='create_date desc')

        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': 'referral',
            'referred_leads': referred_leads,
            'success': kw.get('success'),
            'error': kw.get('error'),
        })
        return request.render('estate_portal.portal_referral_page', values)

    @http.route(['/my/referral/submit'], type='http', auth='user',
                methods=['POST'], website=True, csrf=True)
    def portal_referral_submit(self, **kw):
        """Procesa el formulario de referido."""
        partner = request.env.user.partner_id
        ref_name = (kw.get('ref_name') or '').strip()
        ref_phone = (kw.get('ref_phone') or '').strip()
        ref_email = (kw.get('ref_email') or '').strip()
        ref_notes = (kw.get('ref_notes') or '').strip()
        prop_type = (kw.get('prop_type') or '').strip()
        city = (kw.get('city') or '').strip()

        if not ref_name or not ref_phone:
            return request.redirect('/my/referral?error=Nombre+y+teléfono+son+obligatorios')

        # Buscar tipo de propiedad
        ptype = None
        if prop_type:
            ptype = request.env['estate.property.type'].sudo().search(
                [('name', 'ilike', prop_type)], limit=1)

        # Crear lead referido
        # Asignar asesor: el salesperson del referidor, o el de su contrato más reciente
        user_id = False
        if partner.user_id:
            user_id = partner.user_id.id
        else:
            last_contract = request.env['estate.contract'].sudo().search([
                ('partner_id', '=', partner.id),
            ], limit=1, order='id desc')
            if last_contract and last_contract.user_id:
                user_id = last_contract.user_id.id

        vals = {
            'name': f"Referido por {partner.name}: {ref_name}",
            'contact_name': ref_name,
            'mobile': ref_phone,
            'email_from': ref_email or False,
            'type': 'lead',
            'lead_source': 'referral',
            'referral_partner_id': partner.id,
            'user_id': user_id,
            'description': ref_notes or f"Lead referido por {partner.name} desde el portal.",
        }
        if city:
            vals['preferred_city'] = city
        if ptype:
            vals['preferred_property_type_id'] = ptype.id

        lead = request.env['crm.lead'].sudo().create(vals)
        lead.message_post(
            body=(
                f'🤝 <b>Referido desde el Portal</b><br/>'
                f'Referidor: <b>{partner.name}</b> ({partner.email or partner.mobile or ""})<br/>'
                f'Prospecto: {ref_name} — {ref_phone}'
            )
        )
        return request.redirect('/my/referral?success=1')
