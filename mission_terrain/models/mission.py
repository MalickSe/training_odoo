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

    mission_count = fields.Integer(
        string="Nombre de missions",
        compute="_compute_mission_count",
        store=True
    )

    def _compute_mission_count(self):
        for rec in self:
            rec.mission_count = 1

    #  LOGISTIQUE

    vehicle_id = fields.Many2one('fleet.vehicle', string="Véhicule")
    driver_id = fields.Many2one('res.partner', string="Chauffeur")

    vehicle_usage_rate = fields.Float(
        string="Taux utilisation (%)",
        compute="_compute_vehicle_usage"
    )

    def _compute_vehicle_usage(self):

        all_missions = self.env['mission.terrain'].search([])
        total_missions = len(all_missions)

        for rec in self:

            if rec.vehicle_id and total_missions > 0:

                vehicle_missions = all_missions.filtered(
                    lambda m: m.vehicle_id == rec.vehicle_id
                )

                rec.vehicle_usage_rate = (len(vehicle_missions) / total_missions) * 100

            else:
                rec.vehicle_usage_rate = 0

    #  FINANCE

    ligne_budgetaire = fields.Char("Ligne budgétaire")

    requested_amount = fields.Float(
        string="Montant demandé",
        compute="_compute_requested_amount",
        store=True
    )

    @api.depends('participant_ids.total_per_diem')
    def _compute_requested_amount(self):
        for rec in self:
            total = 0.0
            for p in rec.participant_ids:
                total += p.total_per_diem
            rec.requested_amount = total

# CALCUL MONTANT APPROUVÉ

    approved_amount = fields.Float(
        string="Montant approuvé",
        compute="_compute_approved_amount",
        store=True
    )

    @api.depends(
        'requested_amount',
        'hebergement_total',
        'transport_amount'
    )
    def _compute_approved_amount(self):
        for rec in self:
            rec.approved_amount = (
                    rec.requested_amount
                    + rec.hebergement_total
                    + rec.transport_amount
            )

    # CALCUL NBRE DE JOURS
    nb_days = fields.Integer(
        string="Nombre de jours",
        compute="_compute_nb_days",
        store=True
    )

    @api.depends('date_depart', 'date_retour')
    def _compute_nb_days(self):
        for rec in self:
            if rec.date_depart and rec.date_retour:
                rec.nb_days = (rec.date_retour - rec.date_depart).days + 1
            else:
                rec.nb_days = 0

        # CHAMP HEBERGEMENT
    hebergement_journalier = fields.Float(
        string="Hébergement / jour"
    )

    hebergement_total = fields.Float(
        string="Hébergement total",
        compute="_compute_hebergement_total",
        store=True
    )

    @api.depends('hebergement_journalier', 'nb_days', 'participant_ids')
    def _compute_hebergement_total(self):
        for rec in self:
            nb_participants = len(rec.participant_ids)
            rec.hebergement_total = (
                    rec.hebergement_journalier
                    * rec.nb_days
                    * nb_participants
            )

        # CHAMP TRANSPORT
    transport_amount = fields.Float(
        string="Transport"
    )
    # CHAMP COMPUTE LOGISTIQUE

    kpi_total_projects = fields.Integer(compute="_compute_kpis_logistique")
    kpi_total_vehicule = fields.Integer(compute="_compute_kpis_logistique")
    kpi_total_chauffeurs = fields.Integer(compute="_compute_kpis_logistique")
    kpi_total_vehicles = fields.Integer(compute="_compute_kpis_logistique")

    def _compute_kpis_logistique(self):

        all_missions = self.env['mission.terrain'].search([])

        total_projects = len(all_missions.mapped('project_id'))
        total_vehicule = len(all_missions.filtered(lambda m: m.mission_type == 'vehicule'))
        total_chauffeurs = len(all_missions.mapped('driver_id'))
        total_vehicles = len(all_missions.mapped('vehicle_id'))

        for rec in self:
            rec.kpi_total_projects = total_projects
            rec.kpi_total_vehicule = total_vehicule
            rec.kpi_total_chauffeurs = total_chauffeurs
            rec.kpi_total_vehicles = total_vehicles

    #  DOCUMENT

    tdr_note = fields.Html(
        string="TDR (Termes de référence)"
    )

    # CHAMP SIGNATURE

    validated_by_security = fields.Many2one(
        'res.users',
        string="Validé par (Security)"
    )

    validated_by_finance = fields.Many2one(
        'res.users',
        string="Validé par (Finance)"
    )

    approved_by = fields.Many2one(
        'res.users',
        string="Approuvé par"
    )

    actual_amount = fields.Float(
        string="Montant réel"
    )

    budget_variance = fields.Float(
        string="Écart budget",
        compute="_compute_budget_variance",
        store=True
    )

    variance_status = fields.Char(
        string="Variance Budget",
        compute="_compute_variance_status"
    )

    @api.depends('budget_variance')
    def _compute_variance_status(self):
        for rec in self:
            if rec.budget_variance > 0:
                rec.variance_status = "Dépassement"
            elif rec.budget_variance < 0:
                rec.variance_status = "Économie"
            else:
                rec.variance_status = "Respecté"

    @api.depends('approved_amount', 'actual_amount')
    def _compute_budget_variance(self):
        for rec in self:
            rec.budget_variance = rec.actual_amount - rec.approved_amount

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
        for rec in self:
            if rec.state != 'submitted':
                raise UserError("Action non autorisée")

            rec.state = 'security'
            rec.validated_by_security = self.env.user

    def action_assign_fleet(self):
        for rec in self:
            if rec.state != 'security':
                raise UserError("Action non autorisée")

            rec.state = 'fleet'

    def action_validate_finance(self):
        for rec in self:
            if rec.state != 'fleet':
                raise UserError("Action non autorisée")

            rec.state = 'finance'
            rec.validated_by_finance = self.env.user

    def action_approve(self):
        for rec in self:
            if rec.state != 'finance':
                raise UserError("Action non autorisée")

            rec.state = 'approval'
            rec.approved_by = self.env.user

    def action_done(self):
        for rec in self:
            if rec.state != 'approval':
                raise UserError("Action non autorisée")

            rec.state = 'done'

    def action_reject(self):
        for rec in self:
            rec.state = 'rejected'

    def action_start_review(self):
        for rec in self:
            if rec.state != 'done':
                raise UserError("La mission doit être terminée")

            rec.state = 'review_finance'

    def action_close(self):
        for rec in self:
            if rec.state != 'review_finance':
                raise UserError("Revue financière requise avant clôture")

            rec.state = 'closed'

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
        ('review_finance', 'Revue Finance'),
        ('closed', 'Clôturée'),
        ('rejected', 'Rejetée')
    ], default='draft', tracking=True)