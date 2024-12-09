#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# @File    :   asset_swith_handler.py
# @Time    :   2024/12/05 12:03:09
# @Author  :   DongdongLiu
# @Version :   1.0
# @Desc    :   内网交换机
from abc import ABC
import json

from libs.base_handler import BaseHandler
from services.asset_switch_service import (
    get_switch_list_for_api,
    import_switch,
    opt_obj_switch,
)


class SwitchHandler(BaseHandler, ABC):
    def get(self):
        res = get_switch_list_for_api(**self.params)
        self.write(res)
        
    def delete(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = opt_obj_switch.handle_delete(data)
        self.write(res)
        
class SwitchImportHandler(BaseHandler, ABC):
    def post(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = import_switch(data)
        self.write(res)
        

switch_urls = [
    (
        r"/api/v2/cmdb/switch/",
        SwitchHandler,
        {"handle_name": "配置平台-内网-交换机管理", "method": ["GET"]},
    ),
    (
        r"/api/v2/cmdb/switch/import/",
        SwitchImportHandler,
        {"handle_name": "配置平台-内网-交换机导入", "method": ["POST"]},
    ),
]



