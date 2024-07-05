# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/5/16
# @Description: jmss

from abc import ABC
from concurrent.futures import ThreadPoolExecutor

from tornado.concurrent import run_on_executor

from libs.base_handler import BaseHandler
from libs.api_gateway.jumpserver.org import jms_org_api


class JmsHandler(BaseHandler, ABC):

    _thread_pool = ThreadPoolExecutor(3)

    @run_on_executor(executor='_thread_pool')
    def async_get_services(self):
        res = jms_org_api.get()
        return res

    async def get(self):
        res = await self.async_get_services()
        data = res.get("results", [])
        count = res.get("count", 0)
        res = dict(msg='获取成功', code=0, data=data, count=count)
        return self.write(res)


jms_urls = [
    (r"/api/v2/cmdb/jms/orgs/list/", JmsHandler, {"handle_name": "配置平台-堡垒机组织列表", "method": ["GET"]}),
]
