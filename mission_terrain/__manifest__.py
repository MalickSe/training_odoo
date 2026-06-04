{
    'name': 'Gestion Missions Terrain',
    'version': '19.0.1',
    'summary': 'Gestion des missions terrain ENABEL',
    'category': 'Operations',
    'author': 'Malick/MalickSe',
    'depends': ['base', 'project', 'mail', 'fleet'],
    'data': [
        'report/mission_report.xml',
        'report/mission_finance_report.xml',
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/mission_views.xml',
        'views/participant_views.xml',

    ],
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}

