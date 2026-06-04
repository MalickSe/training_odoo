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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') == 'Nouveau':
                vals['name'] = self.env['ir.sequence'].next_by_code('mission.terrain') or '/'

        return super().create(vals_list)

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

                if (departure_datetime - now) <= timedelta(hours=48):
                    raise ValidationError(
                        "La demande doit être faite au moins 72h avant le départ."
                    )

    # CONTRAINTE LIMITATION PARTICIPANT

    @api.constrains('participant_ids', 'mission_type')
    def _check_participant_limit(self):
        for rec in self:
            if rec.mission_type == 'vehicule':

                participants = rec.participant_ids.filtered(lambda p: not p.is_driver)
                drivers = rec.participant_ids.filtered(lambda p: p.is_driver)

                if len(drivers) > 1:
                    raise ValidationError("Une mission ne peut avoir qu'un seul chauffeur.")

                if len(participants) > 4:
                    raise ValidationError("Maximum 4 participants autorisés pour une mission avec véhicule.")

                if len(rec.participant_ids) > 5:
                    raise ValidationError("Maximum 5 personnes (chauffeur inclus) pour une mission avec véhicule.")

    # METHODES

    def action_submit(self):
        for rec in self:
            if not rec.participant_ids:
                raise UserError("Ajoutez au moins un participant.")

            rec.state = 'submitted'

    def action_validate_security(self):
        if not self.env.user.has_group('mission_terrain.group_mission_security'):
            raise UserError("Seul le Security Advisor peut valider cette étape.")

        for rec in self:
            rec.state = 'security'

    def action_assign_fleet(self):
        if not self.env.user.has_group('mission_terrain.group_mission_fleet'):
            raise UserError("Accès réservé au gestionnaire de flotte.")

        for rec in self:
            rec.state = 'fleet'

    def action_validate_finance(self):
        if not self.env.user.has_group('mission_terrain.group_mission_finance'):
            raise UserError("Accès réservé au service Finance.")

        for rec in self:
            rec.state = 'finance'

    def action_approve(self):
        if not self.env.user.has_group('mission_terrain.group_mission_manager'):
            raise UserError("Seul un approbateur peut valider cette mission.")

        for rec in self:
            rec.state = 'approval'

    def action_done(self):
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
            'view_mode': 'list,form',
            'views': [
                (self.env.ref('mission_terrain.view_participant_list').id, 'list'),
                (self.env.ref('mission_terrain.view_participant_form').id, 'form')
            ],
            'domain': [('mission_id', '=', self.id)],
            'context': {'default_mission_id': self.id},
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