#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/1/27 11:02
Desc    : 资产类型虚拟子网处理逻辑
"""

from sqlalchemy import or_, desc
from typing import *
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.sqlalchemy_pagination import paginate
from websdk2.model_utils import CommonOptView
from models.asset import AssetVSwitchModels

opt_obj = CommonOptView(AssetVSwitchModels)


def _get_vswitch_by_filter(search_filter: str = None):
    """过滤筛选"""
    if not search_filter:
        return [True]

    query_filter_map = {
        "is_normal": [AssetVSwitchModels.is_expired == False],
        "is_expired": [AssetVSwitchModels.is_expired == True]
    }
    return [*query_filter_map.get(search_filter, [])]


def _get_vswitch_by_cloud(cloud_type: str = None):
    """过滤筛选"""
    if not cloud_type:
        return True
    if cloud_type == 'neiwang':
        return or_(
            AssetVSwitchModels.cloud_name == "neiwang"
        )
    else:
        return or_(
            AssetVSwitchModels.cloud_name != "neiwang"
        )


def _get_vswitch_is_default(is_not_default: str = None):
    """过滤筛选"""
    if not is_not_default:
        return True
    if is_not_default == 'true' or is_not_default is True:
        return or_(
            AssetVSwitchModels.is_default == False
        )
    else:
        return True


def _get_vswitch_by_val(value: str = None):
    """模糊查询"""
    if not value:
        return True

    return or_(
        AssetVSwitchModels.name.like(f'%{value}%'),
        AssetVSwitchModels.instance_id.like(f'%{value}%'),
        AssetVSwitchModels.vpc_id.like(f'%{value}%'),
        AssetVSwitchModels.vpc_name.like(f'%{value}%'),
        AssetVSwitchModels.region.like(f'%{value}%'),
        AssetVSwitchModels.cidr_block_v4.like(f'%{value}%'),
        AssetVSwitchModels.cidr_block_v6.like(f'%{value}%'),
        AssetVSwitchModels.route.like(f'%{value}%'),
        AssetVSwitchModels.route_id.like(f'%{value}%'),
        AssetVSwitchModels.description.like(f'%{value}%'),
    )


def get_vswitch_list_for_api(**params) -> dict:
    value = params.get('searchValue') if "searchValue" in params else params.get('searchVal')
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'page_size' not in params: params['page_size'] = 300  # 默认获取到全部数据
    is_not_default = params.get('is_not_default', 'all')  # 通过页面默认获取非默认数据，不加参数获取全部
    cloud_type = params.get('cloud_type', None)
    with DBContext('r') as session:
        page = paginate(session.query(AssetVSwitchModels).filter(_get_vswitch_by_cloud(cloud_type),
                                                                 _get_vswitch_is_default(is_not_default),
                                                                 _get_vswitch_by_val(value),
                                                                 ).filter_by(**filter_map), **params)
    return dict(code=0, msg='获取成功', data=page.items, count=page.total)


def update_field(data: dict) -> dict:
    sid = data.get('id')
    if not sid or not isinstance(sid, int):
        return dict(code=-1, msg='格式错误，id_list 不能为空')
    cloud_region_id = data.get('cloud_region_id')

    if not cloud_region_id or not isinstance(cloud_region_id, str):
        return dict(code=-1, msg='格式错误，云区域ID 不能为空')

    new_data = {'cloud_region_id': cloud_region_id}
    with DBContext('w', None, True) as session:
        session.query(AssetVSwitchModels).filter(AssetVSwitchModels.id == sid).update(new_data)
    return dict(code=0, msg=f"修改成功")
