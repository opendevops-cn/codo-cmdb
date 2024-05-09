# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/4/29
# @Description: 角色

from abc import ABC
from libs.base_handler import BaseHandler
from websdk2.client import AcsClient
from websdk2.api_set import api_set


class RoleHandler(BaseHandler, ABC):

    def get(self):
        client = AcsClient()
        try:
            response = client.do_action(
                **api_set.get_normal_role_list)
        except Exception as err:
            return self.write(dict(code=-1, msg="请求失败", data=[]))

        return self.write(response)


role_urls = [
    (r"/api/v2/cmdb/role/", RoleHandler,
     {"handle_name": "配置平台-角色列表", "method": ["GET"]}),
]
