# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class EstatePropertyComparatorWizard(models.TransientModel):
    _name = 'estate.property.comparator.wizard'
    _description = 'Comparador de Propiedades'

    property_ids = fields.Many2many(
        'estate.property',
        string='Propiedades a Comparar',
        required=True,
        help='Selecciona entre 2 y 4 propiedades para comparar.',
    )

    @api.constrains('property_ids')
    def _check_property_count(self):
        for rec in self:
            count = len(rec.property_ids)
            if count < 2:
                raise UserError('Debes seleccionar al menos 2 propiedades para comparar.')
            if count > 4:
                raise UserError('Puedes comparar un máximo de 4 propiedades a la vez.')

    def action_print_comparison(self):
        """Genera el PDF de comparación de propiedades."""
        self.ensure_one()
        return self.env.ref(
            'estate_management.action_report_property_comparison'
        ).report_action(self)
