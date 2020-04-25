# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request, redirect_with_hash
import logging
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class Alipay(http.Controller):

    _return_url = "/payment/alipay/validate"
    _notify_url = "/payment/alipay/notify"

    @http.route('/payment_alipay/jump', auth='public')
    def index(self, **kw):
        """跳转至支付宝付款页面"""
        kw["csrf_token"] = request.csrf_token()
        kw["notify_url"] = self._notify_url
        alipay = request.env["payment.acquirer"].sudo().search(
            [('provider', '=', 'alipay')], limit=1)
        return redirect_with_hash(alipay._get_alipay_url(kw))

    def validate_pay_data(self, **kwargs):
        """验证支付结果"""
        """
        {
            'charset': 'utf-8', 
            '   ': 'SO824-6', 
            'method': 'alipay.trade.page.pay.return', 
            'total_amount': '1.00', 
            'sign': 'kMKtZpyVMZT+GJIZVXL2ASdc7uy0uxa6iJVElKpa3a+YRROOyGDOxQX4wjC4xvPXre9rEuwygm83mu5LYQRyYQnlsZEz1UHhrQvnKpxjzbDZxDTzr32T2d2rpZYKllSfmB8FmVHGp57vCq7XiVnRyySeruoPxfnwB/eelT1RKRO0yu5T7Hr9M9W8w/av9l07w96er8CJiG3T4LKi91G8YvNRXUqU9WmscpZj2OuUGnaqDV9hp3drAMkUtV/w/vI3hJi72oqXzJF6V3a0ElFQ87UUVUtQ0xjfGoXUcVMD7YE1Ms5F5Qj0+81JJVt1cIl1yrbhqWR7axaYJ/NInrFBkA==', 
            'trade_no': '2019110522001414381000118540', 
            'auth_app_id': '2016101100664659', 
            'version': '1.0', 
            'app_id': '2016101100664659', 
            'sign_type': 'RSA2', 
            'seller_id': '2088102179155775', 
            'timestamp': '2019-11-05 16:26:20'
        }
        """
        res = request.env['payment.transaction'].sudo(
        ).form_feedback(kwargs, 'alipay')
        return res

    @http.route('/payment/alipay/validate', type="http", auth="none", methods=['POST', 'GET'], csrf=False)
    def alipay_validate(self, **kwargs):
        """验证支付结果"""
        _logger.info("开始验证支付宝支付结果...")
        try:
            res = self.validate_pay_data(**kwargs)
        except ValidationError:
            _logger.exception("支付验证失败")
        return redirect_with_hash("/payment/process")

    @http.route('/payment/alipay/notify', csrf=False, type="http", auth='none', method=["POST"])
    def alipay_notify(self, **kwargs):
        """接收支付宝异步通知"""
        _logger.debug(f"接收支付宝异步通知...收到的数据:{kwargs}")
        """
        {
            'gmt_create': '2019-11-06 12:52:18', 
            'charset': 'utf-8', 
            'gmt_payment': '2019-11-06 12:52:28', 
            'notify_time': '2019-11-06 12:52:29', 
            'subject': 'SO015-1', 
            'sign': 'cG6uWeaX+5FXAJu7O02CI6b8V5L5Qamo/lz3LWvBVNCni4A5G1oWezCOVsqCEII/jO9mErQoY5ZXIW7uayRDOmp4nVWjl9kppDCNdi0YJHTdvY3WfoEUwc6XbDplUWWn9U5X00CPnUIlYMbfWaFFmsW/PVzhECBP2V08iBvbi2pscykf5LtyskG6gorJjzkNUE/WoOw+LV3JR30U8IFbfys7m67HDYRMjbdfSIGVDxZUfNMbgQK0/P3DyDQ0PbmdiD8w/e8WHM29cocJ20jnu8j5ZXyngWw09R/VAAW+15IHWJ+26JLA+vV/IM4Hp+v7C/my0Q+fpQPTcg6QEM/d5w==', 'buyer_id': '2088102179514385', 'passback_params': 'return_url%3Dhttp%3A%2F%2Fproject.mixoo.cn%3A80%2Fpayment%2Falipay%2Fvalidate%26reference%3DSO015-1%26amount%3D1.0%26currency%3DCNY%26csrf_token%3D24cc66c330aed25a1bcc9ca07dfbf8fa568327d6o1573019530%26notify_url%3Dhttp%3A%2F%2Fproject.mixoo.cn%3A80%2Fpayment%2Falipay%2Fnotify', 
            'invoice_amount': '1.00', 
            'version': '1.0', 
            'notify_id': '2019110600222125229014381000618776', 
            'fund_bill_list': '[{"amount":"1.00","fundChannel":"ALIPAYACCOUNT"}]', 
            'notify_type': 'trade_status_sync', 
            'out_trade_no': 'SO015-1', 
            'total_amount': '1.00', 
            'trade_status': 'TRADE_SUCCESS', 
            'trade_no': '2019110622001414381000117218', 
            'auth_app_id': '2016101100664659', 
            'receipt_amount': '1.00', 
            'point_amount': '0.00', 
            'app_id': '2016101100664659', 
            'buyer_pay_amount': '1.00', 
            'sign_type': 'RSA2', 
            'seller_id': '2088102179155775'
            }
        """
        payment = request.env["payment.acquirer"].sudo().search(
            [('provider', '=', 'alipay')], limit=1)
        result = payment._verify_pay(kwargs)
        return "success" if result else "failed"
