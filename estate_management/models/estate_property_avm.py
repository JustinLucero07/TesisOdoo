# -*- coding: utf-8 -*-
"""Modelo AVM (Automated Valuation Model) de estate.property.
Valuacion estimada, confianza, dias previstos y score. Extraido de
estate_property.py para organizar el modulo por responsabilidad."""
import logging

from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class EstatePropertyAVM(models.Model):
    _inherit = 'estate.property'

    @api.depends('avm_comparable_count')
    def _compute_avm_confidence(self):
        for rec in self:
            n = rec.avm_comparable_count or 0
            if n >= 10:
                rec.avm_confidence = 'high'
            elif n >= 3:
                rec.avm_confidence = 'medium'
            elif n >= 1:
                rec.avm_confidence = 'low'
            else:
                rec.avm_confidence = 'none'

    def action_recalculate_avm(self):
        """Mejora 6: Recalcula AVM con comparables reales y actualiza confianza."""
        from datetime import timedelta
        for prop in self:
            if not prop.property_type_id or not prop.city:
                continue
            six_months_ago = fields.Date.today() - timedelta(days=180)
            min_area = (prop.area or 0) * 0.85
            max_area = (prop.area or 0) * 1.15
            domain = [
                ('state', '=', 'sold'),
                ('property_type_id', '=', prop.property_type_id.id),
                ('city', 'ilike', prop.city),
                ('price', '>', 0),
                ('date_sold', '>=', six_months_ago),
            ]
            if prop.area and prop.area > 0:
                domain += [('area', '>=', min_area), ('area', '<=', max_area)]
            comparables = self.search(domain)
            if prop.id and isinstance(prop.id, int):
                comparables = comparables.filtered(lambda c: c.id != prop.id)
            if comparables:
                prices_per_m2 = [c.price / c.area for c in comparables if c.area and c.area > 0]
                if prices_per_m2:
                    avg_price_m2 = sum(prices_per_m2) / len(prices_per_m2)
                    estimated = avg_price_m2 * (prop.area or 1)
                    # Trend: compare first vs second half
                    half = len(comparables) // 2
                    if half > 0:
                        sorted_comps = comparables.sorted('date_sold')
                        first_half = sorted_comps[:half]
                        second_half = sorted_comps[half:]
                        avg_first = sum(c.price for c in first_half) / len(first_half)
                        avg_second = sum(c.price for c in second_half) / len(second_half)
                        if avg_second > avg_first * 1.03:
                            trend = 'Subiendo (+{:.1f}%)'.format(((avg_second/avg_first)-1)*100)
                        elif avg_second < avg_first * 0.97:
                            trend = 'Bajando ({:.1f}%)'.format(((avg_second/avg_first)-1)*100)
                        else:
                            trend = 'Estable'
                    else:
                        trend = 'Estable'
                    prop.write({
                        'avm_estimated_price': int(estimated * 100) / 100.0,
                        'avm_comparable_count': len(comparables),
                        'avm_price_trend': trend,
                        'avm_last_calculated': fields.Datetime.now(),
                    })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'AVM Recalculado',
                'message': 'El valor de mercado fue actualizado con comparables reales.',
                'type': 'success', 'sticky': False,
            }
        }

    @api.depends('price', 'avm_estimated_price')
    def _compute_avm_status(self):
        for rec in self:
            if not rec.avm_estimated_price or rec.avm_estimated_price == 0:
                rec.avm_status = 'insufficient'
                continue
                
            variance = (rec.price - rec.avm_estimated_price) / rec.avm_estimated_price
            if variance > 0.10: # > 10% more
                rec.avm_status = 'high'
            elif variance < -0.10: # < -10% less
                rec.avm_status = 'low'
            else:
                rec.avm_status = 'fair'

    @api.depends('property_type_id', 'city', 'state')
    def _compute_predicted_days(self):
        for rec in self:
            if not rec.property_type_id:
                rec.predicted_days_on_market = 0
                continue
            base_domain = [
                ('state', '=', 'sold'),
                ('property_type_id', '=', rec.property_type_id.id),
                ('days_on_market', '>', 0),
            ]
            if rec.id and isinstance(rec.id, int):
                base_domain.append(('id', '!=', rec.id))
            domain = base_domain + [('city', 'ilike', rec.city)] if rec.city else base_domain
            comparables = self.env['estate.property'].search(domain, limit=15)
            if not comparables and rec.city:
                comparables = self.env['estate.property'].search(domain, limit=15)
            if comparables:
                days_list = comparables.mapped('days_on_market')
                rec.predicted_days_on_market = int(sum(days_list) / len(days_list))
            else:
                rec.predicted_days_on_market = 0

    @api.depends('image_main', 'image_ids', 'description', 'wp_published',
                 'meeting_count', 'days_on_market', 'avm_status')
    def _compute_property_score(self):
        import re
        for rec in self:
            score = 0
            if rec.avm_status == 'fair':
                score += 33
            elif rec.avm_status == 'low':
                score += 43
            elif rec.avm_status == 'high':
               if rec.document_ids:
                score += min(len(rec.document_ids) * 5, 15)
            # Bonuses
            if rec.tour_360_active:
                score += 10
            if rec.capture_sheet:
                score += 5
            
            score = min(score, 100)
            text = re.sub(r'<[^>]+>', '', rec.description or '')
            if len(text) > 200:
                score += 10
            if rec.wp_published:
                score += 10
            score += min(rec.meeting_count * 5, 15)
            if rec.days_on_market > 30:
                weeks_over = (rec.days_on_market - 30) // 7
                score -= min(weeks_over, 20)
            final = max(0, min(100, score))
            rec.property_score = final
            if final >= 80:
                rec.property_score_label = 'Excelente'
            elif final >= 60:
                rec.property_score_label = 'Bueno'
            elif final >= 40:
                rec.property_score_label = 'Regular'
            else:
                rec.property_score_label = 'Incompleto'

    def action_calculate_avm(self):
        """Calcula el valor óptimo basado en propiedades similares VENDIDAS"""
        self.ensure_one()
        # Buscar propiedades vendidas del mismo tipo. Si tiene ciudad, filtrar por ciudad también.
        domain = [
            ('state', '=', 'sold'),
            ('id', '!=', self.id),
            ('property_type_id', '=', self.property_type_id.id)
        ]
        if self.city:
            domain.append(('city', 'ilike', self.city))
            
        comparables = self.env['estate.property'].search(domain, order='date_sold desc', limit=20)
        
        if not comparables:
            # Fallback: Solo buscar por tipo inmobiliario si no hay en la ciudad
            domain.pop()
            comparables = self.env['estate.property'].search(domain, order='date_sold desc', limit=20)
            if not comparables:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'AVM: Datos Insuficientes',
                        'message': 'No hay suficientes propiedades vendidas similares para calcular el AVM.',
                        'type': 'warning',
                        'sticky': False,
                    }
                }
            
        import math
        from datetime import date as _date
        today = _date.today()
        weighted_price = 0.0
        weighted_area = 0.0
        total_weight = 0.0
        direct_weighted_price = 0.0

        for comp in comparables:
            age_days = (today - comp.date_sold).days if comp.date_sold else 365
            age_weight = math.exp(-age_days / 365.0)
            year_diff = abs((self.year_built or 2000) - (comp.year_built or 2000))
            year_factor = max(1.0 - year_diff * 0.005, 0.70)
            weight = age_weight * year_factor
            direct_weighted_price += comp.price * weight
            if comp.area and comp.area > 0:
                weighted_price += comp.price * weight
                weighted_area += comp.area * weight
            total_weight += weight

        if total_weight == 0:
            total_weight = len(comparables)
            direct_weighted_price = sum(c.price for c in comparables)

        if weighted_area > 0 and self.area and self.area > 0:
            avg_price_per_sqm = weighted_price / weighted_area
            estimated_price = avg_price_per_sqm * self.area
        else:
            estimated_price = direct_weighted_price / total_weight
            
        self.write({
            'avm_estimated_price': estimated_price,
            'avm_last_calculated': fields.Datetime.now()
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'AVM Calculado Exitosamente',
                'message': f"Basado en {len(comparables)} ventas históricas (ponderadas por antigüedad y año de construcción) el valor estimado es ${estimated_price:,.2f}.",
                'type': 'success',
                'sticky': False,
            }
        }
