#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2021/1/27 11:02
Desc    : 解释一下吧
"""

from sqlalchemy import or_
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.sqlalchemy_pagination import paginate
from websdk2.model_utils import CommonOptView, model_to_dict
from models.cloud_region import CloudRegionModels, CloudRegionAssetModels
from models.tree import TreeAssetModels
from models.business import BizModels
from models.asset import AssetServerModels

opt_obj = CommonOptView(CloudRegionModels)


def _get_value(value: str = None):
    if not value:
        return True
    return or_(
        CloudRegionModels.name.like(f'%{value}%'),
        CloudRegionModels.cloud_region_id.like(f'%{value}%'),
        CloudRegionModels.proxy_ip.like(f'%{value}%'),
        CloudRegionModels.ssh_ip.like(f'%{value}%'),
        CloudRegionModels.ssh_port.like(f'%{value}%'),
        CloudRegionModels.state.like(f'%{value}%'),
        CloudRegionModels.detail.like(f'%{value}%')
    )


def get_cloud_region(**params) -> dict:
    value = params.get('searchValue') if "searchValue" in params else params.get('searchVal')
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'biz_id' in filter_map: filter_map.pop('biz_id')  # 暂时不隔离
    if 'page_size' not in params: params['page_size'] = 300  # 默认获取到全部数据
    with DBContext('r') as session:
        page = paginate(session.query(CloudRegionModels).filter(_get_value(value)).filter_by(**filter_map), **params)

    return dict(msg='获取成功', code=0, data=page.items, count=page.total)


def _get_server_value(value: str = None):
    if not value:
        return True
    return or_(
        AssetServerModels.name.like(f'%{value}%'),
        AssetServerModels.inner_ip.like(f'%{value}%'),
        AssetServerModels.instance_id.like(f'%{value}%'),
        AssetServerModels.state.like(f'%{value}%')
    )


def preview_cloud_region(**params) -> dict:
    value = params.get('searchValue') if "searchValue" in params else params.get('searchVal')
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'biz_id' in filter_map: filter_map.pop('biz_id')  # 暂时不隔离
    if 'page_size' not in params: params['page_size'] = 300  # 默认获取到全部数据
    region_id = params.get('region_id')
    if not region_id:
        return dict(code=-1, msg='云区域ID不能为空')

    with DBContext('r') as session:
        exist_info = session.query(CloudRegionAssetModels.asset_id).filter(
            CloudRegionAssetModels.region_id == int(region_id), CloudRegionAssetModels.asset_type == 'server').all()

        asset_id_set = set([i[0] for i in exist_info])

        page = paginate(session.query(AssetServerModels).filter(
            AssetServerModels.id.in_(asset_id_set)).filter(_get_server_value(value)).filter_by(**filter_map),
                        **params)
    return dict(msg='获取成功', code=0, data=page.items, count=page.total)


def get_cloud_region_from_id(**params) -> dict:
    asset_id = params.get('asset_id')
    if not asset_id:
        return dict(code=-1, msg='资产ID不能为空')

    with DBContext('r') as session:
        __info = session.query(CloudRegionModels).outerjoin(
            CloudRegionAssetModels, CloudRegionModels.id == CloudRegionAssetModels.region_id).filter(
            CloudRegionAssetModels.asset_id == asset_id, CloudRegionAssetModels.asset_type == 'server').first()
        if not __info:
            return dict(code=-2, msg='当前资产不存在，或者没有关联云区域')

    return dict(msg='获取成功', code=0, data=model_to_dict(__info))


def del_relevance_asset(data) -> dict:
    region_id = data.get('region_id')
    id_list = data.get('id_list')
    if not region_id:
        return dict(code=-1, msg="云区域ID不能为空")

    if not id_list:
        return dict(code=-2, msg="资产ID列表不能为空")

    with DBContext('w', None, True) as session:
        session.query(CloudRegionAssetModels).filter(CloudRegionModels.id == region_id).filter(
            CloudRegionAssetModels.asset_id.in_(id_list)).delete(synchronize_session=False)

    return dict(code=0, msg=f'删除关联关系成功  {len(id_list)} 条')


def relevance_asset(data) -> dict:
    filter_map = dict()
    topo_params = data.get('topoParams')
    region_id = data.get('id')
    biz_cn = topo_params.pop('biz_cn')
    if topo_params.get('env_name'):
        filter_map['env_name'] = topo_params.get('env_name')
    if topo_params.get('region_name'):
        filter_map['region_name'] = topo_params.get('region_name')
    if topo_params.get('module_name'):
        filter_map['env_name'] = topo_params.get('module_name')

    filter_map['asset_type'] = topo_params.get('asset_type')
    asset_type = topo_params.get('asset_type')
    with DBContext('w', None, True) as session:
        __biz_info = session.query(BizModels.biz_id).filter(BizModels.biz_cn_name == biz_cn).first()
        if not __biz_info:
            return dict(code=-1, msg="业务信息有误")

        filter_map['biz_id'] = __biz_info[0]
        tree_asset = session.query(TreeAssetModels.asset_id).filter_by(**filter_map).all()
        asset_id_set = set([i[0] for i in tree_asset])
        if not asset_id_set:
            return dict(code=-2, msg="当前拓扑下并没有主机")

        __cr_info = session.query(CloudRegionModels).filter(CloudRegionModels.id == region_id).first()
        if not __cr_info:
            return dict(code=-5, msg="云区域ID有误")
        cloud_region_id = __cr_info.cloud_region_id
        exist_info = session.query(CloudRegionAssetModels.asset_id).filter_by(
            **dict(region_id=region_id, asset_type=asset_type)).filter(
            CloudRegionAssetModels.asset_id.in_(asset_id_set)).all()

        asset_exist_ids = set([i[0] for i in exist_info])

        need_add_asset_set = asset_id_set.difference(asset_exist_ids)

        session.add_all([CloudRegionAssetModels(
            **{"asset_id": i, "region_id": region_id, "cloud_region_id": cloud_region_id, "asset_type": asset_type}) for
            i in need_add_asset_set])

        update_agent_id(asset_id_set, cloud_region_id)
        return dict(code=0, msg="关联完毕，并更新云区域的agent信息")


def update_agent_id(asset_id_set, cloud_region_id):
    with DBContext('w', None, True) as session:
        __info = session.query(AssetServerModels).filter(AssetServerModels.id.in_(asset_id_set)).all()
        all_info = [dict(id=asset.id, agent_id=f"{asset.inner_ip}:{cloud_region_id}") for asset in __info]
        session.bulk_update_mappings(AssetServerModels, all_info)
