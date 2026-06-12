from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class MissionDeplacement(models.Model):
    _name = 'mission.deplacement'
    _description = 'Déplacement Journalier'
    _inherit = ['mail.thread', 'mail.activity.mixin']


    # INFOS GÉNÉRALES

    name = fields.Char(
        string="Référence",
        required=True,
        copy=False,
        readonly=True,
        default="Nouveau"
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') == 'Nouveau':
                vals['name'] = self.env['ir.sequence'].next_by_code('mission.deplacement') or '/'
        return super().create(vals_list)

    requester_id = fields.Many2one(
        'res.users',
        default=lambda self: self.env.user,
        string="Demandeur",
        tracking=True
    )

    date_deplacement = fields.Date(required=True)
    heure_depart = fields.Float("Heure départ")
    heure_retour = fields.Float("Heure retour")

    motif = fields.Char("Motif")

    participant_ids = fields.Many2many(
        'res.users',
        string="Participants"
    )

    # =====================
    # LOGISTIQUE
    # =====================

    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string="Véhicule",
        tracking=True
    )

    driver_id = fields.Many2one(
        'res.partner',
        string="Chauffeur"
    )

    # =====================
    # WORKFLOW
    # =====================

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('submitted', 'Soumis'),
        ('fleet', 'Assigné'),
        ('done', 'Terminé'),
        ('rejected', 'Rejeté')
    ], default='draft', tracking=True)

    # =====================
    # WORKFLOW ACTIONS
    # =====================

    def action_submit(self):
        for rec in self:
            if not rec.participant_ids:
                raise UserError("Ajoutez au moins un participant.")
            rec.state = 'submitted'

    def action_assign_fleet(self):
        for rec in self:
            if rec.state != 'submitted':
                raise UserError("Action non autorisée")

            # ✅ Auto suggestion si vide
            if not rec.vehicle_id:
                rec.vehicle_id = rec._get_available_vehicle()

            if not rec.vehicle_id:
                raise UserError("Aucun véhicule disponible")

            rec.state = 'fleet'

    def action_done(self):
        for rec in self:
            if rec.state != 'fleet':
                raise UserError("Action non autorisée")
            rec.state = 'done'

    def action_reject(self):
        for rec in self:
            rec.state = 'rejected'

    # =====================
    # SUGGESTION VÉHICULE
    # =====================

    def _get_available_vehicle(self):
        """Retourne un véhicule disponible"""

        Fleet = self.env['fleet.vehicle']
        all_vehicles = Fleet.search([])

        for vehicle in all_vehicles:

            conflicts = self.search([
                ('id', '!=', self.id),
                ('vehicle_id', '=', vehicle.id),
                ('date_deplacement', '=', self.date_deplacement),
                ('state', 'in', ['submitted', 'fleet'])
            ])

            available = True

            for other in conflicts:
                if (
                    self.heure_depart < other.heure_retour and
                    self.heure_retour > other.heure_depart
                ):
                    available = False
                    break

            if available:
                return vehicle

        return False

    # =====================
    # CONTRAINTES
    # =====================

    @api.constrains('heure_depart', 'heure_retour')
    def _check_hours(self):
        for rec in self:
            if rec.heure_depart and rec.heure_retour:
                if rec.heure_retour <= rec.heure_depart:
                    raise ValidationError("Heure retour doit être après heure départ")

    @api.constrains('vehicle_id', 'date_deplacement', 'heure_depart', 'heure_retour')
    def _check_vehicle_availability(self):

        for rec in self:

            if not rec.vehicle_id or not rec.date_deplacement:
                continue

            if not rec.heure_depart or not rec.heure_retour:
                continue

            conflicts = self.search([
                ('id', '!=', rec.id),
                ('vehicle_id', '=', rec.vehicle_id.id),
                ('date_deplacement', '=', rec.date_deplacement),
                ('state', 'in', ['submitted', 'fleet'])
            ])

            for other in conflicts:
                if (
                    rec.heure_depart < other.heure_retour and
                    rec.heure_retour > other.heure_depart
                ):

                    alternative = rec._get_available_vehicle()

                    if alternative:
                        raise ValidationError(
                            f"Véhicule indisponible.\n"
                            f"Suggestion : {alternative.name}"
                        )
                    else:
                        raise ValidationError(
                            "Aucun véhicule disponible sur ce créneau."
                        )