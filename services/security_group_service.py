#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2021/1/27 11:02
Desc    : 解释一下吧
"""

import json
from sqlalchemy import or_
from websdk2.sqlalchemy_pagination import paginate
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.model_utils import CommonOptView
from models.asset import SecurityGroupModels

opt_obj = CommonOptView(SecurityGroupModels)


def _get_value(value: str = None):
    if not value:
        return True
    return or_(
        SecurityGroupModels.security_group_name.like(f'%{value}%'),
        SecurityGroupModels.security_group_type.like(f'%{value}%'),
        SecurityGroupModels.security_info.like(f'%{value}%'),
        SecurityGroupModels.description.like(f'%{value}%'),
    )


def _get_ids(ids: list):
    if not ids:
        return True
    return or_(
        SecurityGroupModels.instance_id.in_(ids)
    )


def get_security_group_for_api(**params) -> dict:
    value = params.get('searchValue') if "searchValue" in params else params.get('searchVal')
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    sg_ids = params.pop('sg_ids') if "sg_ids" in params else []
    if sg_ids and isinstance(sg_ids, str): sg_ids = json.loads(sg_ids)
    if 'biz_id' in filter_map: filter_map.pop('biz_id')  # 暂时不隔离
    if 'page_size' not in params: params['page_size'] = 300  # 默认获取到全部数据
    with DBContext('r') as session:
        page = paginate(
            session.query(SecurityGroupModels).filter(_get_ids(sg_ids), _get_value(value)).filter_by(**filter_map),
            **params)
    return dict(msg='获取成功', code=0, data=page.items, count=page.total)
