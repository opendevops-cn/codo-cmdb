# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/5/16
# @Description: jmss
from abc import ABC
import json

from websdk2.cache_context import cache_conn

from libs.base_handler import BaseHandler


class JmsHandler(BaseHandler, ABC):

    def get(self):
        cache = cache_conn()
        orgs = cache.get("JMS_ORG_ITEMS")
        if orgs:
            data = json.loads(orgs)
            res = dict(msg='获取成功', code=0, data=data.get("results", []), count=data.get("count"))
        else:
            # 没有缓存, 等待缓存刷新， 直接返回空数据
            res = dict(msg='获取成功', code=0, data=[], count=0)
        return self.write(res)


jms_urls = [
    (r"/api/v2/cmdb/jms/orgs/list/", JmsHandler, {"handle_name": "配置平台-堡垒机组织列表", "method": ["GET"]}),
]
