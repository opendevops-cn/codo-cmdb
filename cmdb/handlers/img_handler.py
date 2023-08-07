#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023-2-08
Desc    : 系统镜像API
"""

import json
from abc import ABC
from libs.base_handler import BaseHandler
from services.asset_img_service import opt_obj as opt_obj_img, get_img_list_for_api


class AssetImgHandler(BaseHandler, ABC):
    def get(self):
        res = get_img_list_for_api(**self.params)
        return self.write(res)

    def delete(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = opt_obj_img.handle_delete(data)
        self.write(res)


img_urls = [
    (r"/api/v2/cmdb/img/", AssetImgHandler, {"handle_name": "CMDB-系统镜像", "handle_status": "y"}),
]
