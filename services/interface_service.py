# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/8/21
# @Description: Description

from typing import Iterable
import json

from websdk2.configs import configs
from websdk2.cache_context import cache_conn

from settings import settings

if configs.can_import: configs.import_dict(**settings)

CACHED_KEY = 'INTERFACES'


def get_interfaces():
    """
    公司网络出口IP地址列表
    """
    try:
        cache = cache_conn()
        cached_data = cache.get(CACHED_KEY)
        if not cached_data:
            interfaces = []
        else:
            interfaces = json.loads(cached_data)
        return dict(code=0, msg='获取成功', data=interfaces)
    except Exception as e:
        return dict(code=-1, msg='获取失败', data=[])


def update_interfaces(data: [Iterable[str]]):
    """
    更新公司网络出口IP地址列表
    """
    try:
        ips = data.get("data")
        if not ips:
            return dict(code=-1, msg='更新失败，IP地址不能为空')
        cache = cache_conn()
        interfaces = json.dumps(list(set(ips)))
        cache.set(CACHED_KEY, interfaces)
        return dict(code=0, msg='更新成功')
    except Exception as e:
        return dict(code=-1, msg='更新失败')
