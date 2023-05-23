#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/1/27 11:02
Desc    : 资产类型虚拟子网处理逻辑
"""

from sqlalchemy import or_
from typing import *
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.sqlalchemy_pagination import paginate
from websdk2.model_utils import CommonOptView
from models.asset import AssetVPCModels

opt_obj = CommonOptView(AssetVPCModels)


def _get_vpc_by_val(value: str = None):
    """模糊查询"""
    if not value:
        return True

    return or_(
        AssetVPCModels.vpc_name.like(f'%{value}%'),
        AssetVPCModels.instance_id.like(f'%{value}%'),
        AssetVPCModels.region.like(f'%{value}%'),
        AssetVPCModels.vpc_switch.like(f'%{value}%'),
        AssetVPCModels.cidr_block_v4.like(f'%{value}%'),
        AssetVPCModels.cidr_block_v6.like(f'%{value}%'),
    )


def get_vpc_list_for_api(**params) -> dict:
    value = params.get('searchValue') if "searchValue" in params else params.get('searchVal')
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'page_size' not in params: params['page_size'] = 300  # 默认获取到全部数据
    with DBContext('r') as session:
        page = paginate(session.query(AssetVPCModels).filter(_get_vpc_by_val(value),
                                                             ).filter_by(**filter_map), **params)
    return dict(code=0, msg='获取成功', data=page.items, count=page.total)
