#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# @File    :   asset_nat_service.py
# @Time    :   2024/10/14 10:09:52
# @Author  :   DongdongLiu
# @Version :   1.0
# @Desc    :   NAT网关Service


from sqlalchemy import or_, func
from typing import *
from websdk2.db_context import DBContextV2 as DBContext
from models.asset import AssetNatModels
from websdk2.sqlalchemy_pagination import paginate
from websdk2.model_utils import CommonOptView

opt_obj = CommonOptView(AssetNatModels)

def _get_nat_by_val(search_val: str = None):
    """模糊查询"""
    if not search_val:
        return True

    return or_(
        AssetNatModels.id == search_val,
        AssetNatModels.instance_id == search_val,
        AssetNatModels.name == search_val,
        AssetNatModels.cloud_name.like(f'%{search_val}%'),
        AssetNatModels.name.like(f'%{search_val}%'),
        AssetNatModels.spec.like(f'%{search_val}%'),
        AssetNatModels.charge_type.like(f'%{search_val}%'),
        AssetNatModels.network_type.like(f'%{search_val}%'),
        AssetNatModels.network_interface_id.like(f'%{search_val}%'),
        AssetNatModels.description.like(f'%{search_val}%'),
        AssetNatModels.state.like(f'%{search_val}%'),
        AssetNatModels.vpc_id.like(f'%{search_val}%'),
        func.json_extract(AssetNatModels.outer_ip, '$[*]').like(f'%{search_val}%')
    )


def get_nat_list_for_api(**params) -> dict:
    value = params.get('searchValue') if "searchValue" in params else params.get('searchVal')
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'page_size' not in params: params['page_size'] = 300  # 默认获取到全部数据
    with DBContext('r') as session:
        page = paginate(session.query(AssetNatModels).filter(_get_nat_by_val(value),
                                                       ).filter_by(**filter_map), **params)
    return dict(code=0, msg='获取成功', data=page.items, count=page.total)