#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: shenshuo
Since: 2019/1/12 15:10
Desc:  Consul
"""

import json
from abc import ABC
from libs.base_handler import BaseHandler
from libs.consul_registry import ConsulOpt
from concurrent.futures import ThreadPoolExecutor
from tornado.concurrent import run_on_executor

obj = ConsulOpt()


class ConsulServiceHandlers(BaseHandler, ABC):
    _thread_pool = ThreadPoolExecutor(3)

    @run_on_executor(executor='_thread_pool')
    def async_get_services(self):
        res = obj.get_services()
        return res

    async def get(self):
        res = await self.async_get_services()
        return self.write(res)


class ConsulInstanceHandlers(BaseHandler, ABC):
    _thread_pool = ThreadPoolExecutor(3)

    @run_on_executor(executor='_thread_pool')
    def async_get_instances(self, server):
        res = obj.get_instances(server)
        return res

    @run_on_executor(executor='_thread_pool')
    def del_instances(self, id_list):
        res = obj.deregister_service_batch(id_list)
        return res

    async def get(self):
        server = self.params.get('server')
        res = await self.async_get_instances(server)
        return self.write(res)

    async def delete(self):
        data = json.loads(self.request.body.decode("utf-8"))
        id_list = data.get('id_list')
        res = await self.del_instances(id_list)
        return self.write(res)


consul_urls = [
    (r"/api/v2/cmdb/consul/service/", ConsulServiceHandlers,
     {"handle_name": "配置平台-监控-consul服务列表", "method": ["ALL"]}),
    (r"/api/v2/cmdb/consul/instance/", ConsulInstanceHandlers,
     {"handle_name": "配置平台-监控-consul发现管理", "method": ["ALL"]}),
]
