# -*- coding: utf-8 -*-
{
    'name': "支付宝",

    'summary': """支付宝集成支付""",

    'description': """
        本模块为支付宝支付模块，支持中国大陆商户使用。
        官方模块为支付宝国际版，与本模块不兼容，请用户根据自己情况选择其中一个版本使用。
    """,
    'author': "black-cat",
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
    'images':['images/alipay.png'],
    "price": "20",
    "currency": 'USD',
    "application":True,
    'support': 'kfx2007@163.com',
    "license": "OPL-1",
}
