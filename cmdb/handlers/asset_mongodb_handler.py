# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2025/3/12
# @Description: MongoDB入口
import json
from abc import ABC

from libs.base_handler import BaseHandler
from services.asset_mongodb_service import get_mongodb_list_for_api, opt_obj as opt_obj_mongodb


class MongoDBHandler(BaseHandler, ABC):
    def get(self):
        res = get_mongodb_list_for_api(**self.params)
        self.write(res)

    def delete(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = opt_obj_mongodb.handle_delete(data)
        self.write(res)


mongodb_urls = [
    (
        r"/api/v2/cmdb/mongodb/",
        MongoDBHandler,
        {"handle_name": "配置平台-云商-MongoDB管理", "method": ["ALL"]},
    ),
]
