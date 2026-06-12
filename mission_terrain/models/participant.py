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

    per_diem = fields.Float(string="Per diem / jour")

    perdiem_days = fields.Float(
        string="Nombre de jours per diem",
        compute="_compute_perdiem",
        store=True
    )

    total_per_diem = fields.Float(
        string="Total Per Diem",
        compute="_compute_perdiem",
        store=True
    )

    nb_days = fields.Integer(
        string="Nb jours",
        related="mission_id.nb_days",
        store=True,
        readonly=True
    )

    @api.depends(
        'per_diem',
        'mission_id.date_depart',
        'mission_id.date_retour',
        'mission_id.heure_depart'
    )
    def _compute_perdiem(self):

        for rec in self:

            mission = rec.mission_id

            if not mission.date_depart or not mission.date_retour:
                rec.perdiem_days = 0
                rec.total_per_diem = 0
                continue

            start = mission.date_depart
            end = mission.date_retour

            total_days = (end - start).days + 1

            perdiem_days = 0

            #  CAS 1 SEUL JOUR
            if total_days == 1:
                if mission.heure_depart and mission.heure_depart < 12:
                    perdiem_days = 1
                else:
                    perdiem_days = 0.5

            else:
                #  JOUR DE DEPART
                if mission.heure_depart and mission.heure_depart < 12:
                    perdiem_days += 1
                else:
                    perdiem_days += 0.5

                #  JOURS INTERMEDIAIRES
                if total_days > 2:
                    perdiem_days += (total_days - 2)

                #  JOUR DE RETOUR
                perdiem_days += 0.5

            rec.perdiem_days = perdiem_days
            rec.total_per_diem = perdiem_days * rec.per_diem

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



