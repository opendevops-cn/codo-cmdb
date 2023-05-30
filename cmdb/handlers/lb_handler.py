#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/2/15 14:59
Desc    : this module is used for lb handler.
"""

import json
from abc import ABC
from libs.base_handler import BaseHandler
from services.asset_lb_service import get_lb_list_for_api, opt_obj
from services.asset_server_service import check_delete


class AssetLBHandler(BaseHandler, ABC):
    def get(self):
        res = get_lb_list_for_api(**self.params)
        self.write(res)

    def delete(self):
        data = json.loads(self.request.body.decode("utf-8"))
        check_status = check_delete(data, 'lb')
        if check_status:
            return self.write(dict(code=-2, msg='LB有业务关联，请先处理与业务的关联'))
        res = opt_obj.handle_delete(data)
        self.write(res)


lb_urls = [
    (r"/api/v2/cmdb/lb/", AssetLBHandler, {"handle_name": "CMDB-LB管理", "handle_status": "y"}),
]
