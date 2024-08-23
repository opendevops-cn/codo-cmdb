# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/8/21
# @Description: Description

import json
from abc import ABC
from libs.base_handler import BaseHandler
from services.interface_service import get_interfaces, update_interfaces


class InterfaceHandler(BaseHandler, ABC):
    def get(self):
        res = get_interfaces()
        return self.write(res)

    def put(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = update_interfaces(data)
        self.write(res)


interface_urls = [
    (r"/api/v2/interface/", InterfaceHandler, {"handle_name": "配置平台-内部-公司网络出口", "method": ["ALL"]}),
]
