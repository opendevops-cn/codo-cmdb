#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/3/27 11:02
Desc    : 动态分组API
"""

import json
from abc import ABC
from libs.base_handler import BaseHandler
from services.dynamic_group_service import get_dynamic_group, opt_obj, preview_dynamic_group_for_api, \
    update_dynamic_group_for_api, add_dynamic_group_for_api, get_dynamic_group_for_use_api


class DynamicGroupHandlers(BaseHandler, ABC):
    def get(self):
        res = get_dynamic_group(**self.params)
        return self.write(res)

    def post(self):
        data = json.loads(self.request.body.decode("utf-8"))
        data['modify_user'] = self.request_fullname()
        res = add_dynamic_group_for_api(data)
        return self.write(res)

    def put(self):
        # 更新 分组名称+分组类型+查询条件+备注信息+自动关联
        data = json.loads(self.request.body.decode("utf-8"))
        data['modify_user'] = self.request_fullname()
        res = update_dynamic_group_for_api(data)
        return self.write(res)

    def delete(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = opt_obj.handle_delete(data)

        return self.write(res)


class DynamicGroupListHandlers(BaseHandler, ABC):
    def get(self):
        res = get_dynamic_group_for_use_api(**self.params)
        return self.write(res)


class PreviewHostHandler(BaseHandler, ABC):
    """
    预览动态分组主机
    """

    def get(self):
        exec_uuid = self.get_argument('exec_uuid')
        if not exec_uuid:
            return self.write({"code": 1, "msg": "节点UUID不能为空", "data": []})

        exec_uuid_list = exec_uuid.split(',')
        res = preview_dynamic_group_for_api(exec_uuid_list)
        return self.write(res)
        # res_list = []
        # with DBContext('r') as session:
        #     for exec_id in exec_uuid_list:
        #         group_info = session.query(DynamicGroupModels).filter(
        #             DynamicGroupModels.exec_uuid == exec_id
        #         ).first()
        #         if not group_info:
        #             return self.write({"code": 1, "msg": "groupID不存在"})
        #         # 获取主机信息
        #         is_success, result = get_dynamic_hosts(model_to_dict(group_info))
        #         if not is_success:
        #             return self.write({"code": 1, "msg": result, "data": []})
        #
        #         if not result:
        #             return self.write({"code": 0, "msg": "没有发现主机信息", "data": []})
        #
        #         res_list.extend(result)
        # __count = len(res_list)
        # return self.write({"code": 0, "msg": "获取主机信息完成", "count": __count, "data": res_list})


dynamic_group_urls = [
    (r"/api/v2/cmdb/biz/dynamic_group/", DynamicGroupHandlers, {"handle_name": "CMDB-动态分组", "handle_status": "y"}),
    (r"/api/v2/cmdb/biz/dynamic_group/list/", DynamicGroupListHandlers, {"handle_name": "CMDB-动态分组列表"}),
    (r"/api/v2/cmdb/biz/dynamic_group/preview/", PreviewHostHandler, {"handle_name": "CMDB-动态分组预览",
                                                                      "handle_status": "y"}),
]
