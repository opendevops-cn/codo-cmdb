#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: shenshuo
Since: 2023/2/12 15:10
Description: 集群模板
"""

import json
from abc import ABC
from libs.base_handler import BaseHandler
from services.set_temp_service import set_temp_batch, opt_obj, get_temp_list


class SetTempHandler(BaseHandler, ABC):
    def get(self):
        return self.write(get_temp_list(**self.params))

    def post(self):
        data = json.loads(self.request.body.decode("utf-8"))
        temp_name = data.get('temp_name')
        temp_items = data.get('items')
        header_username = self.request.headers.get('Username')
        create_user = header_username if header_username else 'admin'

        if not isinstance(temp_items, list):
            return self.write({"code": 1, "msg": "模块类型错误"})

        # 处理 0表示前端标记删除
        temp_items = list(filter(lambda rule: rule["status"] == 1, temp_items))
        if not temp_items:
            return self.write({"code": 1, "msg": "模块不能为空"})

        res = opt_obj.handle_add(dict(temp_name=temp_name, temp_data={"items": temp_items}, create_user=create_user))
        return self.write(res)

    def put(self):
        data = json.loads(self.request.body.decode("utf-8"))
        temp_id = data.get('id')
        temp_name = data.get('temp_name')
        temp_items = data.get('items')
        header_username = self.request.headers.get('Username')
        create_user = header_username if header_username else 'admin'

        if not isinstance(temp_items, list):
            return self.write({"code": 1, "msg": "模块类型错误"})

        # 处理 0表示前端标记删除
        temp_items = list(filter(lambda rule: rule["status"] == 1, temp_items))
        if not temp_items:
            return self.write({"code": 1, "msg": "模块不能为空"})

            # 换成Json存数据库
        res = opt_obj.handle_update(
            dict(id=temp_id, temp_name=temp_name, temp_data={"items": temp_items}, create_user=create_user))

        return self.write(res)

    def delete(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = opt_obj.handle_delete(data)
        return self.write(res)


class SetTempAPPHandler(BaseHandler, ABC):
    def post(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = set_temp_batch(data)
        return self.write(res)


template_urls = [
    (r"/api/v2/cmdb/biz/set_temp/", SetTempHandler, {"handle_name": "配置平台-业务-集群模板", "method": ["ALL"]}),
    (r"/api/v2/cmdb/biz/set_temp/batch/", SetTempAPPHandler,
     {"handle_name": "配置平台-业务-批量使用集群模板", "method": ["ALL"]}),
]
