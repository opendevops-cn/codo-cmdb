#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023年4月7日
"""
import json
import logging
from sqlalchemy import func, or_
from typing import *
from models.tree import TreeModels, TreeAssetModels
from libs.tree import Tree
from models.business import BizModels, SetTempModels
# from models import asset_mapping as mapping
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.model_utils import model_to_dict, queryset_to_list


def add_tree_by_api(data) -> dict:
    biz_id = data.get('biz_id', None)
    node_type = data.get('node_type', None)
    node_sort = data.get('node_sort', None)
    title = data.get('title', None)
    grand_node = data.get('grand_node', None)
    parent_node = data.get('parent_node', None)
    expand = data.get('expand', False)
    detail = data.get('detail', None)
    create_from = data.get('create_from', None)
    temp_id = data.get('temp_id', None)
    ext_info = data.get('ext_info', {})

    if not all([biz_id, node_sort, title, parent_node]):
        return {"code": 1, "msg": "缺少必要参数"}

    if not isinstance(biz_id, str):
        return {"code": 1, "msg": "项目ID必须是字符串类型"}

    if node_type not in [0, 1, 2, 3]:
        return {"code": 1, "msg": "Type类型错误"}

    with DBContext('w', None, True) as session:
        if node_type == 2: env_title = parent_node
        if node_type == 3:
            env_title = grand_node
            if not grand_node:  return {"code": 1, "msg": "模块添加必须要爷爷"}

        filter_map = dict(biz_id=biz_id, title=title, parent_node=parent_node, node_type=node_type)
        if node_type == 3: filter_map['grand_node'] = grand_node
        exist_id = session.query(TreeModels.id).filter_by(**filter_map).first()
        if exist_id:
            return {"code": 1, "msg": f"{title} already exists."}
        # 判断是否是基于模板创建
        if create_from == "模板创建" and temp_id:
            set_temp_items = []
            temp_data = session.query(SetTempModels.temp_data).filter(SetTempModels.id == temp_id).first()
            if temp_data:  set_temp_items = temp_data[0]['items']
            # module_list = [item['module_name'] for item in set_temp_items]
            module_list = []
            for item in set_temp_items:
                try:
                    module_ext_info = json.loads(item['ext_info'])
                except Exception as err:
                    module_ext_info = dict()
                module_list.append((item['module_name'], module_ext_info))
            if module_list:
                # 先添加集群
                session.add(TreeModels(biz_id=biz_id, title=title, node_type=node_type, ext_info=ext_info,
                                       node_sort=node_sort, parent_node=parent_node, expand=expand, detail=detail))
                # 再往集群里面自动加入模块 2023年3月20日 修改模块类型为3
                session.add_all(
                    [TreeModels(biz_id=biz_id, title=module_info[0], grand_node=parent_node, ext_info=module_info[1],
                                parent_node=title, node_type=3, node_sort=100, expand=False)
                     for module_info in module_list])
            else:
                return {"code": 0, "msg": "不能从模板里面获取到模块信息"}
        else:
            new_info = dict(biz_id=biz_id, title=title, node_type=node_type, ext_info=ext_info,
                            node_sort=node_sort, parent_node=parent_node, expand=expand, detail=detail)
            if node_type == 3: new_info['grand_node'] = env_title
            session.add(TreeModels(**new_info))
            # session.add(TreeModels(biz_id=biz_id, title=title, node_type=node_type,grand_node=env_title,
            #                        node_sort=node_sort, parent_node=parent_node, expand=expand, detail=detail))
        session.commit()
    return {"code": 0, "msg": "success"}


def put_tree_by_api(data) -> dict:
    tree_id = data.get('id', None)
    biz_id = data.get("biz_id", None)
    node_type = data.get('node_type', None)
    node_sort = data.get('node_sort', None)
    title = data.get('title', None)
    parent_node = data.get('parent_node', None)
    expand = data.get('expand', False)
    ext_info = data.get('ext_info', {})
    detail = data.get('detail', None)

    if not all([biz_id, tree_id, node_sort, title, parent_node]):
        return {"code": 1, "msg": "缺少必要参数"}

    if not isinstance(biz_id, str):
        return {"code": 1, "msg": "项目ID必须是字符串类型"}

    if node_type not in [0, 1, 2, 3]:
        return {"code": 1, "msg": "Type类型错误"}

    if node_type == 0:
        return {"code": 1, "msg": "Root节点不能编辑"}

    with DBContext('w', None, True) as session:
        try:
            # title + node + type 必须是唯一的
            session.query(TreeModels).filter(
                TreeModels.biz_id == biz_id, TreeModels.id == tree_id
            ).update({
                TreeModels.title: title, TreeModels.parent_node: parent_node, TreeModels.node_type: node_type,
                TreeModels.ext_info: ext_info,
                TreeModels.node_sort: node_sort, TreeModels.expand: expand, TreeModels.detail: detail
            })
            session.commit()
        except Exception as err:
            logging.error(f'Tree节点更新失败,{err}')
            return {"code": 1, "msg": f'Tree节点更新失败,{err},请确认名称是否重复'}
    return {"code": 0, "msg": "更新完成"}


def patch_tree_by_api(data) -> dict:
    tree_list = data.get('tree_list', None)  # tree_list = ["id":1, "ext_info":{"xx":"xxx"}]
    tree_id = data.get('tree_id', None)
    attr_key = data.get('attr_key', None)
    attr_val = data.get('attr_val', None)
    if tree_list:
        with DBContext('w', None, True) as session:
            session.bulk_update_mappings(TreeModels, tree_list)
        return {"code": 0, "msg": "更新完成"}
    elif attr_key:
        with DBContext('w', None, True) as session:
            session.query(TreeModels).filter(TreeModels.id == tree_id).update(
                {TreeModels.ext_info: func.json_set(TreeModels.ext_info, "$." + attr_key, attr_val)},
                synchronize_session='fetch')
        return {"code": 0, "msg": f"更新{attr_key}完成"}
    return {"code": 1, "msg": "缺少必要参数"}


def del_tree_by_api(data) -> dict:
    tree_id = data.get('id', None)
    biz_id = data.get('biz_id', None)
    title = data.get('title', None)
    parent_node = data.get('parent_node', None)
    node_type = data.get('node_type', None)

    if not all([tree_id, biz_id, title]):
        return {"code": 1, "msg": "关键参数不能为空"}

    if node_type not in [0, 1, 2, 3]:
        return {"code": 1, "msg": "Type类型错误"}

    if node_type == 0:
        return {"code": 1, "msg": "根节点不能删除"}

    with DBContext('w', None, True) as session:
        if node_type == 1:
            exist_children = session.query(TreeModels.id).filter(
                TreeModels.biz_id == biz_id, TreeModels.parent_node == title, TreeModels.node_type == 2).all()
        elif node_type == 2:
            exist_children = session.query(TreeModels.id).filter(
                TreeModels.biz_id == biz_id, TreeModels.grand_node == parent_node,
                TreeModels.parent_node == title, TreeModels.node_type == 3).all()
        else:
            exist_children = None

        if exist_children:
            return {"code": 1, "msg": f"当前业务，{title}节点为其他节点的父节点,禁止删除！"}
        # 判断节点下是否有数据
        if node_type == 3:
            env_name = session.query(TreeModels.grand_node).filter(TreeModels.id == tree_id).first()
            if not env_name:
                return {"code": 1, "msg": "数据格式有误，请刷新页面后重试"}
            env_name = env_name[0]
            exist_data = session.query(TreeAssetModels.id).filter(
                TreeAssetModels.biz_id == biz_id,
                TreeAssetModels.env_name == env_name,
                TreeAssetModels.region_name == parent_node,
                TreeAssetModels.module_name == title).first()
            if exist_data:
                return {"code": 1, "msg": f"/{env_name}/{parent_node}/{title}节点下存在业务数据,删除失败!"}
        # del TreeID
        session.query(TreeModels).filter(TreeModels.id == tree_id).delete(synchronize_session=False)

    return {"code": 0, "msg": "节点删除成功"}


def get_tree_by_api(**params) -> dict:
    biz_id = params.get('biz_id')
    with DBContext('r') as session:
        if not biz_id:
            tree_list = get_tree(session, get_all_biz(session))
        else:
            tree_list = get_tree(session, {biz_id: get_biz_name(session=session, biz_id=biz_id)})
    return {"code": 0, "msg": "获取成功", "data": tree_list}


def get_tree_count(session, biz_id: Optional[str], asset_type: Optional[str] = 'server') -> Union[int]:
    """
    获取一个业务有多少主机数量
    """
    biz_count = session.query(TreeAssetModels).filter(
        TreeAssetModels.asset_type == asset_type, TreeAssetModels.biz_id == biz_id).count()

    return biz_count


def get_env_count(session, biz_id: Optional[str], asset_type: Optional[str] = 'server') -> Dict[str, int]:
    """
    获取一个业务有多少主机数量
    """
    env_info = session.query(TreeAssetModels.env_name, func.count(TreeAssetModels.asset_id)
                             ).filter(TreeAssetModels.asset_type == asset_type,
                                      TreeAssetModels.biz_id == biz_id).group_by(TreeAssetModels.env_name).all()
    mappings: Dict[str, int] = {}
    for res in env_info:
        _env_name, _count = res
        mappings[_env_name] = _count
    return mappings


def get_node_info(session, biz_id: str) -> Dict[str, dict]:
    """
    获取业务下子节点对应的主机数量
    :param session:
    :param biz_id:
    """
    node_hosts = session.query(TreeAssetModels.env_name, TreeAssetModels.region_name, TreeAssetModels.module_name,
                               func.count(TreeAssetModels.asset_id)
                               ).filter(
        TreeAssetModels.biz_id == biz_id).group_by(TreeAssetModels.env_name, TreeAssetModels.region_name,
                                                   TreeAssetModels.module_name).all()

    mappings: Dict[str, Dict[str, Dict[str, int]]] = {}
    for res in node_hosts:
        _env_name, _set_name, _module_name, _count = res
        if not mappings.get(_env_name, None):
            mappings[_env_name] = {}
        if _set_name not in mappings[_env_name]:
            mappings[_env_name][_set_name] = {}
        mappings[_env_name][_set_name][_module_name] = _count
    return mappings


def get_biz_name(
        session,
        biz_id: str
) -> str:
    """
    biz_id 查询Name
    :param session:
    :param biz_id:
    :return:
    """
    biz_name = session.query(BizModels.biz_cn_name).filter(BizModels.biz_id == biz_id).first()
    return biz_name[0] if biz_name else 'Unknown'


def get_all_biz(
        session
) -> Dict[str, str]:
    """
    获取所有的业务id+name
    :param session:
    :return:
    """
    biz_list: List[Tuple[int, str]] = session.query(BizModels.biz_id, BizModels.biz_cn_name).all()
    return {biz_id: biz_name for biz_id, biz_name in biz_list}


def build_tree(session, biz_id: str, biz_name: str) -> Dict[str, Any]:
    """
    生成树
    :return:
    """
    biz_count: int = get_tree_count(biz_id=biz_id, session=session)
    env_count: dict = get_env_count(biz_id=biz_id, session=session)
    node_info: dict = get_node_info(biz_id=biz_id, session=session)
    tree_data = session.query(TreeModels).filter(TreeModels.biz_id == biz_id).all()
    # 一级默认
    the_tree: List[Dict[str, str]] = [
        {
            "biz_id": biz_id, "title": biz_name, "node_type": 0, "node_sort": 1, "parent_node": "Root", "expand": True,
            "contextmenu": True, "children": [], "count": biz_count
        }
    ]
    for item in tree_data:
        data_dict = model_to_dict(item)
        data_dict['count'] = 0
        # 写入节点主机数量
        try:
            if data_dict['node_type'] == 1:
                data_dict['count'] = env_count.get(data_dict['title'], 0)
            elif data_dict['node_type'] == 2:
                data_dict['count'] = sum(node_info[data_dict['parent_node']][data_dict['title']].values())
            elif data_dict['node_type'] == 3:
                data_dict['count'] = node_info[data_dict['grand_node']][data_dict['parent_node']][data_dict['title']]
        except Exception as error:
            logging.debug(f"获取节点主机数量失败: {error}")
            # 这里没有数据的情况下会报错，不用管
            pass
        data_dict.pop('create_time')
        data_dict.pop('update_time')
        the_tree.append(data_dict)
    return Tree(the_tree).build()


def get_tree(
        session,
        biz_data: Dict[str, str]
) -> List[dict]:
    """
    生成业务树信息返回前端
    :param session:
    :param biz_data:
    :return:
    """
    tree_list: List[Dict[str, Any]] = []
    for biz_id, biz_name in biz_data.items():
        tree_list.append(build_tree(session, biz_id, biz_name))
    return tree_list


def get_tree_info_by_api(**params) -> dict:
    biz_id = params.get('biz_id')
    grand_node = params.get('grand_node')
    parent_node = params.get('parent_node')
    title = params.get('title')
    node_type = int(params.get('node_type', 3))

    # 先检查是否支持当前类型
    if node_type not in [2, 3]:
        return {"code": -1, "msg": "不支持当前类型"}

    with DBContext('r') as session:
        # 检查业务信息是否存在
        if not session.query(BizModels.biz_id).filter(BizModels.biz_id == biz_id).scalar():
            return {"code": -2, "msg": "业务信息有误，请联系管理员"}

        # 构建查询的基础部分
        query = session.query(TreeModels).filter_by(biz_id=biz_id, node_type=node_type, title=title)

        # 根据node_type添加额外的过滤条件
        if node_type == 2:
            query = query.filter_by(parent_node=parent_node)
        else:  # node_type == 3
            if not grand_node:
                return {"code": -4, "msg": "缺少参数 grand_node"}
            query = query.filter_by(grand_node=grand_node, parent_node=parent_node)

        # 执行查询并获取第一个结果
        tree_info = query.first()
        if not tree_info:
            return {"code": -3, "msg": "未找到对应的树信息"}

    return {"code": 0, "msg": "获取成功", "data": model_to_dict(tree_info)}
