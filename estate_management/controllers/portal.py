from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager

class EstateCustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id
        if 'property_count' in counters:
            # Propiedades en las que está de Cliente
            property_count = request.env['estate.property'].sudo().search_count([
                ('client_id', '=', partner.id)
            ])
            values['property_count'] = property_count
        if 'contract_count' in counters:
            contract_count = request.env['estate.contract'].sudo().search_count([
                ('partner_id', '=', partner.id)
            ])
            values['contract_count'] = contract_count
        return values

    @http.route(['/my/properties', '/my/properties/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_properties(self, page=1, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        Property = request.env['estate.property'].sudo()

        domain = [('client_id', '=', partner.id)]
        
        searchbar_sortings = {
            'date': {'label': 'Fecha Añadida', 'order': 'date_added desc'},
            'name': {'label': 'Referencia', 'order': 'name'},
            'price': {'label': 'Precio', 'order': 'price desc'},
        }
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        property_count = Property.search_count(domain)
        pager = portal_pager(
            url="/my/properties",
            url_args={'sortby': sortby},
            total=property_count,
            page=page,
            step=self._items_per_page
        )
        
        properties = Property.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        
        values.update({
            'date': 'date_added',
            'properties': properties,
            'page_name': 'property',
            'pager': pager,
            'default_url': '/my/properties',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        return request.render("estate_management.portal_my_properties", values)

    @http.route(['/my/property/<int:property_id>'], type='http', auth="user", website=True)
    def portal_my_property_detail(self, property_id, **kw):
        prop = request.env['estate.property'].sudo().browse(property_id)
        if not prop.exists() or prop.client_id != request.env.user.partner_id:
            return request.redirect('/my')
            
        values = {
            'property': prop,
            'page_name': 'property_detail',
        }
        return request.render("estate_management.portal_property_page", values)

    @http.route(['/my/contracts', '/my/contracts/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_contracts(self, page=1, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        Contract = request.env['estate.contract'].sudo()

        domain = [('partner_id', '=', partner.id)]
        searchbar_sortings = {
            'date': {'label': 'Fecha Inicial', 'order': 'date_start desc'},
            'name': {'label': 'Referencia', 'order': 'name'},
        }
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        contract_count = Contract.search_count(domain)
        pager = portal_pager(
            url="/my/contracts",
            url_args={'sortby': sortby},
            total=contract_count,
            page=page,
            step=self._items_per_page
        )
        
        contracts = Contract.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        
        values.update({
            'date': 'date_start',
            'contracts': contracts,
            'page_name': 'contract',
            'pager': pager,
            'default_url': '/my/contracts',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        return request.render("estate_management.portal_my_contracts", values)

    @http.route(['/my/contract/<int:contract_id>'], type='http', auth="user", website=True)
    def portal_my_contract_detail(self, contract_id, **kw):
        contract = request.env['estate.contract'].sudo().browse(contract_id)
        if not contract.exists() or contract.partner_id != request.env.user.partner_id:
            return request.redirect('/my')
            
        values = {
            'contract': contract,
            'page_name': 'contract_detail',
        }
        return request.render("estate_management.portal_contract_page", values)
