#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/3/27 11:02
Desc    : 动态分组逻辑处理
"""

import logging
from typing import *
from shortuuid import uuid
from sqlalchemy import or_
from websdk2.sqlalchemy_pagination import paginate
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.model_utils import CommonOptView, model_to_dict
from models.business import DynamicGroupModels
from models.tree import TreeAssetModels
from models.asset import AssetServerModels

opt_obj = CommonOptView(DynamicGroupModels)

public_resource = "公共项目"
public_tenantid = "501"


def pre_format(data: dict) -> dict:
    biz_id = data.get('biz_id', '501')

    # 处理 0表示前端标记删除
    dynamic_group_rules = list(
        filter(
            lambda rule: rule["status"] == 1, data.get('dynamic_group_rules')
        )
    )
    _dynamic_group_dict = {
        "items": dynamic_group_rules
    }

    if data.get('dynamic_group_type') == 'normal':
        biz_id = '501'

    res = dict(
        biz_id=biz_id, dynamic_group_name=data.get('dynamic_group_name'),
        dynamic_group_type=data.get('dynamic_group_type'), modify_user=data.get('modify_user', 'admin'),
        dynamic_group_rules=_dynamic_group_dict, dynamic_group_detail=data.get('dynamic_group_detail'),
        env_name=data.get('env_name'), region_name=data.get('region_name'), module_name=data.get('module_name'),

    )

    return res


def add_dynamic_group_for_api(data: dict) -> dict:
    dynamic_group_rules = data.get('dynamic_group_rules', None)

    if 'dynamic_group_name' not in data:
        return {"code": 1, "msg": "动态分组名称不能为空"}
    if 'dynamic_group_type' not in data:
        return {"code": 1, "msg": "动态分组类型不能为空"}

    if dynamic_group_rules and not isinstance(dynamic_group_rules, list):
        return {"code": 1, "msg": "条件规则类型错误"}

    new_data = pre_format(data)
    if data.get('dynamic_group_type') == 'normal':
        if not new_data.get('dynamic_group_rules').get('items'):
            return {"code": 1, "msg": "条件不能为空"}
    else:
        if not new_data.get('biz_id'):
            return {"code": 1, "msg": "业务ID 不能为空"}
    new_data['exec_uuid'] = uuid()
    try:
        with DBContext('w', None, True) as session:
            exist_id = session.query(DynamicGroupModels).filter(
                DynamicGroupModels.dynamic_group_name == new_data.get('dynamic_group_name')).first()
            if exist_id:
                return {"code": 1, "msg": f"{exist_id.dynamic_group_name} already exists."}

            session.add(DynamicGroupModels(**new_data))
    except Exception as error:
        logging.error(error)
        return {"code": 1, "msg": str(error)}

    return {"code": 0, "msg": "添加成功"}


def update_dynamic_group_for_api(data: dict) -> dict:
    dynamic_group_rules = data.get('dynamic_group_rules', None)

    if 'id' not in data:
        return {"code": 1, "msg": "动态分组ID不能为空"}

    if 'dynamic_group_name' not in data:
        return {"code": 1, "msg": "动态分组名称不能为空"}
    if 'dynamic_group_type' not in data:
        return {"code": 1, "msg": "动态分组类型不能为空"}

    if dynamic_group_rules and not isinstance(dynamic_group_rules, list):
        return {"code": 1, "msg": "条件规则类型错误"}

    new_data = pre_format(data)
    if data.get('dynamic_group_type') == 'normal':
        if not new_data.get('dynamic_group_rules').get('items'):
            return {"code": 1, "msg": "条件不能为空"}
    else:
        if not new_data.get('biz_id'):
            return {"code": 1, "msg": "业务ID 不能为空"}

    try:
        with DBContext('w', None, True) as session:
            session.query(DynamicGroupModels).filter(DynamicGroupModels.id == data.get('id')).update(new_data)
    except Exception as error:
        logging.error(error)
        return {"code": 1, "msg": str(error)}
    return {"code": 0, "msg": "更新成功"}


def _get_value(value: str = None):
    if not value:
        return True
    return or_(
        DynamicGroupModels.dynamic_group_name.like(f'%{value}%'),
        DynamicGroupModels.exec_uuid.like(f'%{value}%'),
        DynamicGroupModels.modify_user.like(f'%{value}%'),
        DynamicGroupModels.biz_id == value,
        DynamicGroupModels.dynamic_group_type == value,
        DynamicGroupModels.dynamic_group_detail.like(f'%{value}%'),
    )


def get_dynamic_group(**params) -> dict:
    value = params.get('searchValue') if "searchValue" in params else params.get('searchVal')
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'biz_id' in filter_map: filter_map.pop('biz_id')  # 暂时不隔离
    if 'page_size' not in params: params['page_size'] = 300  # 默认获取到全部数据
    with DBContext('r') as session:
        page = paginate(session.query(DynamicGroupModels).filter(_get_value(value)).filter_by(**filter_map), **params)

    return dict(msg='获取成功', code=0, data=page.items, count=page.total)


def get_dynamic_group_for_use_api(**params) -> dict:
    value = params.get('searchValue') if "searchValue" in params else params.get('searchVal')
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    # if 'biz_id' in filter_map: filter_map.pop('biz_id')  # 暂时不隔离
    biz_id = filter_map.pop('biz_id') if filter_map.get('biz_id') else params.get('biz_id')

    if 'page_size' not in params: params['page_size'] = 300  # 默认获取到全部数据
    with DBContext('r') as session:
        page = paginate(session.query(DynamicGroupModels).filter(
            or_(DynamicGroupModels.biz_id == biz_id, DynamicGroupModels.biz_id == public_tenantid)).filter(
            _get_value(value)).filter_by(**filter_map), **params)

    return dict(msg='获取成功', code=0, data=page.items, count=page.total)


def preview_dynamic_group_for_api(exec_uuid_list: list) -> dict:
    res_list = []

    with DBContext('r') as session:
        for exec_id in exec_uuid_list:
            group_info = session.query(DynamicGroupModels).filter(DynamicGroupModels.exec_uuid == exec_id).first()
            if not group_info:
                return dict(code=-1, msg='动态分组ID不存在', data=[])

            if group_info.dynamic_group_type == 'normal':
                # 获取主机信息
                is_success, result = get_dynamic_hosts(model_to_dict(group_info))
                if not is_success or not result:
                    logging.error(f"normal {exec_id} 没有发现主机信息")

                res_list.extend(result)
            elif group_info.dynamic_group_type == 'biz':
                is_success, result = get_dynamic_hosts_for_biz(model_to_dict(group_info))
                if not is_success or not result:
                    logging.error(f"biz {exec_id} 没有发现主机信息")
            else:
                result = []

            res_list.extend(result)

        asset_set = set(res_list)
        try:
            the_model = AssetServerModels
            __asset = session.query(the_model.instance_id, the_model.name, the_model.inner_ip, the_model.outer_ip,
                                    the_model.state, the_model.agent_status, the_model.agent_id).filter(
                the_model.id.in_(asset_set)).all()

            server_list = [dict(zip(res.keys(), res)) for res in __asset]
            __count = len(server_list)
            return dict(msg='获取成功', code=0, data=server_list, count=__count)
        except Exception as error:
            logging.error(f"{error} 获取主机失败")
            return dict(msg='获取失败', code=-1)


def _get_env(value: str = None):
    if not value:
        return True
    return or_(
        TreeAssetModels.env_name == value
    )


def _get_region(value: str = None):
    if not value:
        return True
    value = value.replace(',', ' ')
    value = value.replace(';', ' ')
    value = value.replace('，', ' ')
    region_list = value.split()

    return or_(
        TreeAssetModels.region_name.in_(region_list)
    )


def _get_module(value: str = None):
    if not value:
        return True
    value = value.replace(',', ' ')
    value = value.replace(';', ' ')
    value = value.replace('，', ' ')
    module_list = value.split()
    return or_(
        TreeAssetModels.module_name.in_(module_list)
    )


def get_dynamic_hosts_for_biz(group_info: Optional[dict]) -> Tuple[bool, Union[list]]:
    """
    :param group_info:
    "data": {
        "id": 7,
        "biz_id": "508",
        "dynamic_group_name": "",
        "dynamic_group_type": "",
        "dynamic_group_detail": "",
        "env_name": "prod",
        "region_name": "",
        "module_name": ""
    }
    根据动态分组ID获取主机信息
    """

    if not isinstance(group_info, dict):
        logging.error(f"group_info类型错误")
        return False, []

    biz_id = group_info.get('biz_id')
    env_name = group_info.get('env_name')
    region_name = group_info.get('region_name')
    module_name = group_info.get('module_name')
    with DBContext('r') as session:
        __tree_asset = session.query(TreeAssetModels.asset_id).filter(TreeAssetModels.biz_id == biz_id,
                                                                      TreeAssetModels.asset_type == 'server',
                                                                      _get_env(env_name), _get_region(region_name),
                                                                      _get_module(module_name)
                                                                      ).all()
        server_list = [i[0] for i in __tree_asset]
    return True, server_list


def get_dynamic_hosts(group_info: Optional[dict]) -> Tuple[bool, Union[list]]:
    """
    :param group_info:
    "data": {
        "id": 7,
        "biz_id": "501",
        "dynamic_group_name": "",
        "dynamic_group_type": "",
        "dynamic_group_detail": "",
        "dynamic_group_rules": {
            "items": [
                {
                    "index": 1,
                    "status": 1,
                    "query_name": "name",
                    "query_value": "-111",
                    "query_conditions": "like"
                },
            ]
        }
    }
    根据动态分组ID获取主机信息
    """
    if not isinstance(group_info, dict):
        logging.error(f"group_info类型错误")
        return False, []

    # 根据规则查主机
    try:
        rules = group_info['dynamic_group_rules']['items']
    except TypeError:
        rules = []

    if not rules:
        logging.error(f"匹配规则出错")
        return False, []

    sql_string = """ SELECT id FROM t_asset_server WHERE name = ""\n """
    # 查询条件
    sql_conditions = ''
    for rule in rules:
        query_name = rule['query_name']
        query_conditions = rule['query_conditions']
        if query_conditions not in ['like', '=', '!=']: continue
        query_value = f"%{rule['query_value']}%" if query_conditions == 'like' else f"{rule['query_value']}"
        sql_conditions += f'or {query_name} {query_conditions} "{query_value}"\n'
    # 拼接SQL
    sql_string += sql_conditions
    try:
        with DBContext('r') as session:
            results = session.execute(sql_string)
            server_list = [res[0] for res in results]
    except Exception as error:
        logging.error(f"{error}")
        return False, []

    return True, server_list
