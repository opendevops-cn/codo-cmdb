#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 2023/10/30 20:58
# @Author  : harilou
# @Describe: 通用方法
from datetime import datetime
import types
from functools import wraps
import traceback


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
            print(f'call function {self.__name__} error. args: {args}, kwargs: {kwargs}, msg: {traceback.format_exc()}')

    def __get__(self, instance, cls):
        if instance is None:
            return self
        else:
            return types.MethodType(self, instance)


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