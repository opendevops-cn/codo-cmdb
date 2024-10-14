#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# @File    :   nat_handler.py
# @Time    :   2024/10/14 10:29:28
# @Author  :   DongdongLiu
# @Version :   1.0
# @Desc    :   nat网关API接口



import json
from abc import ABC

from libs.base_handler import BaseHandler
from services.asset_nat_service import opt_obj as opt_obj_nat, get_nat_list_for_api



class NatHandler(BaseHandler, ABC):
    def get(self):
        res = get_nat_list_for_api(**self.params)
        return self.write(res)
    
    def delete(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = opt_obj_nat.handle_delete(data)
        self.write(res)
        
        

nat_urls = [
    (r"/api/v2/cmdb/nat/", NatHandler,
     {"handle_name": "配置平台-云商-NAT管理", "method": ["ALL"]}),
]