#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/5/10 17:35
# @Author  : Fred Yangxiaofei
# @File    : res_get_test.py.py
# @Role    : 说明脚本功能


import requests


res = requests.get('http://www.qq.com/')
print(res.url)
print(res.status_code)