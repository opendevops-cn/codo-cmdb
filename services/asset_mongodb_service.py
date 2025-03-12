# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2025/3/12
# @Description: MongoDB服务


from sqlalchemy import or_, cast, String
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.sqlalchemy_pagination import paginate
from websdk2.model_utils import CommonOptView

from models.asset import AssetMongoModels

opt_obj = CommonOptView(AssetMongoModels)

def _get_mongodb_by_filter(search_filter: str = None):
    """过滤筛选"""
    if not search_filter:
        return [True]

    query_filter_map = {
        "is_normal": [AssetMongoModels.is_expired == False],
        "is_expired": [AssetMongoModels.is_expired == True],
        "is_showdown": [AssetMongoModels.state == "关机"],
    }
    return [*query_filter_map.get(search_filter, [])]


def _get_mongodb_by_val(search_val: str = None):
    """模糊查询"""
    if not search_val:
        return True

    return or_(
        AssetMongoModels.name.like(f'%{search_val}%'),
        AssetMongoModels.instance_id.like(f'%{search_val}%'),
        AssetMongoModels.region.like(f'%{search_val}%'),
        AssetMongoModels.zone.like(f'%{search_val}%'),
        AssetMongoModels.db_class.like(f'%{search_val}%'),
        AssetMongoModels.db_version.like(f'%{search_val}%'),
    )


def _get_mongodb_by_address_like(search_address: str = None):
    """根据地址模糊查询"""
    if not search_address:
        return True

    return cast(AssetMongoModels.db_address, String).like(f'%{search_address}%')


def get_mongodb_list_for_api(**params) -> dict:
    value = params.get('searchValue') if "searchValue" in params else params.get('searchVal')
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'page_size' not in params: params['page_size'] = 300  # 默认获取到全部数据
    search_filter = params.get('search_filter', None)
    search_address = params.get('search_address', '')
    with DBContext('r') as session:
        page = paginate(
            session.query(AssetMongoModels).filter(*_get_mongodb_by_filter(search_filter), _get_mongodb_by_val(value),
                                                   _get_mongodb_by_address_like(search_address)).filter_by(
                **filter_map),
            **params)
    return dict(code=0, msg='获取成功', data=page.items, count=page.total)

def delete_mongodb():
    pass
