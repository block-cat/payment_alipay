# -*- coding: utf-8 -*-

from odoo import models, fields, api
from alipay.api import AliPay
from Crypto.PublicKey import RSA
import base64
from urllib.parse import quote_plus
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class AcquirerAlipay(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('alipay', "AliPay")])
    seller_id = fields.Char("Alipay Seller Id")
    alipay_appid = fields.Char("Alipay AppId")
    alipay_secret = fields.Binary("Merchant Private Key")
    alipay_public_key = fields.Binary("Alipay Public Key")
    alipay_sign_type = fields.Selection(
        selection=[('rsa', 'RSA'), ('rsa2', 'RSA2')], string="Sign Type")

    def _get_feature_support(self):
        """Get advanced feature support by provider.

        Each provider should add its technical in the corresponding
        key for the following features:
            * fees: support payment fees computations
            * authorize: support authorizing payment (separates
                         authorization and capture)
            * tokenize: support saving payment data in a payment.tokenize
                        object
        """
        res = super(AcquirerAlipay, self)._get_feature_support()
        res['fees'].append('alipay')
        return res

    def _get_alipay(self):
        """
        获取支付宝sdk
        """
        try:
            private_key = RSA.importKey(base64.b64decode(
                self.alipay_secret).decode('utf-8'))
            public_key = RSA.importKey(base64.b64decode(
                self.alipay_public_key).decode('utf-8'))

            if self.state == "enabled":
                alipay = AliPay(self.alipay_appid, private_key, ali_public_key=public_key,
                                sign_type=self.alipay_sign_type)
            else:
                alipay = AliPay(self.alipay_appid, private_key, ali_public_key=public_key,
                                sign_type=self.alipay_sign_type, sandbox=True)
            return alipay
        except Exception as err:
            _logger.exception(f"生成支付宝客户端失败：{err}")

    @api.model
    def _get_alipay_url(self, params=None):
        """Alipay URL"""
        base_url = self.env['ir.config_parameter'].sudo(
        ).get_param('web.base.url')
        # 额外的参数
        passback_params = quote_plus("&".join(
            f"{k}={v}" for k, v in params.items() if v)) if params else None
        alipay = self._get_alipay()
        alipay.return_url = f'{base_url}{params["return_url"]}'
        alipay.notify_url = f'{base_url}{params["notify_url"]}'

        return alipay.pay.trade_page_pay(params["reference"], params["amount"],
                                         params["reference"], product_code="FAST_INSTANT_TRADE_PAY",
                                         passback_params=passback_params)

    @api.model
    def alipay_compute_fees(self, amount, currency_id, country_id):
        """
            支付宝也是要恰饭的
            单笔费率 0.6%
        """
        if not self.fees_active:
            return 0.0
        return self.fees_dom_var / 100 * amount

    @api.model
    def alipay_get_form_action_url(self):
        return "/payment_alipay/jump"

    @api.model
    def alipay_form_generate_values(self, values):
        alipay_tx_values = dict(values)
        alipay_tx_values.update({
            "return_url": "/payment/alipay/validate",
            "notify_url": "/payment/alipay/notify"
        })
        return alipay_tx_values

    def _verify_pay(self, data):
        """
        验证支付宝返回的信息
        """
        alipay = self._get_alipay()
        # 验证是否符合验签逻辑
        if not alipay.comm.validate_sign(data):
            _logger.warn(f"支付宝推送支付结果验签失败：{data}")
            return False
        # 校验收款方
        if self.alipay_appid != data["app_id"]:
            _logger.warn(f"支付宝推送AppID校验失败:{data['app_id']}")
            return False
        if self.seller_id != data["seller_id"]:
            _logger.warn(f"支付宝推送卖家ID校验失败:{data['seller_id']}")
            return False
        # 校验支付信息
        transaction = self.env["payment.transaction"].sudo().search(
            [('reference', '=', data["out_trade_no"])], limit=1)
        if float(transaction.amount) != float(data["total_amount"]):
            _logger.warn(
                f"支付宝推送金额{float(transaction.amount)}与系统订单不符:{float(data['total_amount'])}")
            return False
        # 将支付结果设置完成
        if transaction.state != "done" and data["trade_status"] == "TRADE_SUCCESS":
            transaction.acquirer_reference = data["trade_no"]
            transaction._set_transaction_done()
            # 完成付款单
            sale_order = self.env['sale.order'].search(
                [('name', '=', data["out_trade_no"])], limit=1)
            if sale_order:
                elect = self.env.ref(
                    'payment.account_payment_method_electronic_in').id
                sale_order.custom_payment_id.payment_method_id = elect
                sale_order.custom_payment_id.payment_transaction_id = self.id
                sale_order.custom_payment_id.post()

        return True


class TxAlipay(models.Model):
    _inherit = 'payment.transaction'

    alipay_txn_type = fields.Char('Transaction type')

    @api.model
    def _alipay_form_get_tx_from_data(self, data):
        """获取支付事务"""
        if not data.get("out_trade_no", None):
            raise ValidationError("订单号错误")
        reference = data.get("out_trade_no")
        txs = self.env["payment.transaction"].search(
            [('reference', '=', reference)])
        if not txs or len(txs) > 1:
            error_msg = 'Alipay: received data for reference %s' % (reference)
            if not txs:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.info(error_msg)
            raise ValidationError(error_msg)
        return txs[0]

    @api.model
    def _alipay_form_validate(self, data):
        """验证支付"""
        if self.state == 'done':
            _logger.info(f"支付已经验证：{data['out_trade_no']}")
            return True
        result = {
            "acquirer_reference": data["trade_no"]
        }
        # 根据支付宝同步返回的信息，去支付宝服务器查询
        payment = self.env["payment.acquirer"].sudo().search(
            [('provider', '=', 'alipay')], limit=1)
        alipay = payment._get_alipay()
        res = alipay.pay.trade_query(out_trade_no=data["out_trade_no"])
        # 校验结果
        if res["code"] == "10000" and res["trade_status"] in ("TRADE_SUCCESS", "TRADE_FINISHED"):
            _logger.info(f"支付单：{data['out_trade_no']} 已成功付款")
            date_validate = fields.Datetime.now()
            res.update(date=date_validate)
            self._set_transaction_done()
            self.execute_callback()
        if res["code"] == "10000" and res["trade_status"] == "WAIT_BUYER_PAY":
            _logger.info(f"支付单：{data['out_trade_no']} 正等待付款...")
            self._set_transaction_pending()
        if res["code"] == "10000" and res["trade_status"] == "TRADE_CLOSED":
            _logger.info(f"支付单：{data['out_trade_no']} 已关闭或已退款.")
            self._set_transaction_cancel()
        # 完成付款单
        sale_order = self.env['sale.order'].search(
            [('name', '=', data["out_trade_no"])], limit=1)
        if sale_order:
            elect = self.env.ref(
                'payment.account_payment_method_electronic_in').id
            sale_order.custom_payment_id.payment_method_id = elect
            sale_order.custom_payment_id.payment_transaction_id = self.id
            sale_order.custom_payment_id.post()

        return self.write(result)
