# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/9/19
# @Description: CBB区服接口
import json
from abc import ABC
from concurrent.futures import ThreadPoolExecutor

from tornado.concurrent import run_on_executor

from libs.base_handler import BaseHandler
from services.area_service import get_big_area_list, get_area_list, create_or_update_big_area, create_area, \
    delete_big_area, delete_area, get_big_area_detail, update_area


class CBBAreaHandler(BaseHandler, ABC):

    _thread_pool = ThreadPoolExecutor(3)

    @run_on_executor(executor='_thread_pool')
    def async_get_area_list(self):
        self.params.update(biz_id=self.request_tenantid)
        return get_area_list(**self.params)

    async def get(self):
        res = await self.async_get_area_list()
        return self.write(res)

    @run_on_executor(executor='_thread_pool')
    def async_create_area(self):
        data = json.loads(self.request.body.decode("utf-8"))
        data.update(biz_id=self.request_tenantid)
        return create_area(**data)

    async def post(self):
        res = await self.async_create_area()
        return self.write(res)

    @run_on_executor(executor='_thread_pool')
    def async_delete_area(self):
        data = json.loads(self.request.body.decode("utf-8"))
        data.update(biz_id=self.request_tenantid)
        return delete_area(**data)

    async def delete(self):
        res = await self.async_delete_area()
        return self.write(res)

    @run_on_executor(executor='_thread_pool')
    def async_update_area(self):
        data = json.loads(self.request.body.decode("utf-8"))
        data.update(biz_id=self.request_tenantid)
        return update_area(**data)

    async def put(self):
        res = await self.async_update_area()
        return self.write(res)


class CBBBigAreaDetailHandler(BaseHandler, ABC):

    _thread_pool = ThreadPoolExecutor(3)

    @run_on_executor(executor='_thread_pool')
    def async_get_big_area_detail(self):
        self.params.update(biz_id=self.request_tenantid)
        return get_big_area_detail(**self.params)

    async def get(self):
        res = await self.async_get_big_area_detail()
        return self.write(res)



class CBBBigAreaHandler(BaseHandler, ABC):
    _thread_pool = ThreadPoolExecutor(3)

    @run_on_executor(executor='_thread_pool')
    def async_get_big_area_list(self):
        self.params.update(biz_id=self.request_tenantid)
        return get_big_area_list(**self.params)

    async def get(self):
        res = await self.async_get_big_area_list()
        return self.write(res)

    @run_on_executor(executor='_thread_pool')
    def async_create_or_update_big_area(self):
        data = json.loads(self.request.body.decode("utf-8"))
        data.update(biz_id=self.request_tenantid)
        return create_or_update_big_area(**data)

    async def post(self):
        res = await self.async_create_or_update_big_area()
        return self.write(res)

    @run_on_executor(executor='_thread_pool')
    def async_delete_big_area(self):
        data = json.loads(self.request.body.decode("utf-8"))
        big_area = data.get("big_area")
        env_id = data.get("env_id")
        return delete_big_area(big_area, env_id, self.request_tenantid)

    async def delete(self):
        res = await self.async_delete_big_area()
        return self.write(res)

    async def put(self):
        res = await self.async_create_or_update_big_area()
        return self.write(res)




area_urls = [
    (r"/cbb_area/area/", CBBAreaHandler, {"handle_name": "配置平台-区服管理", "method": ["ALL"]}),
    (r"/cbb_area/big_area/", CBBBigAreaHandler, {"handle_name": "配置平台-大区管理", "method": ["ALL"]}),
    (r"/cbb_area/big_area/detail/", CBBBigAreaDetailHandler, {"handle_name": "配置平台-大区详情", "method": ["GET"]}),
]

