#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/3/15 14:59
Desc    : 云区域管理
"""

import json
from abc import ABC
from services.cloud_region_service import get_cloud_region, preview_cloud_region, opt_obj, relevance_asset, \
    del_relevance_asset, \
    get_cloud_region_from_id, add_cloud_region_for_api, put_cloud_region_for_api, preview_cloud_region_v2
from libs.base_handler import BaseHandler
from libs.mycrypt import MyCrypt

mc = MyCrypt()


class CloudRegionListHandlers(BaseHandler, ABC):
    def get(self):
        res = get_cloud_region(**self.params)
        return self.write(res)


class CloudRegionHandlers(BaseHandler, ABC):
    def get(self):
        res = get_cloud_region(**self.params)
        return self.write(res)

    def post(self):
        data = json.loads(self.request.body.decode("utf-8"))
        ssh_key = data.get('ssh_key')
        if ssh_key and ssh_key.startswith('-----'):
            data['ssh_key'] = mc.my_encrypt(ssh_key)
        # res = opt_obj.handle_add(data)
        res = add_cloud_region_for_api(data)
        return self.write(res)

    def put(self):
        # 编辑
        data = json.loads(self.request.body.decode("utf-8"))
        ssh_key = data.get('ssh_key')
        if ssh_key and ssh_key.startswith('-----'):
            data['ssh_key'] = mc.my_encrypt(ssh_key)
        # res = opt_obj.handle_update(data)
        res = put_cloud_region_for_api(data)
        return self.write(res)

    def patch(self):
        # 关联
        data = json.loads(self.request.body.decode("utf-8"))
        res = relevance_asset(data)
        return self.write(res)

    def delete(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = opt_obj.handle_delete(data)
        return self.write(res)


class CloudRegionPreHandlers(BaseHandler, ABC):

    def get(self):
        res = preview_cloud_region_v2(**self.params)
        return self.write(res)


class CloudRegionProHandlers(BaseHandler, ABC):
    def get(self):
        # 根据资产ID查询 后续根据需求再拓展
        res = get_cloud_region_from_id(**self.params)
        return self.write(res)

    def delete(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = del_relevance_asset(data)
        return self.write(res)


cloud_region_urls = [
    (r"/api/v2/cmdb/cloud_region/", CloudRegionHandlers, {"handle_name": "配置平台-业务-云区域管理", "method": ["ALL"]}),
    (r"/api/v2/cmdb/cloud_region/list/", CloudRegionListHandlers,
     {"handle_name": "配置平台-业务-云区域查看", "method": ["GET"]}),
    (r"/api/v2/cmdb/cloud_region/pro/", CloudRegionProHandlers,
     {"handle_name": "配置平台-业务-云区域管理解绑反查", "method": ["ALL"]}),
    (r"/api/v2/cmdb/cloud_region/preview/", CloudRegionPreHandlers,
     {"handle_name": "配置平台-业务-云区域主机预览", "method": ["GET"]}),
]
