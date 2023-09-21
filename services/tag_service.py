#!/usr/bin/env python
# -*- coding: utf-8 -*-
""""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023年2月5日
Desc    : TAG 逻辑处理
"""

from sqlalchemy import or_
from typing import *
from websdk2.db_context import DBContextV2 as DBContext
from models.tag import TagModels
from websdk2.sqlalchemy_pagination import paginate


def _get_by_key(tag_key: str = None):
    """模糊查询"""
    if not tag_key:
        return True
    return or_(
        TagModels.tag_key == tag_key
    )


def _get_by_val(val: str = None):
    """模糊查询"""
    if not val:
        return True
    return or_(
        TagModels.tag_key.like(f'%{val}%'),
        TagModels.tag_value.like(f'%{val}%'),
        TagModels.tag_detail.like(f'%{val}%'),
        TagModels.id == val,
    )

