#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/3/15 14:59
Desc    : 动态规则管理
"""

import json
from abc import ABC
from services.dynamic_rule_service import get_dynamic_rules, get_dynamic_rules_asset, refresh_asset, \
    del_relational_asset, \
    opt_obj
from libs.base_handler import BaseHandler


class DynamicGroupHandlers(BaseHandler, ABC):
    def get(self):
        count, queryset = get_dynamic_rules(**self.params)
        return self.write(dict(code=0, msg="获取成功", count=count, data=queryset))

    def post(self):
        data = json.loads(self.request.body.decode("utf-8"))
        header_username = self.request.headers.get('Username')
        modify_user = header_username if header_username else 'admin'
        data['modify_user'] = modify_user
        res = opt_obj.handle_add(data)
        return self.write(res)

    def put(self):
        # 编辑
        data = json.loads(self.request.body.decode("utf-8"))
        res = opt_obj.handle_update(data)
        return self.write(res)

    def delete(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = opt_obj.handle_delete(data)
        return self.write(res)


class DynamicGroupProHandlers(BaseHandler, ABC):
    """
    动态规则 预览变更,更新
    """

    def get(self):
        res = get_dynamic_rules_asset(**self.params)
        return self.write(res)

    def put(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = refresh_asset(data)
        return self.write(res)

    def delete(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = del_relational_asset(data)
        return self.write(res)


dynamic_rule_urls = [
    (r"/api/v2/cmdb/dynamic_rule/", DynamicGroupHandlers, {"handle_name": "配置平台-业务-动态规则管理", "method": ["ALL"]}),
    (r"/api/v2/cmdb/dynamic_rule/pro/", DynamicGroupProHandlers,
     {"handle_name": "配置平台-业务-动态规则-预览变更,更新,删除关联", "method": ["ALL"]}),
]
