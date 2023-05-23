#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/1/27 11:02
Desc    : 资产类型MySQL处理逻辑
"""

from sqlalchemy import or_
from typing import *
from websdk2.db_context import DBContextV2 as DBContext
from models.asset import AssetMySQLModels
from websdk2.sqlalchemy_pagination import paginate
from websdk2.model_utils import CommonOptView

opt_obj = CommonOptView(AssetMySQLModels)


def _models_to_list(server_info: List[AssetMySQLModels]) -> List[dict]:
    """模型转换,格式处理"""
    server_list: List[dict] = []
    for data_dict in server_info:
        update_data = data_dict['ext_info']
        update_data = {} if not update_data else update_data
        data_dict.pop('ext_info')
        data_dict.update(update_data)
        server_list.append(data_dict)
    return server_list


def _get_mysql_by_filter(search_filter: str = None):
    """过滤筛选"""
    if not search_filter:
        return [True]

    query_filter_map = {
        "is_normal": [AssetMySQLModels.is_expired == False],
        "is_expired": [AssetMySQLModels.is_expired == True],
        "is_showdown": [AssetMySQLModels.state == "关机"],
    }
    return [*query_filter_map.get(search_filter, [])]


def _get_mysql_by_val(search_val: str = None):
    """模糊查询"""
    if not search_val:
        return True

    return or_(
        AssetMySQLModels.name.like(f'%{search_val}%'),
        AssetMySQLModels.instance_id.like(f'%{search_val}%'),
        AssetMySQLModels.region.like(f'%{search_val}%'),
        AssetMySQLModels.zone.like(f'%{search_val}%'),
        AssetMySQLModels.db_class.like(f'%{search_val}%'),
        AssetMySQLModels.db_engine.like(f'%{search_val}%'),
    )


def _get_mysql_by_address_like(search_address: str = None):
    """根据地址模糊查询"""
    if not search_address:
        return True

    return AssetMySQLModels.db_address.like(f'%{search_address}%')


def get_mysql_list_for_api(**params) -> dict:
    value = params.get('searchValue') if "searchValue" in params else params.get('searchVal')
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'page_size' not in params: params['page_size'] = 300  # 默认获取到全部数据
    search_filter = params.get('search_filter', None)
    search_address = params.get('search_address', '')
    with DBContext('r') as session:
        page = paginate(
            session.query(AssetMySQLModels).filter(*_get_mysql_by_filter(search_filter), _get_mysql_by_val(value),
                                                   _get_mysql_by_address_like(search_address)).filter_by(**filter_map),
            **params)
        data = _models_to_list(page.items)
    return dict(code=0, msg='获取成功', data=data, count=page.total)
