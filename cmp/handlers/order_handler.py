#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Contact : 1084430062@qq.com
Author  : 娄文军
Date    : 2023/7/20 15:05
Desc    : 申购订单
"""

import json
from abc import ABC
from libs.base_handler import BaseHandler
from cmp.handlers.cloud_price import CloudPriceHandler
from services.order_service import get_order_template, get_order_info, info_obj, tmp_obj, update_tmp_last_time
from cmp.handlers.cloud_buy import CloudBuyHandler
from cmp.handlers.callback import CloudCallbackHandler
from cmp.handlers.cloud_ins_type import CloudInsTypeHandler
from libs.qcloud.qcloud_band_width_pkg import BandWidthPkg
from datetime import datetime


# TODO  请参考其他数据进行 路由功能备注
class OrderTemplateHandler(BaseHandler, ABC):
    """资源模板管理"""

    def get(self):
        res = get_order_template(**self.params)
        return self.write(res)

    def post(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = tmp_obj.handle_add(data)
        return self.write(res)

    def put(self):
        data = json.loads(self.request.body.decode("utf-8"))
        data["update_time"] = datetime.now()
        res = tmp_obj.handle_update(data)
        return self.write(res)

    def delete(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = tmp_obj.handle_delete(data)
        return self.write(res)

    def patch(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = update_tmp_last_time(data)
        return self.write(res)


class OrderInfoHandler(BaseHandler, ABC):
    """采购信息"""

    def get(self):
        res = get_order_info(**self.params)
        self.write(res)

    def post(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = info_obj.handle_add(data)
        return self.write(res)

    def delete(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = info_obj.handle_delete(data)
        return self.write(res)


class OrderBuyHandler(BaseHandler, ABC):
    """订单购买"""

    def post(self):
        # 购买
        data = json.loads(self.request.body.decode("utf-8"))
        api = CloudBuyHandler()
        res = api.buy(data)
        return self.write(res)


class OrderPriceHandler(BaseHandler, ABC):
    """获取云实例价格"""

    def post(self):
        data = json.loads(self.request.body.decode("utf-8"))
        account_id = data["account_id"]
        tx_api = CloudPriceHandler(account_id=account_id)
        res = tx_api.get_preice(data=data)
        return self.write(res)


class OrderCallbackHandler(BaseHandler, ABC):
    """Terraform 回调处理接口"""

    def post(self):
        data = json.loads(self.request.body.decode("utf-8"))
        # 将回调的结果数据进行保存
        obj = CloudCallbackHandler()
        res = obj.save(data)
        return self.write(res)


class TmpInsTypeHandler(BaseHandler, ABC):
    """模板的实例类型查询配置"""

    def post(self):
        data = json.loads(self.request.body.decode("utf-8"))
        account_id = data["account_id"]
        tx_api = CloudInsTypeHandler(account_id=account_id)
        res = tx_api.get_ins_type(data=data)
        return self.write(res)


class GetBandWidthPkgHandler(BaseHandler, ABC):
    """获取云带宽包"""

    def post(self):
        data = json.loads(self.request.body.decode("utf-8"))
        account_id = data["account_id"]
        tx_api = BandWidthPkg(account_id=account_id)
        res = tx_api.get_bandwh_pkg(data=data)
        return self.write(res)


order_template_urls = [
    (r"/api/v2/cmdb/order/template/", OrderTemplateHandler),
    (r"/api/v2/cmdb/order/info/", OrderInfoHandler),
    (r"/api/v2/cmdb/order/buy/", OrderBuyHandler),
    (r"/api/v2/cmdb/order/callback/", OrderCallbackHandler),
    # 云资源信息查询
    (r"/api/v2/cmdb/order/query_cloud/ins_type/", TmpInsTypeHandler),
    (r"/api/v2/cmdb/order/query_cloud/price/", OrderPriceHandler),
    (r"/api/v2/cmdb/order/query_cloud/bandwidth_pkg/", GetBandWidthPkgHandler),

]
