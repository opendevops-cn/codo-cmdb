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
from cmp.utils.cloud_price import CloudPrice
from services.order_service import get_order_template, get_order_info, info_obj, tmp_obj, update_tmp_last_time
from cmp.utils.cloud_buy import CloudBuyUtils
from cmp.utils.callback import CloudCallback
from cmp.utils.cloud_ins_type import CloudInsType
from cmp.utils.cloud_band_width_pkg import BandWidthPkg
from datetime import datetime

# TODO

"""
1、 定义函数的时候需要定义返回值类型
2、 Handler 结尾的命名是标识这个是一个API
3、 对数据库的操作主要放在 service 目录下
"""


class OrderTemplateHandler(BaseHandler, ABC):
    """资源模板管理"""

    def get(self):
        """查询模板信息"""
        res = get_order_template(**self.params)
        return self.write(res)

    def post(self):
        """新增模板"""
        data = json.loads(self.request.body.decode("utf-8"))
        res = tmp_obj.handle_add(data)
        return self.write(res)

    def put(self):
        """修改模板"""
        data = json.loads(self.request.body.decode("utf-8"))
        data["update_time"] = datetime.now()
        res = tmp_obj.handle_update(data)
        return self.write(res)

    def delete(self):
        """删除模板"""
        data = json.loads(self.request.body.decode("utf-8"))
        res = tmp_obj.handle_delete(data)
        return self.write(res)

    def patch(self):
        """更新模板最后使用时间"""
        data = json.loads(self.request.body.decode("utf-8"))
        res = update_tmp_last_time(data)
        return self.write(res)


class OrderInfoHandler(BaseHandler, ABC):
    """采购信息"""

    def get(self):
        """获取资源订单信息"""
        res = get_order_info(**self.params)
        self.write(res)

    def post(self):
        """创建订单信息"""
        data = json.loads(self.request.body.decode("utf-8"))
        res = info_obj.handle_add(data)
        return self.write(res)

    def delete(self):
        """删除订单信息"""
        data = json.loads(self.request.body.decode("utf-8"))
        res = info_obj.handle_delete(data)
        return self.write(res)


class OrderBuyHandler(BaseHandler, ABC):
    """订单购买"""

    def post(self):
        """购买"""
        data = json.loads(self.request.body.decode("utf-8"))
        api = CloudBuyUtils()
        res = api.buy(data)
        return self.write(res)


class OrderPriceHandler(BaseHandler, ABC):
    """获取云实例价格"""

    def post(self):
        """取云实例价格"""
        data = json.loads(self.request.body.decode("utf-8"))
        account_id = data["account_id"]
        tx_api = CloudPrice(account_id=account_id)
        res = tx_api.get_preice(data=data)
        return self.write(res)


class OrderCallbackHandler(BaseHandler, ABC):
    """Terraform 回调处理接口"""

    def post(self):
        """将回调的结果数据进行保存"""
        data = json.loads(self.request.body.decode("utf-8"))
        obj = CloudCallback()
        res = obj.save(data)
        return self.write(res)


class TmpInsTypeHandler(BaseHandler, ABC):
    """模板的实例类型查询配置"""

    def post(self):
        """模板的实例类型查询配置"""
        data = json.loads(self.request.body.decode("utf-8"))
        account_id = data["account_id"]
        tx_api = CloudInsType(account_id=account_id)
        res = tx_api.get_ins_type(data=data)
        return self.write(res)


class GetBandWidthPkgHandler(BaseHandler, ABC):
    """获取云带宽包"""

    def post(self):
        """获取云带宽包"""
        data = json.loads(self.request.body.decode("utf-8"))
        account_id = data["account_id"]
        tx_api = BandWidthPkg(account_id=account_id)
        res = tx_api.get_bandwh_pkg(data=data)
        return self.write(res)


order_template_urls = [
    (r"/api/v2/cmdb/order/template/", OrderTemplateHandler,
     {"handle_name": "CMDB-资源采购-模板管理", "method": ["ALL"]}),
    (r"/api/v2/cmdb/order/info/", OrderInfoHandler, {"handle_name": "CMDB-资源采购-采购列表", "method": ["ALL"]}),
    (r"/api/v2/cmdb/order/buy/", OrderBuyHandler, {"handle_name": "CMDB-资源采购-资源购买", "method": ["POST"]}),
    (r"/api/v2/cmdb/order/callback/", OrderCallbackHandler,
     {"handle_name": "CMDB-资源采购-资源购买后回调", "method": ["POST"]}),
    # 云资源信息查询
    (r"/api/v2/cmdb/order/query_cloud/ins_type/", TmpInsTypeHandler,
     {"handle_name": "CMDB-资源采购-获取实例类型", "method": ["POST"]}),
    (r"/api/v2/cmdb/order/query_cloud/price/", OrderPriceHandler,
     {"handle_name": "CMDB-资源采购-获取实例价格", "method": ["POST"]}),
    (r"/api/v2/cmdb/order/query_cloud/bandwidth_pkg/", GetBandWidthPkgHandler,
     {"handle_name": "CMDB-资源采购-带宽包", "method": ["POST"]}),

]
