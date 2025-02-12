#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2021/1/27 11:02
Desc    : 解释一下吧
"""

import logging
from shortuuid import uuid
from sqlalchemy import or_, func
from typing import *
from websdk2.db_context import DBContextV2 as DBContext
from models.asset import AssetServerModels
from models.tree import TreeAssetModels
from websdk2.sqlalchemy_pagination import paginate
from websdk2.model_utils import CommonOptView, insert_or_update, queryset_to_list

# from websdk2.model_utils import insert_or_update

opt_obj = CommonOptView(AssetServerModels)


def _models_to_list(server_info: List[AssetServerModels]) -> List[dict]:
    """模型转换,格式处理"""
    server_list: List[dict] = []
    for data_dict in server_info:
        # data_dict['create_time'] = str(data_dict['create_time'])
        # data_dict['update_time'] = str(data_dict['update_time'])
        # 特殊处理下ext_info数据，合并下
        update_data = data_dict['ext_info']
        update_data = {} if not update_data else update_data
        data_dict.pop('ext_info')
        data_dict.update(update_data)
        server_list.append(data_dict)
    return server_list


def _get_server_by_filter(search_filter: str = None):
    """过滤筛选"""
    if not search_filter:
        return [True]

    query_filter_map = {
        "is_normal": [AssetServerModels.is_expired == False],
        "is_expired": [AssetServerModels.is_expired == True],
        "is_showdown": [AssetServerModels.state == "关机"],
        "is_product": [AssetServerModels.is_product == 0],
    }
    return [*query_filter_map.get(search_filter, [])]


def _get_server_by_val(val: str = None):
    """模糊查询"""
    if not val:  return True
    return or_(
        AssetServerModels.instance_id.like(f'%{val}%'), AssetServerModels.cloud_name.like(f'%{val}%'),
        AssetServerModels.name.like(f'%{val}%'), AssetServerModels.state.like(f'%{val}%'),
        AssetServerModels.inner_ip.like(f'%{val}%'), AssetServerModels.outer_ip.like(f'%{val}%'),
        AssetServerModels.ext_info['zone'].like(f'%{val}%'),
        AssetServerModels.ext_info['charge_type'].like(f'%{val}%'),
        AssetServerModels.ext_info['network_type'].like(f'%{val}%'),
        AssetServerModels.ext_info['instance_type'].like(f'%{val}%'),
    )


def get_server_list(**params) -> dict:
    value = params.get('searchValue') if "searchValue" in params else params.get('searchVal')
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'page_size' not in params: params['page_size'] = 300  # 默认获取到全部数据
    search_filter = params.get('search_filter', None)
    with DBContext('r') as session:
        page = paginate(session.query(AssetServerModels).filter(*_get_server_by_filter(search_filter),
                                                                _get_server_by_val(value)).filter_by(**filter_map),
                        **params)
        data = _models_to_list(page.items)
    return dict(code=0, msg='获取成功', data=data, count=page.total)


def _get_server_by_sg(val: str = None):
    """模糊查询"""
    if not val:  return True
    return or_(
        AssetServerModels.ext_info['security_group_ids'].like(f'%{val}%'),
    )


def get_server_for_security_group(sg_id: str) -> dict:
    with DBContext('r') as session:
        models: List[AssetServerModels] = session.query(AssetServerModels).filter(_get_server_by_sg(sg_id)).all()
        queryset = queryset_to_list(models)
        data = _models_to_list(queryset)
    return dict(code=0, msg='获取成功', data=data, count=len(queryset))


def mark_server(data: dict) -> dict:
    """
    标记上线状态
    """

    name = data.get("name", None)
    is_product = data.get("is_product", "0")

    if not isinstance(is_product, int):
        return {"code": 1, "msg": "is_product type error"}

    if not name or int(is_product) not in [0, 1]:
        return {"code": 2, "msg": "update is_product params error"}

    filter_map = dict(name=name)
    with DBContext("w", None, True) as session:
        exist_id = session.query(AssetServerModels.id).filter_by(**filter_map).first()
        if not exist_id:
            return {"code": 3, "msg": f"name: {name} 不存在"}

        session.query(AssetServerModels).filter_by(**filter_map).update({AssetServerModels.is_product: is_product})
    return dict(code=0, msg='标记成功')


def add_server(server: dict):
    if not isinstance(server, dict):
        return {"code": 1, "msg": "server类型错误"}

    ext_info = server.pop('ext_info', None)
    if ext_info and not isinstance(ext_info, dict):
        return {"code": 1, "msg": "ext_info必须是json"}

    server = dict(list(ext_info.items()) + list(server.items()))
    cloud_name = server.get('cloud_name', None)
    inner_ip = server.get('inner_ip')
    name = server.get('name', None)
    if not cloud_name:
        return {"code": 1, "msg": "cloud_name不能为空"}

    if not name or not inner_ip:
        return {"code": 1, "msg": "inner_ip/name不能为空"}

    instance_id = server.get('instance_id')
    if not instance_id:
        instance_id = uuid(f'{inner_ip}{name}')

    ext_info['instance_id'] = instance_id
    if cloud_name: ext_info['cloud_name'] = cloud_name
    if name: ext_info['name'] = name
    if inner_ip: ext_info['inner_ip'] = inner_ip
    ownership = server.get('ownership', None)
    if not ownership:
        return {"code": 1, "msg": "归属不能为空"}

    try:
        with DBContext('w', None, True) as session:
            try:
                session.add(AssetServerModels(**dict(instance_id=instance_id, cloud_name=cloud_name,
                                                     account_id=server.get('account_id', uuid()).strip(),
                                                     # 随机uuid标记post写入
                                                     agent_id=server.get('agent_id', "0"),
                                                     state=server.get('state', '运行中'), name=name,
                                                     region=server.get('region'), zone=server.get('zone'),
                                                     inner_ip=inner_ip, outer_ip=server.get('outer_ip'),
                                                     ext_info=ext_info, is_expired=False, ownership=ownership)))
            except Exception as err:
                print(err)
                return dict(code=-1, msg=f'批量添加失败 {err}')
    except Exception as err:
        return dict(code=-2, msg=f'批量添加失败 {err}')

    return dict(code=0, msg='批量添加成功')


def add_server_batch(data: dict):
    server_list = data.get('server_list')

    if not server_list:
        logging.error(f'server_list error: {server_list}')
        return {"code": 1, "msg": "server_list可能为空"}

    if not isinstance(server_list, list):
        logging.error(f'server_list error: {server_list}')
        return {"code": 1, "msg": "server_list格式不正确"}

    for server in server_list:
        if not isinstance(server, dict):
            return {"code": 1, "msg": "server类型错误"}

        cloud_name = server.get('cloud_name', None)
        instance_id = server.get('instance_id', None)
        name = server.get('name', None)  # 统一用name
        ext_info = server.get('ext_info', None)
        if not cloud_name:
            return {"code": 1, "msg": "cloud_name不能为空"}

        if not instance_id or not name:
            return {"code": 1, "msg": "instance_id/name不能为空"}

        if ext_info and not isinstance(ext_info, dict):
            return {"code": 1, "msg": "ext_info必须是json"}

        instance_id = server.get('instance_id')

        try:
            with DBContext('w', None, True) as session:
                try:
                    session.add(insert_or_update(AssetServerModels, f"instance_id='{instance_id}'",
                                                 instance_id=instance_id, cloud_name=cloud_name,
                                                 account_id='3bba81a',  # 随机uuid标记post写入
                                                 agent_id=server.get('agent_id').strip(),
                                                 state=server.get('state'), name=server.get('name'),
                                                 region=server.get('region'), zone=server.get('zone'),
                                                 inner_ip=server.get('inner_ip'),
                                                 outer_ip=server.get('outer_ip'),
                                                 ext_info=ext_info, is_expired=False  # 新机器标记正常))
                                                 ))
                except Exception as err:
                    print(err)
        except Exception as err:
            print(err)

    return dict(code=0, msg='批量添加成功')


def patch_server_batch(data: dict):
    hosts = data.get('hosts')
    outer_biz_addr = data.get('outer_biz_addr')

    with DBContext('w', None, True) as session:
        if outer_biz_addr:
            for host in hosts:
                logging.info(
                    f"{host.get('instance_id')},{host.get('name')} 修改 {host.get('outer_biz_addr')} 为 {outer_biz_addr}")
                session.query(AssetServerModels).filter(AssetServerModels.id == host.get('id')).update(
                    {AssetServerModels.outer_biz_addr: outer_biz_addr})
        else:
            return dict(code=-1, msg='缺少必要参数')
    return dict(code=0, msg='修改成功')


def delete_server(data: dict) -> dict:
    hosts = data.get('hosts')
    name = data.get('name')

    # 根据name删除，回收使用 不做过期校验
    if name:
        with DBContext("w", None, True) as session:
            session.query(AssetServerModels).filter(AssetServerModels.name == name).delete(synchronize_session=False)
        return dict(code=0, msg='不做过期校验')

    if not hosts:
        return dict(code=-1, msg='hosts不能为空')

    host_ids = [i.get('id') for i in hosts]
    with DBContext('w', None, True) as session:
        __info = session.query(TreeAssetModels).filter(TreeAssetModels.asset_type == 'server').filter(
            TreeAssetModels.asset_id.in_(host_ids)).all()
        if __info:
            return dict(code=-2, msg='还有主机有业务关联，请先处理与业务的关联')
        else:
            session.query(AssetServerModels).filter(AssetServerModels.id.in_(host_ids)).delete(
                synchronize_session=False)
    return dict(code=0, msg='删除成功')

    # hosts_state = list(filter(lambda x: x["state"] == "运行中", hosts))
    # normal_hosts = list(filter(lambda x: x["is_expired"] == False, hosts))
    #
    # if normal_hosts and hosts_state:
    #     logging.error(f"以下主机List未过期，不能删除: {normal_hosts}")
    #     return {"code": 1, "msg": "存在未过期的主机，不能删除"}
    #
    # host_ids = [i.get('id') for i in hosts]
    # with DBContext('w', None, True) as session:
    #     # for _id in host_ids:
    #     session.query(AssetServerModels).filter(AssetServerModels.id.in_(host_ids)).delete(
    #         synchronize_session=False)
    # return dict(code=0, msg='删除成功')


def check_delete(data: dict, asset_type) -> bool:
    id_list = data.get('id_list')
    if id_list and isinstance(id_list, list):
        with DBContext('w', None, True) as session:
            __info = session.query(TreeAssetModels).filter(TreeAssetModels.asset_type == asset_type).filter(
                TreeAssetModels.asset_id.in_(id_list)).all()
            if __info:
                return True

    return False


def get_unique_servers():
    """查询唯一的inner_ip -> server 映射"""
    with DBContext("r") as session:
        subquery = (
            session.query(
                AssetServerModels.inner_ip,
                func.max(AssetServerModels.id).label(
                    "max_id"
                ),  # 获取最大 id 作为唯一标识
            )
            .filter(AssetServerModels.is_expired.is_(False))  # 只查询未过期的记录
            .filter(AssetServerModels.state == "运行中")  # 只查询运行中的记录
            .filter(AssetServerModels.inner_ip.isnot(None))  # 过滤掉 inner_ip 为空的记录
            .filter(AssetServerModels.inner_ip != "")  # 过滤掉 inner_ip 为空字符串的记录
            .group_by(AssetServerModels.inner_ip)  # 按 inner_ip 分组
            .having(
                func.count(AssetServerModels.inner_ip) == 1
            )  # 只保留每个 inner_ip 出现一次的记录
            .subquery()  # 创建一个子查询
        )
        # 主查询：基于子查询结果连接，确保每个 inner_ip 只对应一条记录
        servers = (
            session.query(AssetServerModels)
            .join(subquery, AssetServerModels.id == subquery.c.max_id)
            .filter(AssetServerModels.is_expired.is_(False))
            .filter(AssetServerModels.state == "运行中")
            .filter(AssetServerModels.inner_ip.isnot(None))  # 过滤掉 inner_ip 为空的记录
            .filter(AssetServerModels.inner_ip != "")  # 过滤掉 inner_ip 为空字符串的记录
            .all()
        )
        return {server.inner_ip: server for server in servers}