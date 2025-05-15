# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/9/19
# @Description: CBB区服接口
import json
from abc import ABC
from concurrent.futures import ThreadPoolExecutor

from tornado.concurrent import run_on_executor

from libs.base_handler import BaseHandler
from services.area_service import (
    create_area,
    create_or_update_big_area,
    delete_area,
    delete_big_area,
    get_area_list,
    get_big_area_detail,
    get_big_area_detail_for_gmt,
    get_big_area_list,
    get_big_area_list_for_gmt,
    update_area,
)
from services.env_service import env_checker


class CBBAreaHandler(BaseHandler, ABC):
    _thread_pool = ThreadPoolExecutor(3)

    @run_on_executor(executor="_thread_pool")
    def async_get_area_list(self):
        if not self.request_tenantid:
            biz_id = self.params.get("biz_id")
        else:
            biz_id = self.request_tenantid
        self.params.update(biz_id=biz_id)
        return get_area_list(**self.params)

    async def get(self):
        res = await self.async_get_area_list()
        return self.write(res)

    @run_on_executor(executor="_thread_pool")
    def async_create_area(self):
        data = json.loads(self.request.body.decode("utf-8"))
        if self.request_tenantid:
            data["biz_id"] = self.request_tenantid
        return create_area(**data)

    async def post(self):
        res = await self.async_create_area()
        return self.write(res)

    @run_on_executor(executor="_thread_pool")
    def async_delete_area(self):
        data = json.loads(self.request.body.decode("utf-8"))
        if self.request_tenantid:
            data.update(biz_id=self.request_tenantid)
        return delete_area(**data)

    async def delete(self):
        res = await self.async_delete_area()
        return self.write(res)

    @run_on_executor(executor="_thread_pool")
    def async_update_area(self):
        data = json.loads(self.request.body.decode("utf-8"))
        if self.request_tenantid:
            data.update(biz_id=self.request_tenantid)
        return update_area(**data)

    async def put(self):
        res = await self.async_update_area()
        return self.write(res)


class CBBBigAreaDetailHandler(BaseHandler, ABC):
    _thread_pool = ThreadPoolExecutor(3)

    @run_on_executor(executor="_thread_pool")
    def async_get_big_area_detail(self):
        if not self.request_tenantid:
            biz_id = self.params.get("biz_id")
        else:
            biz_id = self.request_tenantid

        self.params.update(biz_id=biz_id)
        return get_big_area_detail(**self.params)

    async def get(self):
        res = await self.async_get_big_area_detail()
        return self.write(res)


class CBBBigAreaHandler(BaseHandler, ABC):
    _thread_pool = ThreadPoolExecutor(3)

    @run_on_executor(executor="_thread_pool")
    def async_get_big_area_list(self):
        if not self.request_tenantid:
            biz_id = self.params.get("biz_id")
        else:
            biz_id = self.request_tenantid
        self.params.update(biz_id=biz_id)
        return get_big_area_list(**self.params)

    async def get(self):
        res = await self.async_get_big_area_list()
        return self.write(res)

    @run_on_executor(executor="_thread_pool")
    def async_create_or_update_big_area(self):
        data = json.loads(self.request.body.decode("utf-8"))
        if self.request_tenantid:
            data.update(biz_id=self.request_tenantid)
        return create_or_update_big_area(**data)

    async def post(self):
        res = await self.async_create_or_update_big_area()
        return self.write(res)

    @run_on_executor(executor="_thread_pool")
    def async_delete_big_area(self):
        data = json.loads(self.request.body.decode("utf-8"))
        big_area = data.get("big_area")
        env_id = data.get("env_id")
        if self.request_tenantid:
            biz_id = self.request_tenantid
        else:
            biz_id = data.get("biz_id")
        return delete_big_area(big_area, env_id, biz_id)

    async def delete(self):
        res = await self.async_delete_big_area()
        return self.write(res)

    async def put(self):
        res = await self.async_create_or_update_big_area()
        return self.write(res)


class CBBAreaWithoutPrdHandler(CBBAreaHandler):
    def prepare(self):
        result, msg = env_checker(self)
        if not result:
            self.set_status(200)
            self.write(dict(code=-1, msg=msg))
            self.finish()
            return
        return super().prepare()


class CBBBigAreaWithoutPrdHandler(CBBBigAreaHandler):
    def prepare(self):
        result, msg = env_checker(self)
        if not result:
            self.set_status(200)
            self.write(dict(code=-1, msg=msg))
            self.finish()
            return
        return super().prepare()


class CBBBigAreaDetailWithoutPrdHandler(CBBBigAreaDetailHandler):
    def prepare(self):
        result, msg = env_checker(self)
        if not result:
            self.set_status(200)
            self.write(dict(code=-1, msg=msg))
            self.finish()
            return
        return super().prepare()


class CBBBigAreaForGMTHandler(CBBBigAreaHandler):
    _thread_pool = ThreadPoolExecutor(3)

    @run_on_executor(executor="_thread_pool")
    def async_get_big_area_list(self):
        if not self.request_tenantid:
            biz_id = self.params.get("biz_id")
        else:
            biz_id = self.request_tenantid
        self.params.update(biz_id=biz_id)
        return get_big_area_list_for_gmt(**self.params)

    async def get(self):
        res = await self.async_get_big_area_list()
        return self.write(res)


class CBBBigAreaDetailForGMTHandler(BaseHandler, ABC):
    _thread_pool = ThreadPoolExecutor(3)

    @run_on_executor(executor="_thread_pool")
    def async_get_big_area_detail(self):
        if not self.request_tenantid:
            biz_id = self.params.get("biz_id")
        else:
            biz_id = self.request_tenantid

        self.params.update(biz_id=biz_id)
        return get_big_area_detail_for_gmt(**self.params)

    async def get(self):
        res = await self.async_get_big_area_detail()
        return self.write(res)


class CBBAreaForGMTHandler(CBBAreaHandler): ...


area_urls = [
    (r"/cbb_area/area/", CBBAreaHandler, {"handle_name": "配置平台-区服管理", "method": ["ALL"]}),
    (r"/cbb_area/big_area/", CBBBigAreaHandler, {"handle_name": "配置平台-大区管理", "method": ["ALL"]}),
    (r"/cbb_area/big_area/detail/", CBBBigAreaDetailHandler, {"handle_name": "配置平台-大区详情", "method": ["GET"]}),
    (
        r"/cbb_area/without_prd/area/",
        CBBAreaWithoutPrdHandler,
        {"handle_name": "配置平台-区服管理-非生产环境", "method": ["ALL"]},
    ),
    (
        r"/cbb_area/without_prd/big_area/",
        CBBBigAreaWithoutPrdHandler,
        {"handle_name": "配置平台-大区管理-非生产环境", "method": ["ALL"]},
    ),
    (
        r"/cbb_area/without_prd/big_area/detail/",
        CBBBigAreaDetailWithoutPrdHandler,
        {"handle_name": "配置平台-大区详情-非生产环境", "method": ["GET"]},
    ),
    (
        r"/cbb_area/gmt/big_area/",
        CBBBigAreaForGMTHandler,
        {"handle_name": "配置平台-大区管理-GMT专用", "method": ["ALL"]},
    ),
    (
        r"/cbb_area/gmt/big_area/detail/",
        CBBBigAreaDetailForGMTHandler,
        {"handle_name": "配置平台-大区详情-GMT专用", "method": ["GET"]},
    ),
    (
        r"/cbb_area/gmt/area/",
        CBBAreaForGMTHandler,
        {"handle_name": "配置平台-区服管理-GMT专用", "method": ["ALL"]},
    ),
]
