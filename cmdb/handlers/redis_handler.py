#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date   : 2023-2-08
Desc   : Redis API
"""

import json
from abc import ABC
from libs.base_handler import BaseHandler
from services.asset_redis_service import get_redis_list_for_api, opt_obj, add_redis
from services.asset_server_service import check_delete


class AssetRedisHandler(BaseHandler, ABC):
    def get(self):
        res = get_redis_list_for_api(**self.params)
        return self.write(res)

    def post(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = add_redis(data)
        self.write(res)

    def delete(self):
        data = json.loads(self.request.body.decode("utf-8"))
        check_status = check_delete(data, 'redis')
        if check_status:
            return self.write(dict(code=-2, msg='Redis有业务关联，请先处理与业务的关联'))
        res = opt_obj.handle_delete(data)
        self.write(res)


redis_urls = [
    (r"/api/v2/cmdb/redis/", AssetRedisHandler, {"handle_name": "配置平台-云商-Redis管理", "method": ["ALL"]}),
]
