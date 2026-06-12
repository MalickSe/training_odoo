from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    signature_image = fields.Binary(
        string="Signature",
        attachment=True
    )
