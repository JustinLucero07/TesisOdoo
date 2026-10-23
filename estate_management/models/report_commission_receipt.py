# -*- coding: utf-8 -*-
from odoo import api, models


class ReportCommissionReceipt(models.AbstractModel):
    """Un comprobante por asesor: si se eligen varias comisiones del mismo
    asesor (por ejemplo recepción, visita y cierre) sale una sola hoja con el
    desglose por rol, lista para firmar."""
    _name = 'report.estate_management.report_commission_receipt'
    _description = 'Comprobante de pago al asesor'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['estate.commission'].browse(docids)
        groups = {}
        for com in docs:
            key = com.payment_id.id or (com.user_id.id, com.property_id.id, com.payment_date)
            groups.setdefault(key, docs.browse())
            groups[key] |= com
        return {
            'doc_ids': docids,
            'doc_model': 'estate.commission',
            'docs': docs,
            'groups': list(groups.values()),
        }
