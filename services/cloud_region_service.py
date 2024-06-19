#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2021/1/27 11:02
Desc    : 解释一下吧
"""
import logging
from typing import *

from sqlalchemy import or_, func
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.sqlalchemy_pagination import paginate
from websdk2.model_utils import CommonOptView, model_to_dict
from models.cloud_region import CloudRegionModels, CloudRegionAssetModels
from models.tree import TreeAssetModels
from models.business import BizModels
from models.asset import AssetServerModels
from services.asset_server_service import _models_to_list


opt_obj = CommonOptView(CloudRegionModels)


def _get_value(value: str = None):
    if not value:
        return True
    return or_(
        CloudRegionModels.name.like(f'%{value}%'),
        CloudRegionModels.cloud_region_id.like(f'%{value}%'),
        # CloudRegionModels.proxy_ip.like(f'%{value}%'),
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


def check_asset_group_rules(asset_group_rules: List[List[dict]], existing_asset_group_rules: []):
    """
    为了保证每一个实例只能归属于一个云区域，对资产组规则之间做交集校验
    """

    rules = [item.get("query_value")[-1] for item in asset_group_rules[0] if item['query_name'] == "vpc"]

    # 已存在的规则
    existing_asset_group_rules = [[item.get("query_value")[-1] for item in asset_group_rules[0]
                                   if item['query_name'] == "vpc"] for asset_group_rules in existing_asset_group_rules]


    # 通过集合求交集
    has_intersection = any(not set(rules).isdisjoint(set(existing_asset_group_rule)) for existing_asset_group_rule
                           in existing_asset_group_rules)
    return False if has_intersection else True


def update_server_agent_id_by_cloud_region_rules(asset_group_rules: List[List[Dict]], cloud_region_id: str):
    if not (asset_group_rules and cloud_region_id):
        return False
    vpc_values = [query["query_value"][-1] for sublist in asset_group_rules for query in sublist if query["query_name"] == "vpc"]

    if not vpc_values:
        logging.warning("没有找到有效的VPC规则")
        return False

    try:
        with DBContext('w', None, True) as session:
            # 使用 JSON 字段中的 vpc_id 进行过滤
            servers = session.query(AssetServerModels).filter(
                func.json_extract(AssetServerModels.ext_info, '$.vpc_id').in_(vpc_values)
            ).all()

            for server in servers:
                server.agent_id = f"{server.inner_ip}:{cloud_region_id}"

            session.commit()
            logging.info(f"成功更新了{len(servers)}台服务器的AgentID")
            return True
    except Exception as e:
        logging.error(f"更新服务器AgentID失败: {e}")
        return False


def add_cloud_region_for_api(data) -> dict:
    """
    添加云区域
    """
    asset_group_rules = data.get('asset_group_rules', None)

    if 'cloud_region_id' not in data:
        return {"code": 1, "msg": "云区域ID不能为空"}

    if 'name' not in data:
        return {"code": 1, "msg": "云区域名称不能为空"}

    if 'proxy_ip' not in data:
        return {"code": 1, "msg": "代理地址不能为空"}

    if 'ssh_user' not in data:
        return {"code": 1, "msg": "ssh用户不能为空"}

    if 'auto_update_agent_id' not in data:
        return {"code": 1, "msg": "自动更新AgentID不能为空"}

    if not isinstance(asset_group_rules, list):
        return {"code": 1, "msg": "资产规则类型错误"}

    if not asset_group_rules:
        return {"code": 1, "msg": "资产规则不能为空"}

    for rules in asset_group_rules:
        for rule in rules:
            if rule.get('status') == 1 and rule.get('query_name') == 'vpc' and len(rule.get('query_value')) < 3:
                return {"code": 1, "msg": "资产规则值不能为空"}

    # 防止参数中存在不必要的字段
    create_data = dict(name=data.get("name"), cloud_region_id=data.get('cloud_region_id'),
                       proxy_ip=data.get('proxy_ip'), ssh_user=data.get('ssh_user'), detail=data.get('detail'),
                       ssh_ip=data.get('ssh_ip'), ssh_port=data.get('ssh_port'), ssh_key=data.get('ssh_key'),
                       ssh_pub_key=data.get('ssh_pub_key'), asset_group_rules=data.get('asset_group_rules'),
                       jms_org_id=data.get('jms_org_id'), jms_account_template=data.get('jms_account_template'),
                       auto_update_agent_id=data.get('auto_update_agent_id'))

    try:
        with DBContext('r') as session:
            res = session.query(CloudRegionModels.asset_group_rules).filter(CloudRegionModels.asset_group_rules.isnot(None)).all()
            rules = [item[0] for item in res]
            is_valid = check_asset_group_rules(asset_group_rules, rules)
            if not is_valid:
                return {"code": 1, "msg": "资产规则已存在"}
    except Exception as error:
        return {"code": 1, "msg": str(error)}

    try:
        with DBContext('w', None, True) as session:
            exist_id = session.query(CloudRegionModels).filter(or_(CloudRegionModels.name == data.get('name'),
                                                                   CloudRegionModels.cloud_region_id == data.get('cloud_region_id'))).first()
            if exist_id:
                if exist_id.name == data.get('name'):
                    return {"code": 1, "msg": f"云区域{exist_id.name}已存在."}
                elif exist_id.cloud_region_id == data.get('cloud_region_id'):
                    return {"code": 1, "msg": f"云区域{exist_id.cloud_region_id}已存在."}
            session.add(CloudRegionModels(**create_data))
    except Exception as error:
        return {"code": 1, "msg": str(error)}

    # 处理自动更新 AgentID
    auto_update_agent_id = data.get('auto_update_agent_id')
    if auto_update_agent_id == "yes":
        result = update_server_agent_id_by_cloud_region_rules(asset_group_rules, data.get('cloud_region_id'))
        logging.info(f"更新AgentID结果: {result}")

    return {"code": 0, "msg": "添加成功"}


def put_cloud_region_for_api(data) -> dict:
    """
    编辑云区域
    """
    asset_group_rules = data.get('asset_group_rules', None)
    if "id" not in data:
        return {"code": 1, "msg": "ID不能为空"}

    if 'cloud_region_id' not in data:
        return {"code": 1, "msg": "云区域ID不能为空"}

    if 'name' not in data:
        return {"code": 1, "msg": "云区域名称不能为空"}

    if 'proxy_ip' not in data:
        return {"code": 1, "msg": "代理地址不能为空"}

    if 'ssh_user' not in data:
        return {"code": 1, "msg": "ssh用户不能为空"}

    if 'auto_update_agent_id' not in data:
        return {"code": 1, "msg": "自动更新AgentID不能为空"}

    if not isinstance(asset_group_rules, list):
        return {"code": 1, "msg": "资产规则类型错误"}

    if not asset_group_rules:
        return {"code": 1, "msg": "资产规则不能为空"}

    for rules in asset_group_rules:
        for rule in rules:
            if rule.get('status') == 1 and rule.get('query_name') == 'vpc' and len(rule.get('query_value')) < 3:
                return {"code": 1, "msg": "资产规则值不能为空"}

    try:
        with DBContext('r') as session:
            res = session.query(CloudRegionModels.asset_group_rules). \
                filter(CloudRegionModels.id != data.get('id')). \
                filter(CloudRegionModels.asset_group_rules.isnot(None)).all()
            rules = [item[0] for item in res]
            is_valid = check_asset_group_rules(asset_group_rules, rules)
            if not is_valid:
                return {"code": 1, "msg": "资产规则已存在"}
    except Exception as error:
        return {"code": 1, "msg": str(error)}

    new_data = dict(name=data.get("name"), cloud_region_id=data.get('cloud_region_id'), proxy_ip=data.get('proxy_ip'),
                    ssh_user=data.get('ssh_user'), detail=data.get('detail'),
                    ssh_ip=data.get('ssh_ip'), ssh_port=data.get('ssh_port'), ssh_key=data.get('ssh_key'),
                    ssh_pub_key=data.get('ssh_pub_key'), asset_group_rules=data.get('asset_group_rules'),
                    jms_org_id=data.get('jms_org_id'), jms_account_template=data.get('jms_account_template'),
                    auto_update_agent_id=data.get('auto_update_agent_id')
    )

    try:
        with DBContext('w', None, True) as session:
            session.query(CloudRegionModels).filter(CloudRegionModels.id == data.get('id')).update(new_data)
    except Exception as error:
        return {"code": 1, "msg": str(error)}

    # 处理自动更新AgentID
    auto_update_agent_id = data.get('auto_update_agent_id')
    if auto_update_agent_id == "yes":
        result = update_server_agent_id_by_cloud_region_rules(asset_group_rules, data.get('cloud_region_id'))
        logging.info(f"更新AgentID结果: {result}")

    return {"code": 0, "msg": "更新成功"}


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


def preview_cloud_region_v2(**params) -> dict:
    """预览主机"""
    # 根据云区域vpc查找主机
    value = params.get('searchValue') if "searchValue" in params else params.get('searchVal')
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'biz_id' in filter_map: filter_map.pop('biz_id')  # 暂时不隔离
    if 'page_size' not in params: params['page_size'] = 300  # 默认获取到全部数据
    region_id = params.get('region_id')
    if not region_id:
        return dict(code=-1, msg='云区域ID不能为空')
    result = []
    with DBContext('r') as session:
        cloud_region_obj = session.query(CloudRegionModels).filter(CloudRegionModels.id == region_id).first()
        if not cloud_region_obj:
            return dict(code=-1, msg='云区域不存在')
        asset_group_rules = cloud_region_obj.asset_group_rules
        if not asset_group_rules:
            return dict(msg='获取成功', code=0, data=result, count=0)
        vpc_values = [query["query_value"][-1] for sublist in asset_group_rules for query in sublist
                      if query["query_name"] == "vpc" and query['status'] == 1]
        try:
            # 使用JSON字段中的vpc_id进行过滤
            query = session.query(AssetServerModels).filter(_get_server_value(value)).filter_by(**filter_map)
            query = query.filter(func.json_extract(AssetServerModels.ext_info, '$.vpc_id').in_(vpc_values))
            total = query.count()
            page = paginate(query, order_by=None, **params)
            result = _models_to_list(page.items)
        except Exception as e:
            logging.error(e)
    return dict(msg='获取成功', code=0, data=result, count=total)


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
