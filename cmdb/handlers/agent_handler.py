#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# @File    :   agent_handler.py
# @Time    :   2024/12/25 10:37:29
# @Author  :   DongdongLiu
# @Version :   1.0
# @Desc    :   agent server 注册接口
import json
from abc import ABC

from libs.base_handler import BaseHandler
from services.agent_service import (register_agent_for_api, get_agent_list_for_api, update_agent_for_api,
                                    set_asset_server_id_for_api, opt_obj as opt_obj_agent)

class AgentHandler(BaseHandler, ABC):

    def post(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = register_agent_for_api(**data)
        return self.write(res)

    def get(self):
        res = get_agent_list_for_api(**self.params)
        return self.write(res)

    def delete(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = opt_obj_agent.handle_delete(data)
        self.write(res)

    def put(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = update_agent_for_api(data)
        self.write(res)

    def patch(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = set_asset_server_id_for_api(data)
        self.write(res)


    

agent_urls = [
    (r"/api/v2/cmdb/agent/", AgentHandler, {"handle_name": "配置平台-资源管理-agent", "method": ["ALL"]}),
]

    