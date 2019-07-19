#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/7/12 9:39
# @Author  : Fred Yangxiaofei
# @File    : multi_hosts.py
# @Role    : API批量添加主机

import json
import requests


def add_host():
    add_user_url = 'https://codo.domain.com/api/cmdb2/v1/cmdb/server/'
    csrf_task_url = 'https://codo.domain.com/api/task/v2/task/accept/'

    # 这里就是一个长期Token，管理员可以在用户列表选择一个用户进行生成一个长期Token
    auth_key = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9nVzZXJuYW1lIjoieWFuZ2gFPLN6g"

    the_body = json.dumps({
        "hostname": 'hostname',
        "ip": "1.1.1.1",
        "port": "22",
        "public_ip": "2.2.2.2",
        "idc": "AWS",
        "admin_user": "root",
        "region": "us-east-1",
    })

    req1 = requests.get(csrf_task_url, cookies=dict(auth_key=auth_key))
    csrf_key = json.loads(req1.text)['csrf_key']
    cookies = dict(auth_key=auth_key, csrf_key=csrf_key)
    req = requests.post(add_user_url, data=the_body, cookies=cookies)
    req_code = json.loads(req.text)['code']
    if req_code != 0:
        print(json.loads(req.text)['msg'])
        exit(-111)
    else:
        print(json.loads(req.text)['msg'])


if __name__ == '__main__':
    add_host()
