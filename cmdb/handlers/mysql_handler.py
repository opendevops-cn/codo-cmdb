#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date   : 2023-2-08
Desc   : RDS API
"""

import json
from abc import ABC
from libs.base_handler import BaseHandler
from services.asset_mysql_service import get_mysql_list_for_api, opt_obj


class AssetMySQLHandler(BaseHandler, ABC):
    def get(self):
        res = get_mysql_list_for_api(**self.params)
        return self.write(res)

    def delete(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = opt_obj.handle_delete(data)
        self.write(res)


mysql_urls = [
    (r"/api/v2/cmdb/mysql/", AssetMySQLHandler, {"handle_name": "CMDB-MySQL管理", "handle_status": "y"}),
]
