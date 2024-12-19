#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# @File    :   secret.py
# @Time    :   2024/12/19 16:10:29
# @Author  :   DongdongLiu
# @Version :   1.0
# @Desc    :   欢乐剑密钥api入口



import json
from abc import ABC
from libs.base_handler import BaseHandler
from services.secret_service import (
    get_secret_list_for_api,
    add_secret_for_api,
    opt_obj as opt_obj_secret,
)


class SecretHandler(BaseHandler, ABC):
    def get(self):
        res = get_secret_list_for_api(**self.params)
        return self.write(res)

    def delete(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = opt_obj_secret.handle_delete(data)
        self.write(res)

    def post(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = add_secret_for_api(data)
        self.write(res)


secret_urls = [
    (
        r"/api/v2/cmdb/secret/",
        SecretHandler,
        {"handle_name": "配置平台-欢乐剑-密钥", "method": ["ALL"]},
    ),
]