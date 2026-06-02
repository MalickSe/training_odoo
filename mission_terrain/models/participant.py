from odoo import models, fields, api
from odoo.exceptions import ValidationError

class MissionParticipant(models.Model):
    _name = 'mission.participant'
    _description = 'Participant Mission'

    #  RELATION

    mission_id = fields.Many2one(
        'mission.terrain',
        string="Mission",
        ondelete='cascade',
        required=True
    )

    user_id = fields.Many2one(
        'res.users',
        string="Utilisateur",
        required=True
    )

    partner_id = fields.Many2one(
        'res.partner',
        string="Participant",
        related='user_id.partner_id',
        store=True
    )

    #  TYPE PARTICIPANT

    role = fields.Selection([
        ('staff', 'Staff'),
        ('consultant', 'Consultant'),
        ('driver', 'Chauffeur'),
    ], string="Rôle", default='staff')

    is_driver = fields.Boolean(string="Conducteur")

    #  FINANCE SIMPLE

    per_diem = fields.Float(string="Per diem")

    #  CONTRAINTE

    @api.constrains('user_id')
    def _check_unique_user(self):
        for rec in self:
            existing = self.search([
                ('mission_id', '=', rec.mission_id.id),
                ('user_id', '=', rec.user_id.id),
                ('id', '!=', rec.id)
            ])
            if existing:
                raise ValidationError("Ce participant est déjà dans la mission.")



