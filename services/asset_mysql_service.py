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
from shortuuid import uuid
from websdk2.db_context import DBContextV2 as DBContext
from models.asset import AssetMySQLModels as mysqlModel
from websdk2.sqlalchemy_pagination import paginate
from websdk2.model_utils import CommonOptView

opt_obj = CommonOptView(mysqlModel)


def _models_to_list(server_info: List[mysqlModel]) -> List[dict]:
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
        "is_normal": [mysqlModel.is_expired == False],
        "is_expired": [mysqlModel.is_expired == True],
        "is_showdown": [mysqlModel.state == "关机"],
    }
    return [*query_filter_map.get(search_filter, [])]


def _get_mysql_by_val(search_val: str = None):
    """模糊查询"""
    if not search_val:
        return True

    return or_(
        mysqlModel.name.like(f'%{search_val}%'),
        mysqlModel.instance_id.like(f'%{search_val}%'),
        mysqlModel.region.like(f'%{search_val}%'),
        mysqlModel.zone.like(f'%{search_val}%'),
        mysqlModel.db_class.like(f'%{search_val}%'),
        mysqlModel.db_engine.like(f'%{search_val}%'),
    )


def _get_mysql_by_address_like(search_address: str = None):
    """根据地址模糊查询"""
    if not search_address:
        return True

    return mysqlModel.db_address.like(f'%{search_address}%')


def get_mysql_list_for_api(**params) -> dict:
    value = params.get('searchValue') if "searchValue" in params else params.get('searchVal')
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'page_size' not in params: params['page_size'] = 300  # 默认获取到全部数据
    search_filter = params.get('search_filter', None)
    search_address = params.get('search_address', '')
    with DBContext('r') as session:
        page = paginate(
            session.query(mysqlModel).filter(*_get_mysql_by_filter(search_filter), _get_mysql_by_val(value),
                                             _get_mysql_by_address_like(search_address)).filter_by(**filter_map),
            **params)
        data = _models_to_list(page.items)
    return dict(code=0, msg='获取成功', data=data, count=page.total)


def add_mysql(data: dict) -> dict:
    if not isinstance(data, dict):
        return dict(code=-1, msg="数据类型错误")

    db_address = data.pop('db_address', None)

    if not db_address or not db_address.get('items'):
        return {"code": -2, "msg": "db_address 数据不能为空"}
    if db_address and not isinstance(db_address, dict):
        return dict(code=-2, msg="db_address 数据类型错误")

    ext_info = data.pop('ext_info', None)
    if ext_info and not isinstance(ext_info, dict):
        return dict(code=-3, msg="扩展数据数据类型错误")

    data = dict(list(ext_info.items()) + list(data.items()))
    cloud_name = data.get('cloud_name', None)
    name = data.get('name', None)
    if not cloud_name:
        return dict(code=-4, msg="厂商名称不能为空")

    instance_id = data.get('instance_id')
    if not instance_id:
        instance_id = uuid(f'{cloud_name}{name}')

    ext_info['instance_id'] = instance_id
    if cloud_name: ext_info['cloud_name'] = cloud_name
    if name: ext_info['name'] = name
    ext_info['db_address'] = db_address
    try:
        with DBContext('w', None, True) as session:
            try:
                session.add(mysqlModel(**dict(instance_id=instance_id, cloud_name=cloud_name,
                                              account_id=data.get('account_id', uuid()).strip(),
                                              state=data.get('state', '运行中'), name=name,
                                              region=data.get('region'), zone=data.get('zone'),
                                              db_engine=data.get('db_engine'), db_class=data.get('db_class'),
                                              db_version=data.get('db_version'), db_address=db_address,
                                              ext_info=ext_info, is_expired=False)))
            except Exception as err:
                print(err)
                return dict(code=-9, msg=f'添加失败 {err}')
    except Exception as err:
        return dict(code=-10, msg=f'添加失败 {err}')

    return dict(code=0, msg='添加成功')
