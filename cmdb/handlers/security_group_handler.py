#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/2/15 14:59
Desc    : 安全组API
"""

import json
from abc import ABC
from libs.base_handler import BaseHandler

from services.security_group_service import opt_obj, get_security_group_for_api
from services.asset_server_service import get_server_for_security_group


class SecurityGroupHandler(BaseHandler, ABC):
    def get(self):
        res = get_security_group_for_api(**self.params)
        return self.write(res)

    # def post(self):
    #     data = json.loads(self.request.body.decode("utf-8"))
    #     res = opt_obj.handle_add(data)
    #     return self.write(res)

    # def put(self):
    #     data = json.loads(self.request.body.decode("utf-8"))
    #     res = opt_obj.handle_update(data)
    #     return self.write(res)

    def delete(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = opt_obj.handle_delete(data)
        return self.write(res)


class SecurityGroupRefsHandler(BaseHandler, ABC):
    def get(self):
        sg_id = self.params.get('sg_id')
        asset_type = self.params.get('asset_type', 'server')
        if asset_type == 'server':
            res = get_server_for_security_group(sg_id)
            return self.write(res)

        return self.write(dict(code=-1, msg='类型错误'))


security_group_urls = [
    (r"/api/v2/cmdb/security_group/", SecurityGroupHandler, {"handle_name": "cmdb-安全组", "handle_status": "y"}),
    (r"/api/v2/cmdb/security_group/refs/", SecurityGroupRefsHandler, {"handle_name": "cmdb-安全组-关联资源"}),
]
