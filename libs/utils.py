#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 2023/10/30 20:58
# @Author  : harilou
# @Describe: 通用方法
import time
from datetime import datetime
import types
from functools import wraps
from urllib.parse import urlparse
import socket
from typing import Tuple
from contextlib import contextmanager


def human_date(date=None):
    if date:
        assert isinstance(date, datetime)
    else:
        date = datetime.now()
    return date.strftime('%Y-%m-%d')


class CommonDecorator(object):
    """适用于类方法和普通函数的decorator"""
    def __init__(self, func):
        wraps(func)(self)

    def __call__(self, *args, **kwargs):
        try:
            return self.__wrapped__(*args, **kwargs)
        except Exception as e:
            raise

    def __get__(self, instance, cls):
        if instance is None:
            return self
        else:
            return types.MethodType(self, instance)


@contextmanager
def ctx_timer():
    """计算一段代码的执行时间"""
    start_time = time.perf_counter()
    yield
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    print(f"Time elapsed: {elapsed_time:.2f}s")


def compare_dicts(dict1, dict2):
    """
    比较两个dict
    """
    changes = {
        "added": {},
        "removed": {},
        "changed": {}
    }

    def _compare(d1, d2, path=""):
        # 检查新增和变化的项
        for key in d2:
            new_path = f"{path}.{key}" if path else key
            if key not in d1:
                changes["added"][new_path] = d2[key]
            elif isinstance(d2[key], dict) and isinstance(d1.get(key), dict):
                _compare(d1[key], d2[key], new_path)
            elif d1[key] != d2[key]:
                changes["changed"][new_path] = {"old_value": d1[key], "new_value": d2[key]}
        # 检查删除的项
        for key in d1:
            new_path = f"{path}.{key}" if path else key
            if key not in d2:
                changes["removed"][new_path] = d1[key]

    _compare(dict1, dict2)
    return changes


def check_connection(domain: str) -> Tuple[bool, str]:
    """
    检查连接是否可用

    Args:
        domain: 域名或URL

    Returns:
        Tuple[bool, str]: (是否连接成功, 错误信息)
    """
    try:
        # 解析URL
        parsed_url = urlparse(domain)
        host = parsed_url.netloc or parsed_url.path

        # 如果没有端口号，根据协议添加默认端口
        if ":" not in host:
            if parsed_url.scheme == "https":
                host = f"{host}:443"
            else:
                host = f"{host}:80"

        # 分割主机名和端口
        hostname, port = host.split(":")

        # 创建socket并设置超时
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)  # 2秒超时

        # 尝试连接
        result = sock.connect_ex((hostname, int(port)))
        sock.close()

        if result == 0:
            return True, ""
        else:
            return False, "连接失败"

    except Exception as e:
        return False, f"连接检查失败: {str(e)}"