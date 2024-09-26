# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/9/23
# @Description: 区服环境


import json
from abc import ABC
from libs.base_handler import BaseHandler
from services.env_service import get_env_list_for_api, update_env_for_api, add_env_for_api, opt_obj as opt_obj_env, \
    get_all_env_list_for_api


class EnvHandler(BaseHandler, ABC):
    def get(self):
        res = get_env_list_for_api(**self.params)
        return self.write(res)

    def delete(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = opt_obj_env.handle_delete(data)
        self.write(res)

    def post(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = add_env_for_api(data)
        self.write(res)

    def put(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = update_env_for_api(data)
        self.write(res)


class EnvListHandler(BaseHandler, ABC):
    def get(self):
        res = get_all_env_list_for_api()
        return self.write(res)

env_urls = [
    (r"/api/v2/cmdb/env/", EnvHandler, {"handle_name": "配置平台-环境管理", "method": ["ALL"]}),
    (r"/api/v2/cmdb/env/list/", EnvListHandler, {"handle_name": "配置平台-环境列表", "method": ["GET"]}),
]