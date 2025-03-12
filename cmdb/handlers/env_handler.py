# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/9/23
# @Description: 区服环境


import json
from abc import ABC
from libs.base_handler import BaseHandler
from services.env_service import get_env_list_for_api, update_env_for_api, add_env_for_api, opt_obj as opt_obj_env, \
    get_all_env_list_for_api, check_idip_connection, get_env_list_for_api_v2


class EnvHandler(BaseHandler, ABC):
    def get(self):
        if self.request_tenantid:
            self.params.update(biz_id=self.request_tenantid)
        res = get_env_list_for_api(**self.params)
        return self.write(res)

    def delete(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = opt_obj_env.handle_delete(data)
        self.write(res)

    def post(self):
        data = json.loads(self.request.body.decode("utf-8"))
        if "biz_id" not in data:
            data.update(biz_id=self.request_tenantid)
        res = add_env_for_api(data)
        self.write(res)

    def put(self):
        data = json.loads(self.request.body.decode("utf-8"))
        if "biz_id" not in data:
            data.update(biz_id=self.request_tenantid)
        res = update_env_for_api(data)
        self.write(res)


class EnvListHandler(BaseHandler, ABC):
    def get(self):
        if self.request_tenantid:
            self.params.update(biz_id=self.request_tenantid)
        res = get_all_env_list_for_api(**self.params)
        return self.write(res)

class NoAuthEnvHandler(BaseHandler, ABC):
    def get(self):
        if self.request_tenantid:
            self.params.update(biz_id=self.request_tenantid)
        res = get_env_list_for_api_v2(**self.params)
        return self.write(res)
    
class IdipConnectionCheckHandler(BaseHandler, ABC):
    def post(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = check_idip_connection(data)
        return self.write(res)

env_urls = [
    (
        r"/cbb_area/env/",
        EnvHandler,
        {"handle_name": "配置平台-环境管理", "method": ["ALL"]},
    ),
    (
        r"/cbb_area/env/list/",
        EnvListHandler,
        {"handle_name": "配置平台-环境列表", "method": ["GET"]},
    ),
    (
        r"/cbb_area/env/idip/check/",
        IdipConnectionCheckHandler,
        {"handle_name": "配置平台-环境列表-IDIP连通性检测", "method": ["POST"]},
    ),
    (
        r"/cbb_area/cbb_acc/env/list/",
        NoAuthEnvHandler,
        {"handle_name": "配置平台-免鉴权环境列表", "method": ["GET"]},
    ),
]