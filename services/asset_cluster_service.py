# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2025/3/12
# @Description: 集群服务


from sqlalchemy import or_
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.model_utils import CommonOptView
from websdk2.sqlalchemy_pagination import paginate

from models.asset import AssetClusterModels

opt_obj = CommonOptView(AssetClusterModels)


def _get_cluster_by_val(search_val: str = None):
    """模糊查询"""
    if not search_val:
        return True

    return or_(
        AssetClusterModels.id == search_val,
        AssetClusterModels.instance_id == search_val,
        AssetClusterModels.name == search_val,
        AssetClusterModels.cloud_name.like(f'%{search_val}%'),
        AssetClusterModels.name.like(f'%{search_val}%'),
        AssetClusterModels.description.like(f'%{search_val}%'),
        AssetClusterModels.state.like(f'%{search_val}%'),
        AssetClusterModels.vpc_id.like(f'%{search_val}%'),
        AssetClusterModels.inner_ip.like(f'%{search_val}%'),
        AssetClusterModels.outer_ip.like(f'%{search_val}%'),
        AssetClusterModels.cidr_block_v4.like(f'%{search_val}%'),
        AssetClusterModels.version.like(f'%{search_val}%'),
    )


def get_cluster_list_for_api(**params) -> dict:
    value = params.get('searchValue') if "searchValue" in params else params.get('searchVal')
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'page_size' not in params: params['page_size'] = 300  # 默认获取到全部数据
    with DBContext('r') as session:
        page = paginate(session.query(AssetClusterModels).filter(_get_cluster_by_val(value),
                                                                 ).filter_by(**filter_map), **params)
    return dict(code=0, msg='获取成功', data=page.items, count=page.total)
