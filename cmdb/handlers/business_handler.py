#!/usr/bin/env python
# -*-coding:utf-8-*-

"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/2/8 17:56
Desc    : 业务信息
"""

import json
from abc import ABC
from libs.base_handler import BaseHandler
from services.biz_service import get_business_list, add_biz, opt_obj


class BusinessHandlers(BaseHandler, ABC):
    def get(self):
        res = get_business_list(**self.params)
        return self.write(res)

    def post(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = add_biz(data)
        return self.write(res)

    def put(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = opt_obj.handle_update(data)
        return self.write(res)


biz_urls = [
    (r"/api/v2/cmdb/biz/", BusinessHandlers, {"handle_name": "配置平台-业务-业务列表", "method": ["GET"]}),
]
