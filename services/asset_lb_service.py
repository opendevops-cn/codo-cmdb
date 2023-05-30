#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/1/27 11:02
Desc    : 资产类型LB处理逻辑
"""

from sqlalchemy import or_
from typing import *
from websdk2.db_context import DBContextV2 as DBContext
from models.tree import TreeAssetModels
from models.asset import AssetLBModels
from websdk2.sqlalchemy_pagination import paginate
from websdk2.model_utils import CommonOptView

opt_obj = CommonOptView(AssetLBModels)


def _get_lb_by_filter(search_filter: str = None):
    """过滤筛选"""
    if not search_filter:
        return [True]
    query_filter_map = {
        "is_normal": [AssetLBModels.is_expired == False],
        "is_expired": [AssetLBModels.is_expired == True],
        "is_alb": [AssetLBModels.type == "alb"],
        "is_slb": [AssetLBModels.type == "slb"],
        "is_nlb": [AssetLBModels.type == "nlb"],
    }
    return [*query_filter_map.get(search_filter, [])]


def _get_lb_by_val(search_val: str = None):
    """模糊查询"""
    if not search_val:
        return True

    return or_(
        AssetLBModels.id == search_val,
        AssetLBModels.lb_vip == search_val,
        AssetLBModels.cloud_name.like(f'%{search_val}%'),
        AssetLBModels.name.like(f'%{search_val}%'),
        AssetLBModels.dns_name.like(f'%{search_val}%'),
        AssetLBModels.endpoint_type.like(f'%{search_val}%'),
        AssetLBModels.instance_id.like(f'%{search_val}%'),
        AssetLBModels.type.like(f'%{search_val}%'),
        AssetLBModels.state.like(f'%{search_val}%'),
    )


def get_lb_list_for_api(**params) -> dict:
    value = params.get('searchValue') if "searchValue" in params else params.get('searchVal')
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'page_size' not in params: params['page_size'] = 300  # 默认获取到全部数据
    search_filter = params.get('search_filter', None)
    with DBContext('r') as session:
        page = paginate(session.query(AssetLBModels).filter(*_get_lb_by_filter(search_filter), _get_lb_by_val(value),
                                                            ).filter_by(**filter_map), **params)
    return dict(code=0, msg='获取成功', data=page.items, count=page.total)
