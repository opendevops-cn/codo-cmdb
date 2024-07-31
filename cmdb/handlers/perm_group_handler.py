# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/4/30
# @Description: 权限分组管理
import asyncio
import json
from abc import ABC
import tornado.ioloop

from libs.base_handler import BaseHandler
from services.perm_group_service import (add_perm_group_for_api, opt_obj, get_perm_group_list_for_api,
                                         preview_perm_group_for_api, update_perm_group_for_api)
from libs.sync_utils_set import sync_cmdb_to_jms_with_enterprise


class PermGroupHandler(BaseHandler, ABC):

    def post(self):
        data = json.loads(self.request.body.decode("utf-8"))
        data['modify_user'] = self.request_fullname()
        res = add_perm_group_for_api(data)
        self.write(res)

    def get(self):
        res = get_perm_group_list_for_api(**self.params)
        return self.write(res)

    def delete(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = opt_obj.handle_delete(data)
        self.write(res)

    def put(self):
        # 编辑
        data = json.loads(self.request.body.decode("utf-8"))
        data['modify_user'] = self.request_fullname()
        res = update_perm_group_for_api(data)
        return self.write(res)


class PreviewHostHandler(BaseHandler, ABC):
    """
    预览权限分组主机
    """

    def get(self):
        exec_uuid = self.get_argument('exec_uuid')
        if not exec_uuid:
            return self.write({"code": 1, "msg": "节点UUID不能为空", "data": []})

        exec_uuid_list = exec_uuid.split(',')
        res = preview_perm_group_for_api(exec_uuid_list)
        return self.write(res)


class SyncPermGroupHandler(BaseHandler, ABC):
    """
    同步权限分组到JMS
    """

    async def post(self):
        data = json.loads(self.request.body.decode("utf-8"))
        asyncio.create_task(self.run_sync_task(data.get('id')))
        self.write(dict(code=0, msg="同步已发起"))

    @staticmethod
    async def run_sync_task(perm_group_id):
        await tornado.ioloop.IOLoop.current().run_in_executor(None, sync_cmdb_to_jms_with_enterprise,
                                                              perm_group_id, False)


perm_group_urls = [
    (r"/api/v2/cmdb/biz/perm_group/", PermGroupHandler,
     {"handle_name": "配置平台-业务-权限分组管理", "method": ["ALL"]}),
    (r"/api/v2/cmdb/biz/perm_group/preview/", PreviewHostHandler,
     {"handle_name": "配置平台-业务-权限分组预览", "method": ["GET"]}),
    (r"/api/v2/cmdb/biz/perm_group/sync/", SyncPermGroupHandler,
     {"handle_name": "配置平台-业务-权限分组同步", "method": ["POST"]}),
]
