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
        return redirect_with_hash("/shop/confirmation")

    @http.route('/payment/alipay/notify', csrf=False, type="http", auth='none', method=["POST"])
    def alipay_notify(self, **kwargs):
        """接收支付宝异步通知"""
        _logger.debug("接收支付宝异步通知...收到的数据:{}".format(kwargs))
        payment = request.env["payment.acquirer"].sudo().search(
            [('provider', '=', 'alipay')], limit=1)
        result = payment._verify_pay(kwargs)
        return "success" if result else "failed"
