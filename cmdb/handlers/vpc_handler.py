#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date   : 2023-2-08
Desc   : 虚拟局域网 API
"""

import json
from shortuuid import uuid
from abc import ABC
from libs.base_handler import BaseHandler
from services.asset_vswitch_service import get_vswitch_list_for_api, opt_obj, update_field
from services.asset_vpc_service import opt_obj as opt_obj_vpc, get_vpc_list_for_api


class AssetVPCHandler(BaseHandler, ABC):
    def get(self):
        res = get_vpc_list_for_api(**self.params)
        return self.write(res)

    def delete(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = opt_obj_vpc.handle_delete(data)
        self.write(res)


class AsseVswitchHandler(BaseHandler, ABC):
    def get(self):
        res = get_vswitch_list_for_api(**self.params)
        return self.write(res)

    def post(self):
        data = json.loads(self.request.body.decode("utf-8"))
        if 'account_id' not in data: data['account_id'] = uuid(name='手工录入')
        if 'instance_id' not in data: data['instance_id'] = uuid(name=data['name'])
        if 'vpc_id' not in data: data['vpc_id'] = data['vpc_name']
        if 'region' not in data: data['region'] = 'intranet'
        res = opt_obj.handle_add(data)
        self.write(res)

    def patch(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = update_field(data)
        self.write(res)

    def delete(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = opt_obj.handle_delete(data)
        self.write(res)


vpc_urls = [
    (r"/api/v2/cmdb/vpc/", AssetVPCHandler, {"handle_name": "CMDB-云商-虚拟局域网管理", "method": ["ALL"]}),
    (r"/api/v2/cmdb/vswitch/", AsseVswitchHandler, {"handle_name": "CMDB-云商-虚拟子网管理", "method": ["ALL"]}),
]
