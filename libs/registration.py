#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2018/11/1 17:07
Desc    : 注册信息到管控平台
"""

import json
from websdk2.client import AcsClient
from websdk2.configs import configs
from settings import settings

if configs.can_import: configs.import_dict(**settings)
client = AcsClient()

uri = "/api/mg/v3/accounts/authority/register/"

menu_list = []
component_list = []
func_list = []
role_list = []

method_dict = dict(
    ALL="管理C",
    GET="查看C",
)


def registration_to_paas():
    app_code = "cmdb"
    api_info_url = f"/backend/cmdb/v1/probe/meta/urls/"
    func_info = client.do_action_v2(**dict(
        method='GET',
        url=api_info_url,
    ))
    if func_info.status_code == 200:
        temp_func_list = func_info.json().get('data')
        func_list.append(dict(method_type='ALL', name=f"{app_code}-管理员", uri=f"/backend/cmdb/*"))
        func_list.append(dict(method_type='GET', name=f"{app_code}-查看所有", uri=f"/backend/cmdb/*"))
        for f in temp_func_list:
            if 'name' not in f or f.get('name') == '暂无': continue
            for m, v in method_dict.items():
                func = dict(method_type=m, name=f"{v}-{f['name']}", uri=f"/backend/cmdb{f.get('url')}")
                if f.get('status') == 'y':  func['status'] = '0'
                func_list.append(func)

    body = {
        "app_code": app_code,
        "menu_list": menu_list,
        "component_list": component_list,
        "func_list": func_list,
        "role_list": role_list
    }
    registration_data = dict(method='POST',
                             url=uri,
                             body=json.dumps(body),
                             description='自动注册')
    response = client.do_action(**registration_data)
    print(json.loads(response))
    return response


class Registration:
    def __init__(self, **kwargs):
        pass

    def start_server(self):
        registration_to_paas()
        raise Exception('初始化完成')
