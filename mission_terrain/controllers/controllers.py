# from odoo import http


# class MissionTerrain(http.Controller):
#     @http.route('/mission_terrain/mission_terrain', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/mission_terrain/mission_terrain/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('mission_terrain.listing', {
#             'root': '/mission_terrain/mission_terrain',
#             'objects': http.request.env['mission_terrain.mission_terrain'].search([]),
#         })

#     @http.route('/mission_terrain/mission_terrain/objects/<model("mission_terrain.mission_terrain"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('mission_terrain.object', {
#             'object': obj
#         })

