#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023年4月7日
"""

import logging
from sqlalchemy import func, or_
from typing import *
from models.tree import TreeModels, TreeAssetModels
# from libs.tree import Tree
from models.business import BizModels
from models import asset_mapping as mapping
from websdk2.model_utils import model_to_dict, queryset_to_list
from websdk2.db_context import DBContextV2 as DBContext

from services.audit_service import audit_log
from services.tree_service import generate_tree_message


@audit_log()
def add_tree_asset_by_api(data: dict) -> dict:
    biz_id = data.get('biz_id')
    env_name = data.get('env_name')
    region_name = data.get('region_name')
    module_name = data.get('module_name', None)
    asset_type = data.get('asset_type', None)
    node_type = data.get('node_type', 3)
    module_list = data.get('module_list')
    asset_ids = data.get('asset_ids', None)
    is_enable = data.get('is_enable', 0)  # 默认0：不上线
    ext_info = data.get('ext_info', {})
    create_user = data.get('create_user', None)

    if not biz_id and asset_type and not asset_ids:
        return {'code': 1, 'msg': '缺少biz_id/asset_type/asset_ids'}

    if node_type == 2 and not module_list:
        return {'code': 2, 'msg': '当在集群下添加资源，必须指定模块列表'}

    with DBContext('w', None, True) as session:
        exist_asset_ids = session.query(TreeAssetModels.asset_id).filter(TreeAssetModels.biz_id == biz_id,
                                                                         TreeAssetModels.asset_type == asset_type,
                                                                         TreeAssetModels.env_name == env_name,
                                                                         TreeAssetModels.region_name == region_name,
                                                                         TreeAssetModels.module_name == module_name).all()

        exist_asset_ids = [i[0] for i in exist_asset_ids]
        # 删除已存在的asset_ids
        asset_ids = list(set(asset_ids) - set(exist_asset_ids))
        # 添加不存在的asset_ids
        if node_type == 2 and module_list and isinstance(module_list, list):
            session.add_all([
                TreeAssetModels(
                    biz_id=biz_id, env_name=env_name, region_name=region_name, module_name=module_name,
                    asset_type=asset_type, asset_id=asset_id, is_enable=is_enable, ext_info=ext_info,
                )
                for asset_id in asset_ids
                for module_name in module_list
            ])
        else:
            session.add_all([
                TreeAssetModels(
                    biz_id=biz_id, env_name=env_name, region_name=region_name, module_name=module_name,
                    asset_type=asset_type, asset_id=asset_id, is_enable=is_enable, ext_info=ext_info,
                )
                for asset_id in asset_ids
            ])

        biz_obj = session.query(BizModels).filter(BizModels.biz_id == biz_id).first()
        asset_names = get_asset_name_by_id(session, asset_type, list(asset_ids))
        _message = generate_tree_message(biz_obj.biz_cn_name, env_name, region_name, module_name, node_type)
        audit_log_message = f"用户{create_user}新增服务树{_message}资源, 资源类型:{asset_type}, 资源名：{asset_names}"
    return {"code": 0, "msg": "添加成功", "audit_log_message": audit_log_message}


@audit_log()
def update_tree_asset_by_api(data: dict) -> dict:
    asset_type = data.get('asset_type', None)
    select_ids = data.get('select_ids', None)
    is_enable = data.get('is_enable', 0)
    modify_user = data.get('modify_user', None)
    if not asset_type:
        return {'code': 1, 'msg': '缺少asset_type'}
    if not select_ids:
        return {'code': 1, 'msg': '缺少select_ids'}

    with DBContext('w', None, True) as session:
        session.query(TreeAssetModels).filter(
            TreeAssetModels.asset_type == asset_type, TreeAssetModels.id.in_(select_ids)
        ).update({TreeAssetModels.is_enable: is_enable}, synchronize_session=False)
        _action = "上线" if is_enable else "下线"
        asset_names = get_asset_name_by_tree_asset_id(session, asset_type, select_ids)
    return {"code": 0, "msg": "修改成功", "audit_log_message": f"用户{modify_user}操作服务树{asset_type}资源{_action}, "
                                                               f"资源名称：{asset_names}"}


def get_tree_asset_by_api(**params) -> dict:
    if "biz_id" not in params and 'biz_cn' in params:
        biz_cn = params.pop('biz_cn')
        with DBContext('r') as session:
            __biz_info = session.query(BizModels.biz_id).filter(BizModels.biz_cn_name == biz_cn).first()
            params['biz_id'] = __biz_info[0]

    # if "biz_id" not in params:  return self.write({"code": -1, "msg": "请选择业务"})
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    results, count = get_tree_assets(params)
    return {"code": 0, "msg": "获取成功", "data": results, "count": count}


def get_asset_id_by_name(session, asset_type: str, names: List[str]) -> List[int]:
    """
    根据主机名获取主机id
    :param session:
    :param asset_type: 资产类型
    :param names: 主机名列表 ['name1','name2']
    :return:
    """
    _the_models = mapping.get(asset_type)
    host_ids = session.query(_the_models.id).filter(_the_models.name.in_(names)).all()
    host_ids = [i[0] for i in host_ids]
    return host_ids


def get_asset_name_by_id(session, asset_type: str, ids: List[int]) -> List[str]:
    """
    根据资产id获取资产名称
    :param session:
    :param asset_type: 资产类型
    :param ids: 主机名列表 [id1, id2]
    :return:
    """
    _the_models = mapping.get(asset_type)
    return [i[0] for i in session.query(_the_models.name).filter(_the_models.id.in_(ids)).all()]


def get_asset_name_by_tree_asset_id(session, asset_type: str, ids: List[int]) -> List[str]:
    """
    根据树&资产关联表id-->获取资产id-->获取资产名称
    :param session:
    :param asset_type: 资产类型
    :param ids: 主机名列表 [id1, id2]
    :return:
    """
    asset_ids = [i[0] for i in session.query(TreeAssetModels.asset_id).filter(TreeAssetModels.id.in_(ids)).all()]
    _the_models = mapping.get(asset_type)
    return [i[0] for i in session.query(_the_models.name).filter(_the_models.id.in_(asset_ids)).all()]


# 删除拓扑
@audit_log()
def del_tree_asset(data: dict) -> dict:
    """
    删除主机
    :return:
    """
    asset_type = data.get('asset_type', None)
    biz_id = data.get("biz_id", None)
    env_name = data.get('env_name', None)
    region_name = data.get('region_name', None)
    module_name = data.get('module_name', None)
    names = data.get('names', None)
    modify_user = data.get('modify_user', None)
    # 参数校验
    if not asset_type or not biz_id or not env_name or not region_name or not module_name:
        return {'code': 1, 'msg': '缺少必要参数'}

    if not isinstance(names, list):
        return {'code': 1, 'msg': 'names必须为list'}

    # 前端还是根据用户选择的ID主键去删除
    with DBContext('w', None, True) as session:
        # 获取资产ID
        _ids = get_asset_id_by_name(session, asset_type, names)
        # print(host_ids)
        session.query(TreeAssetModels.id).filter(TreeAssetModels.biz_id == biz_id,
                                                 TreeAssetModels.asset_type == asset_type,
                                                 TreeAssetModels.env_name == env_name,
                                                 TreeAssetModels.region_name == region_name,
                                                 TreeAssetModels.module_name == module_name,
                                                 TreeAssetModels.asset_id.in_(_ids)
                                                 ).delete(synchronize_session=False)
        biz_obj = session.query(BizModels).filter(BizModels.biz_id == biz_id).first()
        _message = generate_tree_message(biz_obj.biz_cn_name, env_name, region_name, module_name, node_type=3)
    return {"code": 0, "msg": "删除成功", "audit_log_message": f"用户{modify_user}删除服务树{_message}资源, "
                                                               f"资源类型：{asset_type}, 资源名：{names}"}


def update_tree_leaf(data: dict) -> dict:
    """
    修改树叶子节点
    :return:
    """
    required_params = ["biz_id", "env_name", "region_name", "modify_type", "new_name"]
    for param in required_params:
        if not data.get(param):
            return {'code': -1, 'msg': f'缺少必要参数 {param}'}

    biz_id = data["biz_id"]
    env_name = data["env_name"]
    region_name = data["region_name"]
    modify_type = data["modify_type"]
    new_name = data["new_name"]
    module_name = data.get('module_name', None)

    if modify_type not in [2, 3]:
        return {'code': -1, 'msg': '修改的类型有误'}

    # 前端还是根据用户选择的ID主键去删除
    with DBContext('w', None, True) as session:
        biz_info = session.query(BizModels).filter(BizModels.biz_id == biz_id).first()
        if not biz_info:
            return dict(code=-1, msg="业务信息有误，请联系管理员")

        if modify_type == 2 and region_name and new_name:
            session.query(TreeAssetModels).filter(TreeAssetModels.biz_id == biz_id,
                                                  TreeAssetModels.env_name == env_name,
                                                  TreeAssetModels.region_name == region_name
                                                  ).update({TreeAssetModels.region_name: new_name},
                                                           synchronize_session=False)
            session.query(TreeModels).filter(TreeModels.biz_id == biz_id,
                                             TreeModels.node_type == modify_type,
                                             TreeModels.parent_node == env_name,
                                             TreeModels.title == region_name
                                             ).update({TreeModels.title: new_name}, synchronize_session=False)

            session.query(TreeModels).filter(TreeModels.biz_id == biz_id,
                                             TreeModels.node_type == modify_type + 1,
                                             TreeModels.grand_node == env_name,
                                             TreeModels.parent_node == region_name
                                             ).update({TreeModels.parent_node: new_name}, synchronize_session=False)

        elif modify_type == 3 and module_name and new_name:
            session.query(TreeAssetModels).filter(TreeAssetModels.biz_id == biz_id,
                                                  TreeAssetModels.env_name == env_name,
                                                  TreeAssetModels.region_name == region_name,
                                                  TreeAssetModels.module_name == module_name
                                                  ).update({TreeAssetModels.module_name: new_name},
                                                           synchronize_session=False)
            session.query(TreeModels).filter(TreeModels.biz_id == biz_id,
                                             TreeModels.node_type == modify_type,
                                             TreeModels.grand_node == env_name,
                                             TreeModels.parent_node == region_name,
                                             TreeModels.title == module_name
                                             ).update({TreeModels.title: new_name}, synchronize_session=False)
        else:
            return {"code": -2, "msg": "参数错误"}

    return {"code": 0, "msg": "变更成功"}


def del_tree_leaf(data: dict) -> dict:
    """
    修改树叶子节点
    :return:
    """
    required_params = ["biz_id", "env_name", "region_name", "modify_type", "risk"]
    for param in required_params:
        if not data.get(param):
            return {'code': -1, 'msg': f'缺少必要参数 {param}'}

    biz_id = data["biz_id"]
    env_name = data["env_name"]
    region_name = data["region_name"]
    modify_type = data["modify_type"]
    module_name = data.get('module_name', None)

    if modify_type not in [2, 3]:
        return {'code': -1, 'msg': '修改的类型有误'}

    # 前端还是根据用户选择的ID主键去删除
    with DBContext('w', None, True) as session:
        biz_info = session.query(BizModels).filter(BizModels.biz_id == biz_id).first()
        if not biz_info:
            return dict(code=-1, msg="业务信息有误，请联系管理员")

        if modify_type == 2 and region_name:
            session.query(TreeAssetModels).filter(TreeAssetModels.biz_id == biz_id,
                                                  TreeAssetModels.env_name == env_name,
                                                  TreeAssetModels.region_name == region_name
                                                  ).delete(synchronize_session=False)
            session.query(TreeModels).filter(TreeModels.biz_id == biz_id,
                                             TreeModels.node_type == modify_type,
                                             TreeModels.parent_node == env_name,
                                             TreeModels.title == region_name
                                             ).delete(synchronize_session=False)

            session.query(TreeModels).filter(TreeModels.biz_id == biz_id,
                                             TreeModels.node_type == modify_type + 1,
                                             TreeModels.grand_node == env_name,
                                             TreeModels.parent_node == region_name
                                             ).delete(synchronize_session=False)

        elif modify_type == 3 and module_name:
            session.query(TreeAssetModels).filter(TreeAssetModels.biz_id == biz_id,
                                                  TreeAssetModels.env_name == env_name,
                                                  TreeAssetModels.region_name == region_name,
                                                  TreeAssetModels.module_name == module_name
                                                  ).delete(synchronize_session=False)
            session.query(TreeModels).filter(TreeModels.biz_id == biz_id,
                                             TreeModels.node_type == modify_type,
                                             TreeModels.grand_node == env_name,
                                             TreeModels.parent_node == region_name,
                                             TreeModels.title == module_name
                                             ).delete(synchronize_session=False)
        else:
            return {"code": -2, "msg": "参数错误"}
    return {"code": 0, "msg": "删除成功"}


def get_tree_env_list(**params) -> dict:
    biz_id = params.get('biz_id')
    if not biz_id:
        return dict(code=-1, msg='租户ID为必填参数')

    with DBContext('r') as session:
        biz_info = session.query(BizModels).filter(BizModels.biz_id == biz_id).first()
        if not biz_info:
            return dict(code=-2, msg='租户ID错误')

        _env_info = session.query(TreeModels.title).filter(TreeModels.node_type == 1,
                                                           TreeModels.biz_id == biz_id).group_by(
            TreeModels.title).all()
        env_list = [env[0] for env in _env_info]
    return dict(msg='获取成功', code=0, data=dict(biz_id=biz_id, biz_name=biz_info.biz_cn_name, env_list=env_list))


def get_tree_form_env_list(**params) -> dict:
    biz_id = params.get('biz_id')
    if not biz_id:
        return dict(code=-1, msg='租户ID为必填参数')

    with DBContext('r') as session:
        biz_info = session.query(BizModels).filter(BizModels.biz_id == biz_id).first()
        if not biz_info:
            return dict(code=-4, msg='租户ID错误')

        _env_info = session.query(TreeModels.id, TreeModels.title).filter(TreeModels.node_type == 1,
                                                                          TreeModels.biz_id == biz_id).all()
        env_list = [{"text": s[1], "value": s[1], "id": s[0]} for s in _env_info]
    return dict(msg='获取成功', code=0, data=env_list)


def get_tree_form_set_list(**params) -> dict:
    biz_id = params.get('biz_id')
    env_name = params.get('env_name', 'prod')
    if not biz_id:
        return dict(code=-1, msg='租户ID为必填参数')

    if not env_name:
        return dict(code=-2, msg='环境为必填参数')

    with DBContext('r') as session:
        biz_info = session.query(BizModels).filter(BizModels.biz_id == biz_id).first()
        if not biz_info:
            return dict(code=-4, msg='租户ID错误')

        _set_info = session.query(TreeModels.id, TreeModels.title).filter(TreeModels.node_type == 2,
                                                                          TreeModels.biz_id == biz_id,
                                                                          TreeModels.parent_node == env_name).order_by(
            TreeModels.node_sort, TreeModels.id).all()
        set_list = [{"text": s[1], "value": s[1], "id": s[0]} for s in _set_info]

    return dict(msg='获取成功', code=0, data=set_list)


def get_tree_form_module_list(**params) -> dict:
    biz_id = params.get('biz_id')
    env_name = params.get('env_name')
    set_name = params.get('set_name') if params.get('set_name') else params.get('region_name')

    if not biz_id:
        return dict(code=-1, msg='租户ID为必填参数')

    if not env_name:
        return dict(code=-2, msg='环境为必填参数')

    if not set_name:
        return dict(code=-3, msg='集群为必填参数')

    with DBContext('r') as session:
        biz_info = session.query(BizModels).filter(BizModels.biz_id == biz_id).first()
        if not biz_info:
            return dict(code=-4, msg='租户ID错误')

        _m_info = session.query(TreeModels.id, TreeModels.title).filter(TreeModels.node_type == 3,
                                                                        TreeModels.biz_id == biz_id,
                                                                        TreeModels.grand_node == env_name,
                                                                        TreeModels.parent_node == set_name).order_by(
            TreeModels.node_sort, TreeModels.id).all()
        module_list = [{"text": s[1], "value": s[1], "id": s[0]} for s in _m_info]

    return dict(msg='获取成功', code=0, data=module_list)


def get_tree_module_list(**params) -> dict:
    biz_id = params.get('biz_id')
    env_name = params.get('env_name')
    set_name = params.get('set_name') if params.get('set_name') else params.get('region_name')

    if not biz_id:
        return dict(code=-1, msg='租户ID为必填参数')

    if not env_name:
        return dict(code=-2, msg='环境为必填参数')

    if not set_name:
        return dict(code=-3, msg='集群为必填参数')

    with DBContext('r') as session:
        biz_info = session.query(BizModels).filter(BizModels.biz_id == biz_id).first()
        if not biz_info:
            return dict(code=-4, msg='租户ID错误')

        _m_info = session.query(TreeModels).filter(TreeModels.node_type == 3,
                                                   TreeModels.biz_id == biz_id,
                                                   TreeModels.grand_node == env_name,
                                                   TreeModels.parent_node == set_name).order_by(
            TreeModels.node_sort, TreeModels.id).all()
        module_list = queryset_to_list(_m_info)

    return dict(msg='获取成功', code=0, data=module_list)


def register_asset(data: dict) -> dict:
    mock = {
        "biz_id": "88",
        "env_name": "pre",
        "server_data": [
            "集群a  servername  mysql_name",
            "集群a  servername  mysql_name"
        ]
    }
    server_data = data.get('server_data')
    biz_id = data.get('biz_id')
    env_name = data.get('env_name')
    asset_type = data.get('asset_type', 'server')

    if not server_data:
        return {"code": -1, "msg": "数据不能为空"}

    server_list = server_data.split()
    if not isinstance(server_list, list):
        return {"code": -1, "msg": "数据格式错误"}

    _the_models = mapping.get(asset_type)
    with DBContext('w', None, True) as session:
        for row in server_list:
            region_name = row[0]
            __filter_map = dict(biz_id=biz_id, env_name=env_name, region_name=region_name)

            module_list = session.query(TreeAssetModels.module_name).filter_by(**__filter_map).all()
            module_set = set(m[0] for m in module_list)

            asset_id: Optional[int] = session.query(_the_models.id).filter(_the_models.name == row['name']).first()
            for module_name in module_set:
                __filter_map = dict(biz_id=biz_id, env_name=env_name, region_name=region_name, module_name=module_name,
                                    asset_type=asset_type, asset_id=asset_id)

                exist_asset = session.query(TreeAssetModels).filter_by(**__filter_map).first()

    return {"code": 0, "msg": "注册成功"}


###########
def get_tree_attr(params: Dict[str, Any]) -> Tuple[dict, int]:
    filter_map = dict(biz_id=params.get('biz_id'), title=params.get('env_name'))
    if params.get('module_name'):
        filter_map.update(dict(title=params.get('module_name'), parent_node=params.get('region_name'),
                               grand_node=params.get('env_name')))
    elif params.get('region_name'):
        filter_map.update(dict(title=params.get('region_name'), parent_node=params.get('env_name')))
    # print(params, filter_map)
    with DBContext('r', None, None) as session:
        ext_info_set = session.query(TreeModels.ext_info).filter_by(**filter_map).first()
        if not ext_info_set: return {}, 0
        ext_info = ext_info_set[0]
    if not ext_info: return {}, 0
    return ext_info, len(ext_info)


def get_tree_assets(params: Dict[str, Any]) -> Tuple[list or dict, int]:
    """
    获取Tree节点下的详细资产信息或者节点属性信息
    :param params:
    :return:
    """
    # TODO 这里查询优化 走多个方法查询
    page_size = params.get('page_size', 10)
    page_number = params.get('page_number', 1)
    page_number = (int(page_number) - 1) * int(page_size)
    search_val = params.get('search_val', '')
    asset_type = params.get('asset_type', 'server')
    # 删除其他元素
    pop_list = ['page_size', 'page_number', 'search_val', 'nodeKey', 'selected', '__ob__', 'length']
    [params.pop(val) for val in pop_list if val in params]
    # 属性处理
    if asset_type == 'attr':
        return get_tree_attr(params)

    with DBContext('r', None, None) as session:
        _the_models = mapping.get(asset_type)
        # 因为主机名都在元数据表里面
        # if asset_type !=
        query_ids: List[Tuple[int]] = session.query(_the_models.id).filter(
            or_(_the_models.name.like(f"%{search_val}%"))).all()
        query_ids: List[int] = [i[0] for i in query_ids]
        TreeAssetModelsPrimaryID = TypeVar('TreeAssetModelsPrimaryID', bound=int)
        AssetModelsPrimaryID = TypeVar('AssetModelsPrimaryID', bound=int)
        # TODO 这里拆分到多个方法里面

        # 查询tree关系
        tree_query = session.query(TreeAssetModels).filter_by(**params).filter(
            TreeAssetModels.asset_type == asset_type, TreeAssetModels.asset_id.in_(query_ids)
        )
        tree_data: List[TreeAssetModels] = tree_query.offset(int(page_number)).limit(int(page_size)).all()
        tree_count: int = tree_query.count()
        tree_mapping: Dict[TreeAssetModelsPrimaryID, TreeAssetModels] = {i.id: i for i in tree_data}  # 查询的资源
        # TODO 这里拆分到多个方法里面
        # 基础资源映射
        asset_ids = {i.asset_id for i in tree_data}
        asset_data: List[_the_models] = session.query(_the_models).filter(_the_models.id.in_(asset_ids)).all()
        asset_mapping: Dict[AssetModelsPrimaryID, _the_models] = {i.id: i for i in asset_data}

        # TODO 这里if判断后面抽象方法+映射
        result: List[dict] = []
        for _id, tree in tree_mapping.items():
            asset: _the_models = asset_mapping[tree.asset_id]
            res = {
                'cloud_name': asset.cloud_name, 'account_id': asset.account_id, 'instance_id': asset.instance_id,
                'region': asset.region, 'zone': asset.zone, 'is_expired': asset.is_expired, 'name': asset.name,
                # 业务字段
                'id': tree.id, 'biz_id': tree.biz_id, 'is_enable': tree.is_enable, 'env_name': tree.env_name,
                'region_name': tree.region_name, 'module_name': tree.module_name, 'asset_type': tree.asset_type,
                'asset_id': tree.asset_id, 'ext_info': tree.ext_info
            }
            if asset_type == 'server':
                res.update({
                    'inner_ip': asset.inner_ip, 'outer_ip': asset.outer_ip, 'state': asset.state,
                    'agent_status': asset.agent_status, 'agent_id': asset.agent_id,
                    'outer_biz_addr': asset.outer_biz_addr, 'is_product': asset.is_product,
                })
            elif asset_type == 'mysql':
                res.update({
                    'state': asset.state, 'db_class': asset.db_class, 'db_engine': asset.db_engine,
                    'db_version': asset.db_version, 'db_address': asset.db_address
                })
            elif asset_type == 'redis':
                res.update({
                    'state': asset.state, 'instance_class': asset.instance_class,
                    'instance_arch': asset.instance_arch, 'instance_address': asset.instance_address,
                    'instance_type': asset.instance_type, 'instance_version': asset.instance_version,
                })
            elif asset_type == 'lb':
                res.update({
                    'type': asset.type, 'dns_name': asset.dns_name, 'state': asset.state,
                    'lb_vip': asset.lb_vip, 'endpoint_type': asset.endpoint_type,
                })
            result.append(res)
    return result, tree_count


def _get_biz_value(value: str = None):
    if not value:
        return True
    return or_(
        TreeAssetModels.biz_id == value
    )


# 根据服务器内网IP查询主机拓扑
def get_server_tree_for_api(**params: Dict[str, Any]) -> dict:
    asset_type = 'server'
    biz_id = params.get('biz_id')
    inner_ip = params.get('inner_ip')

    __model = mapping[asset_type]
    with DBContext('r') as session:
        __info = session.query(TreeAssetModels).outerjoin(__model,
                                                          __model.id == TreeAssetModels.asset_id).filter(
            _get_biz_value(biz_id), __model.inner_ip == inner_ip, TreeAssetModels.asset_type == asset_type,
                                    TreeAssetModels.is_enable == 1).all()

    return dict(code=0, msg='获取成功', data=queryset_to_list(__info))
