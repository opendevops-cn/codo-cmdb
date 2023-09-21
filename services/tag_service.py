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


def get_tag_list_by_key(**params) -> dict:
    value = params.get('searchValue') if "searchValue" in params else params.get('searchVal')
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'page_size' not in params: params['page_size'] = 300  # 默认获取到全部数据
    tag_key = params.get('tag_key')
    with DBContext('r') as session:
        page = paginate(session.query(TagModels).filter(_get_by_key(tag_key), _get_by_val(value)).filter_by(
            **filter_map), **params)

    return dict(code=0, msg='获取成功', data=page.items, count=page.total)


def get_tag_list(**params) -> dict:
    tag_key = params.get('tag_key', None)
    with DBContext('r') as session:
        if tag_key:
            tag_info = session.query(TagModels.tag_value).filter(TagModels.tag_key == tag_key
                                                                 ).group_by(TagModels.tag_value).all()
        else:
            tag_info = session.query(TagModels.tag_key).group_by(TagModels.tag_key).all()
    tag_data = [i[0] for i in tag_info] if tag_info else []

    return dict(code=0, msg='获取成功', data=tag_data, count=len(tag_data))
