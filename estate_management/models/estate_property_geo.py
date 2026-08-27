# -*- coding: utf-8 -*-
"""Geocodificacion y mapa de estate.property: Nominatim, coordenadas,
iframe/URL de mapa y acciones relacionadas. Extraido de estate_property.py."""
import json
import logging
import requests

from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class EstatePropertyGeo(models.Model):
    _inherit = 'estate.property'

    @api.onchange('city')
    def _onchange_city_zip(self):
        if self.city:
            code = self._EC_POSTAL_CODES.get(self.city.lower().strip(), '')
            if code:
                self.zip_code = code
            # Auto-set Ecuador/Azuay when city is known
            if not self.country_id:
                ec = self.env['res.country'].search([('code', '=', 'EC')], limit=1)
                if ec:
                    self.country_id = ec
            if not self.state_id and self.city.lower().strip() == 'cuenca':
                azuay = self.env['res.country.state'].search(
                    [('name', 'ilike', 'Azuay'), ('country_id.code', '=', 'EC')], limit=1)
                if azuay:
                    self.state_id = azuay
            self.latitude = 0.0
            self.longitude = 0.0

    @api.onchange('state_id')
    def _onchange_state_set_country(self):
        """When province is selected, auto-set country to Ecuador."""
        if self.state_id and self.state_id.country_id:
            self.country_id = self.state_id.country_id

    @api.model
    def _fix_country_defaults(self):
        """Fix existing properties with wrong country/state. Called on module update."""
        ec = self.env['res.country'].search([('code', '=', 'EC')], limit=1)
        if not ec:
            return
        azuay = self.env['res.country.state'].search(
            [('name', 'ilike', 'Azuay'), ('country_id', '=', ec.id)], limit=1)
        # Fix country for all properties (this is an Ecuador-only system)
        bad_country = self.search([('country_id', '!=', ec.id)])
        if bad_country:
            bad_country.with_context(no_wp_sync=True, no_geocode=True).write(
                {'country_id': ec.id})
        # Set Azuay for properties in Cuenca with no state
        if azuay:
            cuenca_props = self.search([
                ('state_id', '=', False),
                ('city', 'ilike', 'Cuenca'),
            ])
            if cuenca_props:
                cuenca_props.with_context(no_wp_sync=True, no_geocode=True).write(
                    {'state_id': azuay.id})

    @api.model
    def _fix_ecuador_coordinates(self):
        """Corrige coordenadas con signo positivo erróneo para propiedades en Ecuador.
        Ecuador siempre tiene longitud negativa (hemisferio oeste) y Cuenca latitud negativa.
        Se ejecuta en cada actualización del módulo para reparar datos existentes.
        """
        # Propiedades con longitud positiva → definitivamente mal signo (Ecuador es siempre negativo en lon)
        wrong = self.search([('longitude', '>', 0)])
        fixed = 0
        for prop in wrong:
            new_lat = -abs(prop.latitude) if prop.latitude else 0.0
            new_lon = -abs(prop.longitude) if prop.longitude else 0.0
            super(EstateProperty, prop).write({'latitude': new_lat, 'longitude': new_lon})
            fixed += 1
        if fixed:
            _logger.info("_fix_ecuador_coordinates: corregidas %d propiedades con coordenadas incorrectas.", fixed)

    @api.onchange('street')
    def _onchange_street_keywords(self):
        if self.street and not self.sector_keywords:
            self.sector_keywords = self.street

    @api.depends('latitude', 'longitude')
    def _compute_map_iframe(self):
        for rec in self:
            if rec.latitude and rec.longitude:
                lat = rec.latitude
                lng = rec.longitude
                # Use OpenStreetMap embed format
                url = f"https://www.openstreetmap.org/export/embed.html?bbox={lng-0.005}%2C{lat-0.005}%2C{lng+0.005}%2C{lat+0.005}&amp;layer=mapnik&amp;marker={lat}%2C{lng}"
                rec.map_iframe = (
                    f'<div style="position:relative; width:100%; padding-bottom:35%; border-radius:8px; border:1px solid #ddd; overflow:hidden;">'
                    f'<iframe src="{url}" style="position:absolute; top:0; left:0; width:100%; height:100%; border:none;"></iframe>'
                    f'</div>'
                )
            else:
                rec.map_iframe = '<div style="padding-bottom:25%; background:#f8f9fa; border:1px dashed #ccc; border-radius:8px; display:flex; align-items:center; justify-content:center; color:#6c757d; gap:6px"><i class="fa fa-map-marker"></i><small>Haz clic en <b>Ubicar en Mapa</b></small></div>'

    @api.depends('street', 'city', 'state_id', 'country_id', 'latitude', 'longitude')
    def _compute_map_url(self):
        for rec in self:
            if rec.latitude and rec.longitude:
                rec.map_url = f"https://www.google.com/maps/search/?api=1&query={rec.latitude},{rec.longitude}"
            else:
                parts = [p for p in [rec.street, rec.city, rec.state_id.name, rec.country_id.name] if p]
                address = ', '.join(parts).replace(' ', '+')
                if address:
                    rec.map_url = f"https://www.google.com/maps/search/?api=1&query={address}"
                else:
                    rec.map_url = False

    def action_open_map(self):
        self.ensure_one()
        if self.map_url:
            return {
                'type': 'ir.actions.act_url',
                'url': self.map_url,
                'target': 'new',
            }

    def _nominatim_search(self, query, countrycodes='ec'):
        """Shared Nominatim search. Returns (lat, lon, display_name) or None on any failure."""
        try:
            resp = requests.get(
                'https://nominatim.openstreetmap.org/search',
                params={'q': query, 'format': 'json', 'limit': 1, 'countrycodes': countrycodes},
                headers={'User-Agent': 'OdooEstateApp/1.0 (tesis@inmobiliaria.ec)'},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            if not data:
                return None
            lat = float(data[0]['lat'])
            lon = float(data[0]['lon'])
            return lat, lon, data[0].get('display_name', query)
        except requests.exceptions.ConnectionError:
            _logger.warning("Geocoding: no se pudo conectar a Nominatim (sin red o DNS). query=%s", query)
            return None
        except requests.exceptions.Timeout:
            _logger.warning("Geocoding: timeout al contactar Nominatim. query=%s", query)
            return None
        except Exception as e:
            _logger.warning("Geocoding: error inesperado. query=%s error=%s", query, e)
            return None

    def _auto_geocode_silent(self):
        """Auto-geocode without recursion — writes coords via super() to avoid re-triggering write()."""
        try:
            parts = [p for p in [self.street, self.city,
                                  self.state_id.name if self.state_id else None,
                                  'Ecuador'] if p]
            if len(parts) < 2:
                return
            result = self._nominatim_search(', '.join(parts))
            if not result:
                result = self._nominatim_search(', '.join(parts), countrycodes='')
            if result:
                lat, lon, _ = result
                super().write({'latitude': lat, 'longitude': lon})
        except Exception as e:
            _logger.warning("_auto_geocode_silent failed: %s", e)

    def geocode_if_missing(self):
        """Called from JS on form load. Geocodes silently only when no coords exist yet.
        Returns True if coords were set, False if already existed or failed."""
        self.ensure_one()
        if self.latitude or self.longitude:
            return False
        self._auto_geocode_silent()
        return bool(self.latitude or self.longitude)

    def action_geocode_address(self):
        """Geocode the property address using Nominatim (OpenStreetMap) — free, no API key."""
        self.ensure_one()
        parts = [p for p in [self.street, self.city,
                             self.state_id.name if self.state_id else None,
                             'Ecuador'] if p]
        if not parts:
            raise UserError('Ingresa al menos la dirección y la ciudad para ubicar en el mapa.')
        query = ', '.join(parts)
        try:
            result = self._nominatim_search(query, countrycodes='ec')
            if not result:
                result = self._nominatim_search(query, countrycodes='')
            if result:
                lat, lon, display_name = result
                self.write({'latitude': lat, 'longitude': lon})
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Ubicación encontrada',
                        'message': f'Coordenadas: {lat:.5f}, {lon:.5f}',
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                # Retry at city level
                result2 = self._nominatim_search(f"{self.city}, Ecuador", countrycodes='ec')
                if result2:
                    lat, lon, _ = result2
                    self.write({'latitude': lat, 'longitude': lon})
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': 'Ubicación aproximada (ciudad)',
                            'message': f'No se encontró la calle exacta. Se usaron las coordenadas de {self.city}.',
                            'type': 'warning',
                            'sticky': False,
                        }
                    }
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Dirección no encontrada',
                        'message': f'No se pudo geocodificar: "{query}". Intenta con la dirección más específica.',
                        'type': 'warning',
                        'sticky': False,
                    }
                }
        except Exception as e:
            _logger.error("Geocoding error: %s", e)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error de geocodificación',
                    'message': str(e),
                    'type': 'danger',
                    'sticky': False,
                }
            }
