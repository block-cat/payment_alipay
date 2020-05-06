# -*- coding: utf-8 -*-
{
    'name': "支付宝",

    'summary': """支付宝集成支付""",

    'description': """
        支付宝集成支付
    """,
    'author': "Kevin Kong",
    'website': "http://www.odoomommy.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'tools',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['payment'],

    # always loaded
    'data': [
        'security/data.xml',
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    "application":True
}
