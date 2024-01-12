#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/2/15 14:59
Desc    : 服务树
"""

import json
import logging
from abc import ABC
from sqlalchemy import func, or_
from typing import *
from libs.base_handler import BaseHandler
from models.tree import TreeModels, TreeAssetModels
from websdk2.db_context import DBContext
from websdk2.model_utils import queryset_to_list
from services.tree_service import get_biz_name, get_tree_by_api, add_tree_by_api, put_tree_by_api, patch_tree_by_api, \
    del_tree_by_api, get_tree_info_by_api
from services.tree_asset_service import get_tree_env_list, get_tree_form_env_list, get_tree_form_module_list, \
    get_tree_form_set_list, register_asset, del_tree_asset, get_tree_asset_by_api, add_tree_asset_by_api, \
    update_tree_asset_by_api, get_server_tree_for_api, get_tree_module_list, update_tree_leaf, del_tree_leaf

from models import asset_mapping as mapping


class TreeHandler(BaseHandler, ABC):
    def get(self):
        res = get_tree_by_api(**self.params)
        return self.write(res)

    def post(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = add_tree_by_api(data)
        return self.write(res)

    def put(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = put_tree_by_api(data)
        return self.write(res)

    def patch(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = patch_tree_by_api(data)
        return self.write(res)

    def delete(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = del_tree_by_api(data)
        return self.write(res)


class TreeSearchInfoHandler(BaseHandler, ABC):
    def get(self):
        res = get_tree_info_by_api(**self.params)
        return self.write(res)


class TreeAssetHandler(BaseHandler, ABC):

    def get(self):
        res = get_tree_asset_by_api(**self.params)
        return self.write(res)

    def post(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = add_tree_asset_by_api(data)
        return self.write(res)

    def patch(self):
        """
        更改上线状态
        :return:
        """
        data = json.loads(self.request.body.decode("utf-8"))
        res = update_tree_asset_by_api(data)
        return self.write(res)

    def delete(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = del_tree_asset(data)
        return self.write(res)


class TreeLeafHandler(BaseHandler, ABC):
    def get(self):
        pass

    def post(self):
        pass

    def put(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = update_tree_leaf(data)
        return self.write(res)

    def delete(self):
        data = json.loads(self.request.body.decode("utf-8"))
        res = del_tree_leaf(data)
        return self.write(res)


class TreeAssetRelationHandler(BaseHandler, ABC):
    def get(self):
        biz_id = self.get_argument('biz_id', None)
        asset_id = self.get_argument('asset_id', None)
        asset_type = self.get_argument('asset_type', None)

        if not asset_id or not biz_id or not asset_type:
            return self.write({"code": 1, "msg": "关键参数不能为空"})

        with DBContext('r') as session:
            tree_asset_info: List[TreeAssetModels] = session.query(TreeAssetModels).filter(
                TreeAssetModels.biz_id == biz_id, TreeAssetModels.asset_id == asset_id,
                TreeAssetModels.asset_type == asset_type).all()
            biz_en_name = get_biz_name(biz_id=biz_id, session=session)

            # 定义Tree
            _the_host_tree = {
                "name": biz_en_name,
                "children": [],
            }
            # 补充TreeData
            for server in queryset_to_list(tree_asset_info):
                _tree_data = {
                    "name": server.get('env_name'),  # 二层环境
                    "children": [
                        {
                            "name": server.get('region_name'),  # 三层集群
                            "children": [
                                {
                                    "name": server.get('module_name')  # 四层模块
                                }
                            ]
                        }
                    ],
                }
                _the_host_tree['children'].append(_tree_data)

        return self.write({"code": 0, "msg": "获取成功", "data": _the_host_tree})


class TreeRegisterHandler(BaseHandler, ABC):
    """

    """

    @staticmethod
    def add_env(server_list: List[dict]) -> None:
        """
        :return:
        """
        # 所有的环境
        env_list: List[tuple] = [(row['biz_id'], row['biz_name'], row['env_name']) for row in server_list]
        # 去重
        env_list = list(set(env_list))
        # output
        messages = ""
        with DBContext('w', None, True) as session:
            for env_info in env_list:
                biz_id, biz_name, env_name = env_info
                # 查询是否存在
                __exist = session.query(TreeModels.id).filter(TreeModels.biz_id == biz_id, TreeModels.title == env_name
                                                              ).first()
                if not __exist:
                    session.add(
                        TreeModels(biz_id=biz_id, title=env_name, node_type=1, node_sort=100, parent_node=biz_name))
                    messages += f'---Add:业务ID：{biz_id},环境节点: {env_name}'
        logging.info(messages) if messages else logging.info('无新增集群节点')

    @staticmethod
    def add_region(server_list: List[dict]) -> None:
        """
        :return:
        """
        # 所有的region
        region_list: List[tuple] = [(row['biz_id'], row['biz_name'], row['region_name']) for row in server_list]
        # 去重
        region_list = list(set(region_list))
        # output
        messages = ""
        with DBContext('w', None, True) as session:
            for region_info in region_list:
                biz_id, biz_name, region_name = region_info
                # 查询是否存在
                exist_region = session.query(TreeModels.id).filter(
                    TreeModels.biz_id == biz_id, TreeModels.title == region_name
                ).first()
                if not exist_region:
                    session.add(
                        TreeModels(biz_id=biz_id, title=region_name, node_type=1, node_sort=100, parent_node=biz_name))
                    messages += f'---Add:业务ID：{biz_id},集群节点: {region_name}'
        logging.info(messages) if messages else logging.info('无新增集群节点')

    @staticmethod
    def add_module(server_list: List[dict]) -> None:
        """
        :return:
        """
        module_list: List[tuple] = [(row['biz_id'], row['region_name'], row['module_name']) for row in server_list]
        # 去重
        module_list = list(set(module_list))
        # output
        messages = ""
        with DBContext('w', None, True) as session:
            for module_info in module_list:
                biz_id, region_name, module_name = module_info
                exist_region_module_name = session.query(TreeModels).filter(
                    TreeModels.biz_id == biz_id,
                    TreeModels.parent_node == region_name,
                    TreeModels.title == module_name
                ).first()
                # 新增模块(module)节点
                if not exist_region_module_name:
                    session.add(TreeModels(
                        biz_id=biz_id, title=module_name,
                        parent_node=region_name, node_type=2, node_sort=100
                    ))
                    messages += f'---Add:业务ID：{biz_id},集群:{region_name},模块节点: {module_name}'

        logging.info(messages) if messages else logging.info("无新增模块节点")

    @staticmethod
    def add_hosts(server_list: List[dict]) -> None:
        """
        :param server_list:
        :return:
        """
        messages = ""
        # 更新树形关系
        with DBContext('w', None, True) as session:
            for row in server_list:
                # 通过发布平台传来的Name换对应的ID入库
                _the_models = mapping.get(row['asset_type'])
                asset_id: Optional[int] = session.query(_the_models.id).filter(
                    _the_models.name == row['name']).first()
                row['asset_id'] = asset_id[0] if asset_id else None
                if not row.get('asset_id'):
                    logging.error(
                        'Fail:业务ID：{biz_id},集群:{region_name},模块:{module_name},主机:{name}，未找到对应的ID'.format(
                            **row)
                    )
                    continue
                # 是否存在id
                exist_tree_asset = session.query(TreeAssetModels).filter(
                    TreeAssetModels.biz_id == row['biz_id'], TreeAssetModels.region_name == row['region_name'],
                    TreeAssetModels.module_name == row['module_name'], TreeAssetModels.asset_id == row['asset_id'],
                    TreeAssetModels.asset_type == row['asset_type']
                ).first()
                if not exist_tree_asset:
                    session.add(TreeAssetModels(
                        biz_id=row['biz_id'], asset_id=row['asset_id'], asset_type=row['asset_type'],
                        is_enable=row["is_enable"], region_name=row['region_name'], module_name=row['module_name'],
                        ext_info=row['ext_info']
                    ))
                    messages += f'---Add:业务ID：{row["biz_id"]},集群：{row["region_name"]},模块:{row["module_name"]}主机节点: {row["asset_id"]}'
                    continue
                session.query(TreeAssetModels).filter(
                    TreeAssetModels.biz_id == row['biz_id'],
                    TreeAssetModels.region_name == row['region_name'],
                    TreeAssetModels.module_name == row['module_name'],
                    TreeAssetModels.asset_type == row['asset_type'],
                    TreeAssetModels.asset_id == row['asset_id']
                ).update(
                    {
                        TreeAssetModels.is_enable: row["is_enable"],
                        TreeAssetModels.ext_info: row['ext_info']
                    })
                messages += f'---Update:业务ID：{row["biz_id"]},集群：{row["region_name"]},模块:{row["module_name"]}主机节点: {row["asset_id"]}'

        logging.info(messages) if messages else logging.info("无新增主机节点")

    def post(self):
        data = json.loads(self.request.body.decode("utf-8"))
        server_list = data.get('server_list', None)

        if not server_list: return self.write({"code": 1, "msg": "数据不能为空"})

        if not isinstance(server_list, list): return self.write({"code": 1, "msg": "数据格式错误"})

        self.add_env(server_list)
        self.add_region(server_list)
        self.add_module(server_list)
        self.add_hosts(server_list)

        return self.write({"code": 0, "msg": "注册成功"})


class TreeServerRelationHandler(BaseHandler, ABC):
    def get(self):
        biz_id = self.get_argument('biz_id', None)
        inner_ip = self.get_argument('inner_ip', None)

        if not inner_ip:
            return self.write({"code": 1, "msg": "关键参数不能为空"})
        res = get_server_tree_for_api(**self.params)
        return self.write(res)


class TreeRegisterV2Handler(BaseHandler, ABC):
    def post(self):
        data = json.loads(self.request.body.decode("utf-8"))

        res = register_asset(data)

        return self.write(res)


class TreeEnvHandler(BaseHandler, ABC):
    def get(self):
        res = get_tree_env_list(**self.params)
        return self.write(res)


class TreeFormEnvHandler(BaseHandler, ABC):
    def get(self):
        res = get_tree_form_env_list(**self.params)
        return self.write(res)


class TreeFormSetHandler(BaseHandler, ABC):
    def get(self):
        res = get_tree_form_set_list(**self.params)
        return self.write(res)


class TreeFormModuleHandler(BaseHandler, ABC):
    def get(self):
        res = get_tree_form_module_list(**self.params)
        return self.write(res)


class TreeModuleHandler(BaseHandler, ABC):
    def get(self):
        res = get_tree_module_list(**self.params)
        return self.write(res)


tree_urls = [
    (r"/api/v2/cmdb/tree/", TreeHandler, {"handle_name": "配置平台-服务树"}),
    (r"/api/v2/cmdb/tree/env/", TreeEnvHandler, {"handle_name": "配置平台-树-获取业务下环境列表", "method": ["GET"]}),
    (r"/api/v2/cmdb/tree/form/env/", TreeFormEnvHandler,
     {"handle_name": "配置平台-树-获取业务环境列表-form", "method": ["GET"]}),
    (r"/api/v2/cmdb/tree/form/set/", TreeFormSetHandler,
     {"handle_name": "配置平台-树-获取业务环境下集群列表-form", "method": ["GET"]}),
    (r"/api/v2/cmdb/tree/form/module/", TreeFormModuleHandler,
     {"handle_name": "配置平台-树-获取业务环境集群下模块列表-form", "method": ["GET"]}),
    (r"/api/v2/cmdb/tree/module/", TreeModuleHandler,
     {"handle_name": "配置平台-树-获取业务环境集群下模块数据", "method": ["GET"]}),
    (r"/api/v2/cmdb/tree/asset/", TreeAssetHandler, {"handle_name": "配置平台-树-资产关系", "method": ["ALL"]}),
    (r"/api/v2/cmdb/tree/asset/relation/", TreeAssetRelationHandler,
     {"handle_name": "配置平台-树-查询所在拓扑结构", "handle_status": "y", "method": ["ALL"]}),
    (r"/api/v2/cmdb/tree/server/relation/", TreeServerRelationHandler,
     {"handle_name": "配置平台-树-根据内网IP查询关联", "handle_status": "y", "method": ["ALL"]}),
    (r"/api/v2/cmdb/tree/search_info/", TreeSearchInfoHandler, {"handle_name": "配置平台-服务树-查询ID"}),
    (r"/api/v2/cmdb/tree/register/", TreeRegisterHandler,
     {"handle_name": "配置平台-树-数据注册-未测试", "handle_status": "y", "method": ["ALL"]}),
    (r"/api/v2/cmdb/tree/v2/register/", TreeRegisterV2Handler,
     {"handle_name": "配置平台-树-数据注册V2-未测试", "method": ["ALL"]}),
    (r"/api/v2/cmdb/tree/leaf/", TreeLeafHandler, {"handle_name": "配置平台-树-叶子处理", "method": ["ALL"]}),
]
