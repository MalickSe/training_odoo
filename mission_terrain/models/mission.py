from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
from odoo.exceptions import UserError

class MissionTerrain(models.Model):
    _name = 'mission.terrain'
    _description = 'Mission Terrain'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    #  INFOS GÉNÉRALES

    name = fields.Char(string="Référence", required=True, copy=False, default="Nouveau")

    @api.model
    def create(self, vals):
        if vals.get('name', 'Nouveau') == 'Nouveau':
            vals['name'] = self.env['ir.sequence'].next_by_code('mission.terrain') or '/'
        return super().create(vals)

    objet = fields.Char(string="Objet", required=True)
    destination = fields.Char(string="Destination", required=True)
    lieu_nuitee = fields.Char(string="Lieu de nuitée")

    requester_id = fields.Many2one(
        'res.users',
        string="Demandeur",
        default=lambda self: self.env.user,
        tracking=True
    )

    mission_type = fields.Selection([
        ('vehicule', 'Véhicule'),
        ('bus', 'Bus'),
        ('avion', 'Avion')
    ], string="Type de mission", default='vehicule', required=True)

    project_id = fields.Many2one(
        'project.project',
        string="Projet"
    )

    #  DATES

    date_depart = fields.Date("Date départ")
    heure_depart = fields.Float("Heure départ")

    date_retour = fields.Date("Date retour")
    heure_retour = fields.Float("Heure retour")

    #  PARTICIPANTS

    participant_ids = fields.One2many(
        'mission.participant',
        'mission_id',
        string="Participants"
    )

    participant_count = fields.Integer(
        string="Nombre de participants",
        compute="_compute_participant_count"
    )

    def _compute_participant_count(self):
        for rec in self:
            rec.participant_count = len(rec.participant_ids)

    #  LOGISTIQUE

    vehicle_id = fields.Many2one('fleet.vehicle', string="Véhicule")
    driver_id = fields.Many2one('res.partner', string="Chauffeur")

    #  FINANCE

    ligne_budgetaire = fields.Char("Ligne budgétaire")
    requested_amount = fields.Float("Montant demandé")
    approved_amount = fields.Float("Montant approuvé")

    #  DOCUMENT

    tdr_file = fields.Binary("TDR")
    tdr_filename = fields.Char("Nom du fichier")

   # CONTRAINTE 72H

    @api.constrains('date_depart', 'heure_depart')
    def _check_delay_before_departure(self):
        for rec in self:
            if rec.date_depart:
                now = datetime.now()

                departure_datetime = datetime.combine(
                    rec.date_depart,
                    datetime.min.time()
                )

                if rec.heure_depart:
                    hours = int(rec.heure_depart)
                    minutes = int((rec.heure_depart - hours) * 60)
                    departure_datetime = departure_datetime.replace(
                        hour=hours,
                        minute=minutes
                    )

                if (departure_datetime - now) <= timedelta(hours=72):
                    raise ValidationError(
                        "La demande doit être faite au moins 72h avant le départ."
                    )

    # METHODES

    def action_submit(self):
        for rec in self:
            if not rec.participant_ids:
                raise UserError("Ajoutez au moins un participant.")

            rec.state = 'submitted'

    def action_validate_security(self):
        for rec in self:
            rec.state = 'security'

    def action_assign_fleet(self):
        for rec in self:
            if rec.mission_type == 'vehicule' and not rec.vehicle_id:
                raise UserError("Veuillez assigner un véhicule.")

            rec.state = 'fleet'

    def action_validate_finance(self):
        for rec in self:
            if not rec.ligne_budgetaire:
                raise UserError("Ligne budgétaire obligatoire.")

            rec.state = 'finance'

    def action_approve(self):
        for rec in self:
            rec.state = 'done'

    def action_reject(self):
        for rec in self:
            rec.state = 'rejected'

    def action_view_participants(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Participants',
            'res_model': 'mission.participant',
            'view_mode': 'tree,form',
            'domain': [('mission_id', '=', self.id)],
            'context': {
                'default_mission_id': self.id
            }
        }

    #  WORKFLOW

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('submitted', 'Soumise'),
        ('security', 'Validation Sécurité'),
        ('fleet', 'Traitement Flotte'),
        ('finance', 'Validation Finance'),
        ('approval', 'Approbation'),
        ('done', 'Terminée'),
        ('rejected', 'Rejetée')
    ], default='draft', tracking=True)