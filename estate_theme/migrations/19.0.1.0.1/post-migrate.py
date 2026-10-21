# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api

from odoo.addons.estate_theme.hooks import set_spanish_defaults


def migrate(cr, version):
    set_spanish_defaults(api.Environment(cr, SUPERUSER_ID, {}))
