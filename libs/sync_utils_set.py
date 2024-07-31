#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/2/8 17:56
Desc    : 同步数据专用
"""

import json
import datetime
import logging
import os
import time
import traceback
from typing import List, Union, Any

from shortuuid import uuid
from concurrent.futures import ThreadPoolExecutor
from settings import settings
from loguru import logger
from websdk2.tools import RedisLock
from websdk2.configs import configs
from websdk2.cache_context import cache_conn
from sqlalchemy import func, and_
from collections import defaultdict
from typing import *
##
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.model_utils import insert_or_update
from websdk2.client import AcsClient
from websdk2.api_set import api_set

from models.business import BizModels, PermissionGroupModels
from models.asset import AssetServerModels, AssetVSwitchModels
from models.cloud_region import CloudRegionModels
from models.cloud import SyncLogModels

from libs.api_gateway.jumpserver.user import jms_user_api
from libs.api_gateway.jumpserver.user_group import jms_user_group_api
from libs.api_gateway.jumpserver.asset import jms_asset_api
from libs.api_gateway.jumpserver.asset_hosts import jms_asset_host_api
from libs.api_gateway.jumpserver.asset_perms import jms_asset_permission_api
from libs.api_gateway.jumpserver.asset_accounts import jms_asset_account_template_api
from libs.api_gateway.jumpserver.org import jms_org_api

from services.tree_service import get_tree_by_api
from services.tree_asset_service import get_tree_assets
from services.perm_group_service import preview_perm_group_for_api
from services.cloud_region_service import update_server_agent_id_by_cloud_region_rules

if configs.can_import: configs.import_dict(**settings)


def deco(cls, release=False, **kw):
    def _deco(func):
        def __deco(*args, **kwargs):
            key_timeout, func_timeout = kw.get("key_timeout", 240), kw.get(
                "func_timeout", 90)
            if not cls.get_lock(cls, key_timeout=key_timeout,
                                func_timeout=func_timeout): return False
            try:
                return func(*args, **kwargs)
            finally:
                # 执行完就释放key，默认不释放
                if release: cls.release(cls)

        return __deco

    return _deco


def biz_sync():
    @deco(RedisLock("async_biz_to_cmdb_redis_lock_key"))
    def index():
        logging.info(f'开始从权限中心同步业务信息到配置平台')
        get_mg_biz = dict(method='GET', url=f'/api/p/v4/biz/',
                          description='获取租户数据')
        try:
            # 实例化client
            client = AcsClient()
            response = client.do_action(**get_mg_biz)
            all_biz_list = json.loads(response).get('data')
            biz_info_map = {}
            for biz in all_biz_list:
                biz_id = str(biz.get('biz_id'))
                biz_info_map[biz_id] = biz.get('biz_cn_name',
                                               biz.get('biz_en_name'))
                with DBContext('w', None, True) as session:
                    try:
                        session.add(
                            insert_or_update(BizModels, f"biz_id='{biz_id}'",
                                             biz_id=biz_id,
                                             biz_en_name=biz.get('biz_en_name'),
                                             biz_cn_name=biz.get('biz_cn_name'),
                                             resource_group=biz.get(
                                                 'biz_cn_name'),
                                             sort=biz.get('sort'),
                                             life_cycle=biz.get('life_cycle'),
                                             corporate=biz.get('corporate')))

                    except Exception as err:
                        logging.error(f'同步业务信息到配置平台出错 1 {err}')

            biz_info_map = json.dumps(biz_info_map)
            redis_conn = cache_conn()
            redis_conn.set("BIZ_INFO_STR", biz_info_map)

        except Exception as err:
            logging.error(f'同步业务信息到配置平台出错 2 {err}')
        logging.info(
            f'从权限中心同步业务信息到配置平台结束 {datetime.datetime.now()}')

    index()


def sync_agent_status():
    @deco(RedisLock("async_agent_status_redis_lock_key"))
    def index():
        logging.info(f'开始同步agent状态到配置平台')
        # 实例化client
        client = AcsClient()
        get_agent_list = dict(method='GET', url=f'/api/agent/v1/agent/info', description='获取Agent List')
        res = client.do_action_v2(**get_agent_list)
        if res.status_code != 200:
            return
        data = res.json()
        agent_list = data.keys()
        the_model = AssetServerModels
        with DBContext('w', None, True) as session:
            __info = session.query(the_model.id, the_model.agent_id,
                                   the_model.agent_status).all()
            all_info = [
                dict(id=asset_id,
                     agent_status='2') if agent_status == '1' and agent_id not in agent_list else
                dict(id=asset_id, agent_status='1') if (
                                                               agent_status == '2' or not agent_status) and agent_id in agent_list else
                None for asset_id, agent_id, agent_status in __info
            ]

            all_info = list(filter(None, all_info))

            for info in all_info:
                logging.info(
                    f"{info['id']} 改为{'在线' if info['agent_status'] == '1' else '离线'} ")

            session.bulk_update_mappings(the_model, all_info)
        logging.info(f'同步agent状态到配置平台 结束 {datetime.datetime.now()}')

    try:
        index()
    except Exception as err:
        logging.error(f'同步agent状态到配置平台出错 {str(err)}')


def clean_sync_logs():
    @deco(RedisLock("clean_sync_logs_redis_lock_key"))
    def index():
        week_ago = datetime.datetime.now() - datetime.timedelta(days=7)
        logging.info(f'开始清理资源同步日志  {week_ago}之前 !!!')
        with DBContext('w', None, True) as session:
            session.query(SyncLogModels).filter(
                SyncLogModels.sync_time < week_ago).delete(
                synchronize_session=False)

    try:
        index()
    except Exception as err:
        logging.error(f'清理资源同步过期日志出错 {str(err)}')


def async_agent():
    executor = ThreadPoolExecutor(max_workers=1)
    executor.submit(sync_agent_status)


def async_biz_info():
    executor = ThreadPoolExecutor(max_workers=2)
    executor.submit(biz_sync)
    executor.submit(clean_sync_logs)


def sync_users(org_id=None):
    # 同步用户
    def _sync_main(user: dict) -> None:
        """
        主逻辑
        :param user: 用户信息字典，包含'username'和'nickname'
        :return: None
        """
        username = user['username']
        user['name'] = user['nickname']
        try:
            jms_user = jms_user_api.get(username=username, org_id=org_id)
            if jms_user:
                logging.debug(f'JumpServer用户{username}已存在')
                return
            user.update(org_id=org_id)
            res = jms_user_api.create(**user)
            logging.debug(f"同步用户{username}到JumpServer结果：{bool(res)}")
        except Exception as err:
            logging.error(f'同步用户{username}到JumpServer出错 {err}')

    @deco(RedisLock("async_users_to_cmdb_redis_lock_key"))
    def index():
        logging.info(f'开始同步codo用户到JumpServer')
        client = AcsClient()
        resp = client.do_action_v2(**api_set.get_users)
        if resp.status_code != 200:
            logging.debug(f"同步codo用户到JumpServer, 获取用户列表失败: {resp.status_code}")
            return
        resp = resp.json()
        users = [user for user in resp['data'] if user['source'] == 'ucenter' and user['status'] == "0"]  # 过滤
        for user in users:
            _sync_main(user)
        logging.info(f'同步codo用户到JumpServer结束')

    try:
        index()
    except Exception as e:
        logging.error(f'同步codo用户到JumpServer出错 {e}')


def _sync_user_group_to_jms(name: str, org_id: str = None) -> None:
    """
    同步codo用户组到JumpServer
    :param name: 用户组名
    :param org_id: 组织ID
    :return:
    """
    try:
        jms_user_group = jms_user_group_api.get(name=name, org_id=org_id)
        if jms_user_group:
            logging.debug(f'JumpServer用户组{name}已存在')
            return
        res = jms_user_group_api.create(name=name,  org_id=org_id)
        logging.debug(f"同步用户组{name}到JumpServer结果：{res}")
    except Exception as err:
        logging.error(f'同步用户组{name}到JumpServer出错 {err}')


def _sync_user_group_members_to_jms(user_group_name: str, users: List[str], org_id: str = None) -> None:
    """
    同步codo用户组成员到JumpServer
    :param user_group_name: 用户组名
    :param users: 用户列表
    :param org_id:  组织ID
    :return:
    """
    try:
        jms_user_group = jms_user_group_api.get(name=user_group_name, org_id=org_id)
        if not jms_user_group:
            logging.debug(f'JumpServer没有该用户组: {user_group_name}')
            return

        # 获取用户组成员在JumpServer的ID
        jms_user_ids = []
        for username in users:
            jms_user = jms_user_api.get(username=username, org_id=org_id)
            if not jms_user:
                continue
            jms_user_ids.append(jms_user[0]['id'])

        # 更新用户组成员
        res = jms_user_group_api.update(name=user_group_name, users=jms_user_ids, org_id=org_id)
        logging.debug(f'同步用户组{user_group_name}成员到JumpServer: {bool(res)}')

    except Exception as err:
        logging.error(f'同步用户组{user_group_name}成员到JumpServer出错 {err}')


def get_jms_parent_name_by_org_id(org_id: str) -> Optional[str]:
    if org_id:
        jms_org_obj = jms_org_api.get_by_id(org_id=org_id)
        if not jms_org_obj:
            logging.error(f"组织不存在: {org_id}")
            return
        parent_name = f"/{jms_org_obj['name']}/"
    else:
        parent_name = '/Default/'
    return parent_name


def sync_perm_group_and_members(perm_group_id=None, org_id=None):
    # 同步权限分组和权限分组成员
    def index():
        logging.info("开始同步codo权限分组和权限组成员到JumpServer")
        client = AcsClient()
        resp = client.do_action_v2(**api_set.get_all_role_user_v4)
        if resp.status_code != 200:
            return
        resp = resp.json()
        res = resp['data']

        with DBContext('w', None, True) as session:
            try:
                if not perm_group_id:
                    perm_groups = session.query(PermissionGroupModels).all()
                else:
                    perm_groups = session.query(PermissionGroupModels).filter(PermissionGroupModels.id == perm_group_id)
            except Exception as err:
                logging.error(f'查询权限分组异常 {err}')
            for perm_group in perm_groups:
                perm_group_name = perm_group.perm_group_name
                perm_group_users = list()

                # step1 先同步权限组
                _sync_user_group_to_jms(perm_group_name, org_id=org_id)

                # step2 再同步权限组成员
                # 数据转换
                user_group = perm_group.user_group  # 用户组列表
                for user_group_name in user_group:
                    members_dict = res.get(user_group_name)
                    if not members_dict:
                        continue
                    perm_group_users.extend([user.split("(")[0].strip() for user in members_dict])

                _sync_user_group_members_to_jms(user_group_name=perm_group_name, users=list(set(perm_group_users)),
                                                org_id=org_id)

        logging.info("同步codo权限分组和权限分组成员到JumpServer结束")

    try:
        index()
    except Exception as err:
        logging.error(f'同步codo权限分组和权限分组成员到JumpServer出错 {err}')


def sync_service_tree(biz_id=None, org_id=None):
    """
    同步服务树
    :return:
    """

    def create_or_update_node(name: str, parent_id: str, full_name: str):
        """创建或者更新节点
        @name: 节点名
        @parent_id: 父节点id
        @full_name: 节点全名
        """
        jms_asset_node = jms_asset_api.create(name=name, parent_id=parent_id, org_id=org_id)
        if not jms_asset_node:
            temp_name = f'新建节点-{str(uuid())}'
            jms_asset_node = jms_asset_api.create(name=temp_name, parent_id=parent_id, org_id=org_id)
            if jms_asset_node:
                result = jms_asset_api.update(node_id=jms_asset_node['id'], org_id=org_id, name=name, value=name,
                                              full_value=full_name)
                logging.info(f"节点{full_name}更新结果: {bool(result)}")
                if not result:
                    return None
        return jms_asset_node

    def sync_node(nodes):
        for node in nodes:
            try:
                title = node.get('title')
                children = node.get('children', [])
                full_name = node.get('full_name')
                jms_node = jms_asset_api.get(name=full_name, org_id=org_id)
                if jms_node:
                    logging.info(f'节点已存在: {full_name}')
                else:
                    # 当前节点不存在，查询父节点ID创建当前节点
                    parent_name = full_name.rsplit('/', 1)[0]
                    jms_parent_node = jms_asset_api.get(name=parent_name, org_id=org_id)
                    if not jms_parent_node:
                        logging.info(f'父节点不存在：{parent_name}')
                        return

                    parent_id = jms_parent_node[0]['id']
                    jms_node = create_or_update_node(name=title, parent_id=parent_id, full_name=full_name)
                    if not jms_node:
                        logging.error(f"节点创建失败：{title}, parent_id: {parent_id}, full_name: {full_name}")

                if children:
                    # 递归创建子节点
                    sync_node(children)

            except Exception as err:
                logging.error(f"节点创建失败: {err}")

    def add_full_name_to_nodes(nodes, parent_name='/Default/'):
        """
        资产节点增加full_name字段
        full_name: e.g. '/Default/运维项目/台北运维/logbackup'
        :param nodes:
        :param parent_name:
        :return:
        """
        # 确保 parent_name 以斜杠结尾
        if not parent_name.endswith('/'):
            parent_name += '/'

        for node in nodes:
            title = node.get('title')
            children = node.get('children', [])

            full_name = f'{parent_name}{title}'
            node['full_name'] = full_name

            if children:
                add_full_name_to_nodes(children, full_name)

        return nodes

    def index():
        logging.info("开始同步服务树到JumpServer")

        parent_name = get_jms_parent_name_by_org_id(org_id)
        if not parent_name:
            return

        if not biz_id:
            data = get_tree_by_api(**{})
        else:
            data = get_tree_by_api(biz_id=biz_id)
        nodes = data['data']
        nodes = add_full_name_to_nodes(nodes, parent_name=parent_name)
        sync_node(nodes)
        logging.info("同步服务树到JumpServer结束")

    index()


def sync_service_tree_assets(biz_id=None, org_id=None):
    # 同步服务树主机资产

    def add_full_name_to_assets(assets, org_name='/Default/'):
        """
        :param assets:
        :param org_name:
        :return:
        """
        # 确保 org_name 以斜杠结尾
        if not org_name.endswith('/'):
            org_name += '/'

        # 获取所有需要的 biz_id 列表
        biz_ids = {asset['biz_id'] for asset in assets}

        # 批量查询所有业务对象
        with DBContext('w', None, True) as session:
            biz_objs = session.query(BizModels).filter(BizModels.biz_id.in_(biz_ids)).all()

            # 创建一个 biz_id 到 biz_cn_name 的映射
            biz_id_to_name = {biz.biz_id: biz.biz_cn_name for biz in biz_objs}

        def _add_full_name():
            for asset in assets:
                biz_cn_name = biz_id_to_name.get(asset['biz_id'])
                if not biz_cn_name:
                    continue
                env_name = asset['env_name']
                region_name = asset['region_name']
                module_name = asset['module_name']
                full_name = f'{org_name}{biz_cn_name}/{env_name}/{region_name}/{module_name}'
                asset.update(biz_cn_name=biz_cn_name, full_name=full_name)
                yield asset

        return list(_add_full_name())

    def is_ip_in_subnet(ip: str, subnet: str = "10.0.0.0/8") -> bool:
        """
        判断ip是否在网段内
        :param ip: ip地址
        :param subnet: 网段
        :return: bool
        """
        import ipaddress
        try:
            ip_obj = ipaddress.ip_address(ip)
            subnet_obj = ipaddress.IPv4Network(subnet)
            return ip_obj in subnet_obj
        except ValueError:
            return False

    def _sync_main(asset: dict, org_name: str = '/Default/') -> None:
        """
        创建资产
        :param asset:
        :return:
        """
        name = asset['name']
        inner_ip = asset['inner_ip']
        full_name = asset.get('full_name')
        biz_cn_name = asset.get('biz_cn_name')
        biz_id = asset.get("biz_id")
        agent_id = asset.get("agent_id")
        if not agent_id or (":" in agent_id and agent_id.split(":")[1] == '0'):
            logging.debug(f"资产没有划分到云区域, 业务: {biz_cn_name}, INNER_IP: {inner_ip}")
            return
        if not full_name:
            return

        # accounts = []
        # 获取网域和特权账号模板ID
        # with (DBContext('w', None, True) as session):
        #     perm_mapping_obj = session.query(PermissionToJMS) \
        #         .filter(PermissionToJMS.biz_id == biz_id).first()
        #     if not perm_mapping_obj:
        #         logging.info(f"没有配置权限分组和堡垒机账号映射, 业务: {biz_cn_name}")
        #         return

        cloud_region_id = agent_id.split(":")[1]
        with (DBContext('w', None, True) as session):
            cloud_region_obj = session.query(CloudRegionModels) \
                .filter(CloudRegionModels.cloud_region_id == cloud_region_id).first()
            if not cloud_region_obj:
                logging.debug(f"云区域不存在, 云区域ID: {cloud_region_id}")
                return

            jms_domain_id = None
            # 10.0.0.0/8 在这个内网网段的主机，需要指定网域
            if is_ip_in_subnet(inner_ip):
                jms_domain_id = cloud_region_obj.jms_domain_id
                if not jms_domain_id:
                    logging.debug(f"没有配置网域ID, 业务: {biz_cn_name}")
                    return

            jms_account_template_id = cloud_region_obj.jms_account_template
            if not jms_account_template_id:
                logging.debug(f"没有配置特权账号模板ID, 业务: {biz_cn_name}")
                return

            accounts = [{"template": jms_account_template_id}]

        asset_name = full_name.split(org_name)[1] + f'/{name}-{inner_ip}'
        jms_asset_host_obj = jms_asset_host_api.get(name=asset_name, address=inner_ip, org_id=org_id)
        if jms_asset_host_obj:
            # 主机资产已存在
            # todo 更新资产
            logging.debug(f'资产已存在: {asset_name}')
            return

        # 查找节点，创建主机资产
        jump_server_node_obj = jms_asset_api.get(name=full_name, org_id=org_id)
        if jump_server_node_obj:
            node_id = jump_server_node_obj[0]['id']
            jms_asset_host_obj = jms_asset_host_api.create(name=asset_name, address=inner_ip, nodes=[node_id],
                                                           domain=jms_domain_id, accounts=accounts, org_id=org_id)
            logging.info(f"资产创建结果:{bool(jms_asset_host_obj)}")

    def index():
        logging.info("开始同步服务树主机资产到JumpServer")

        parent_name = get_jms_parent_name_by_org_id(org_id)
        if not parent_name:
            return

        if not biz_id:
            assets, count = get_tree_assets(params={"page_size": 9999})
        else:
            assets, count = get_tree_assets(params={"page_size": 9999, "biz_id": biz_id})
        assets = add_full_name_to_assets(assets=assets, org_name=parent_name)
        for asset in assets:
            _sync_main(asset, org_name=parent_name)
        logging.info("同步服务树主机资产到JumpServer结束")

    try:
        index()
    except Exception as err:
        print(traceback.format_exc())
        logging.error(f'同步服务树主机资产到JumpServer出错 {err}')


def grant_perms_for_assets(perm_group_id=None, org_id=None):

    def _grant_perms(name: str, nodes: List[str], user_group: List[str], biz_cn_name: str,
                     perm_account_template_id: str, date_start: str = None, date_expired: str = None):
        """
             同步主逻辑，处理资产权限配置。

             Args:
                 name (str): 资产授权的名称。
                 nodes (list[str]): 资产节点名称列表。
                 user_group (list[str]): 用户组名称列表。
                 biz_cn_name (str): 业务中文名称。
                 perm_account_template_id (str): JumpServer待推送到服务器的账号模版ID。
                 date_start (str): 权限开始时间。
                 date_expired (str): 权限结束时间。
             Returns:
                 None
         """

        def get_node_ids(node_names):
            """获取节点ID列表"""
            node_ids = set()
            for name in node_names:
                jms_node_objs = jms_asset_api.get(name=name, org_id=org_id)
                if not jms_node_objs:
                    logging.error(f"资产节点不存在：{name}")
                    continue
                node_ids.add(jms_node_objs[0]['id'])
            return list(node_ids)

        def get_account_template_info(template_id):
            """获取账号模板信息"""
            template_obj = jms_asset_account_template_api.get_account_template_detail(template_id, org_id=org_id)
            if not template_obj:
                logging.error(f"账号模板不存在：业务: {biz_cn_name}, 模板ID: {template_id}")
                return None
            return template_obj['username']

        try:
            if not nodes:
                logging.debug("资产节点不能为空")
                return

            nodes_ids = get_node_ids(nodes) if nodes else []
            if not nodes_ids:
                logging.debug("资产节点ID列表不能为空")
                return

            if not user_group:
                logging.debug("用户组不能为空")
                return

            jms_user_group_objs = jms_user_group_api.get(name=name, org_id=org_id)
            if not jms_user_group_objs:
                logging.debug(f"用户组不存在：{name}")
                return

            user_group_ids = [jms_user_group_objs[0]['id']]

            # 获取jsm账号模版中待推送账号的用户名
            perm_account_template_username = get_account_template_info(perm_account_template_id)
            if not perm_account_template_username:
                return

            # 指定账号，选择模板添加时，会自动创建资产下不存在的账号并推送
            accounts = ["@SPEC", perm_account_template_username, f'%{perm_account_template_id}']

            jms_asset_permission_obj = jms_asset_permission_api.get(name=name, org_id=org_id)

            if not jms_asset_permission_obj:
                # 创建资产授权
                result = jms_asset_permission_api.create(name=name, nodes=nodes_ids, user_groups=user_group_ids,
                                                         accounts=accounts, org_id=org_id, date_start=date_start,
                                                         date_expired=date_expired)
                logging.debug(f"创建资产授权: {name} {bool(result)}")
            else:
                # 更新资产授权
                result = jms_asset_permission_api.update(assets_permissions_id=jms_asset_permission_obj[0]['id'],
                                                         name=name, nodes=nodes_ids, user_groups=user_group_ids,
                                                         accounts=accounts, org_id=org_id)
                logging.debug(f'资产授权已存在: {name}, 更新 {bool(result)}')

            # # 创建账号推送
            # push_name = f'{perm_account_template_username}_{str(uuid())}'
            # jms_account_push_obj = jms_account_push_api.create(name=push_name, accounts=[perm_account_template_username], nodes=nodes_ids)
            # if not jms_account_push_obj:
            #     logging.info("创建账号推送失败")
            #     return
            #
            # # 手动执行账号推送
            # jms_push_task = jms_account_push_execution_api.post(automation=jms_account_push_obj['id'])
            # if not jms_push_task:
            #     logging.error("手动执行账号推送任务失败")
            #     return

            # # 查看推送任务状态 #TODO 待优化
            # time.sleep(30)
            # jms_push_task_history = jms_account_push_execution_api.get(push_id=jms_push_task['task'])
            # if not jms_push_task_history or jms_push_task_history['status'] != 'success':
            #     logging.error("手动执行账号推送任务状态失败")
            #     return
            #
            # jms_account_push_api.delete(automation_id=jms_account_push_obj['id'])
            #
            # # 手动推送的账号更新到账号列表
            # accounts = ["@SPEC", "@SPEC", jms_account_template_username, jms_account_name,
            #             f'%{jms_account_template_id}']
            # result = jms_asset_permission_api.update(assets_permissions_id=jms_asset_permission_obj[0]['id'],
            #                                          name=name, nodes=nodes_ids, user_groups=user_group_ids,
            #                                          accounts=accounts)
            # print(result)

        except Exception as e:
            logging.error(f"同步主机资产权限配置失败: {e}")

    def _get_asset_nodes(biz_cn_name: str, env_name: str, region_name: str,
                         module_name: str, org_name='/Default/'):
        """
        资产节点列表
        :param biz_cn_name: 业务中文名
        :param env_name: 环境
        :param region_name: 集群
        :param module_name: 模块
        :return: e.g. ['/Default/运维项目/台北运维/logbackup'， ...]
        """
        if region_name:
            region_name = (region_name.replace(';', ' ').
                           replace(',', ' ').replace('，', ' ')).split(" ")
        else:
            region_name = []

        if module_name:
            module_name = (module_name.replace(';', ' ').
                           replace(',', ' ').replace('，', ' ')).split(" ")
        else:
            module_name = []

        if not region_name and not module_name:
            return [f'{org_name}{biz_cn_name}/{env_name}']
        nodes = []
        for i in range(len(region_name)):
            node_name = f'{org_name}{biz_cn_name}/{env_name}/{region_name[i]}'
            if module_name:
                # 分组模块
                for j in range(len(module_name)):
                    nodes.append(node_name + f'/{module_name[j]}')
            else:
                nodes.append(node_name)
        return list(set(nodes))

    def index():
        # 根据权限分组对资产节点-用户组授权
        logging.info("开始对JumpServer资产-用户组授权")

        with DBContext('w', None, True) as session:
            try:
                if not perm_group_id:
                    perm_groups = session.query(PermissionGroupModels).all()
                else:
                    perm_groups = session.query(PermissionGroupModels).filter(PermissionGroupModels.id == perm_group_id).all()
            except Exception as err:
                logging.error(f'查询权限分组异常 {err}')
                raise

            for perm_group in perm_groups:
                biz_obj = session.query(BizModels).filter(
                    BizModels.biz_id == perm_group.biz_id).first()
                if not biz_obj:
                    logging.debug(f'没有查到业务, ID: {perm_group.biz_id}')
                    continue

                # perm_mapping_obj = session.query(PermissionToJMS) \
                #     .filter(and_(PermissionToJMS.perm_type == perm_group.perm_type),
                #             PermissionToJMS.biz_id == biz_obj.biz_id).first()
                # if not perm_mapping_obj:
                #     logging.info(f"没有配置权限分组和堡垒机账号映射, 业务: {biz_obj.biz_cn_name}, "
                #                  f"权限类型: {perm_group.perm_type}")
                #     continue
                exec_uuid = perm_group.exec_uuid
                # 获取全部主机
                servers = preview_perm_group_for_api(exec_uuid_list=[exec_uuid])['data']

                if not servers:
                    logging.debug(f"没有查到主机, 分组: {perm_group.perm_group_name}")
                    continue

                # 设定属于同一个业务的主机在一个云区域
                servers = [server for server in servers if server.get('agent_id') and server.get('agent_id').split(":")[1] != '0']
                agent_id = max(servers, key=servers.count)['agent_id']
                cloud_region_id = agent_id.split(":")[1]

                # 获取云区域
                cloud_region_obj = session.query(CloudRegionModels).filter(CloudRegionModels.cloud_region_id == cloud_region_id).first()
                if not cloud_region_obj:
                    logging.debug(f"没有查到云区域, 云区域ID: {cloud_region_id}")
                    continue

                jms_account_template_id = cloud_region_obj.jms_account_template
                if not jms_account_template_id:
                    logging.debug(f"没有配置jms特权账号模板ID：业务: {biz_obj.biz_cn_name}, 权限类型: {perm_group.perm_type}")
                    continue

                perm_type = perm_group.perm_type
                accounts = cloud_region_obj.accounts
                if not accounts:
                    logging.debug(f"没有配置jms账号：业务: {biz_obj.biz_cn_name}, 权限类型: {perm_group.perm_type}")
                    continue

                for account in accounts:
                    if account.get('account_type') == perm_type:
                        perm_account_template_id = account.get('jms_account_template_id')
                        break
                else:
                    logging.debug(f"没有配置jms账号：业务: {biz_obj.biz_cn_name}, 权限类型: {perm_group.perm_type}")
                    continue

                biz_cn_name = biz_obj.biz_cn_name
                jms_org_id = perm_group.jms_org_id
                if not jms_org_id:
                    logging.debug(f"堡垒机企业版没有配置组织ID, 业务: {biz_cn_name}")
                    continue

                parent_name = get_jms_parent_name_by_org_id(jms_org_id)
                if not parent_name:
                    continue

                nodes = _get_asset_nodes(biz_cn_name=biz_cn_name, env_name=perm_group.env_name,
                                         region_name=perm_group.region_name, module_name=perm_group.module_name,
                                         org_name=parent_name)

                _grant_perms(name=perm_group.perm_group_name, nodes=nodes, user_group=perm_group.user_group,
                             biz_cn_name=biz_cn_name, perm_account_template_id=perm_account_template_id,
                             date_start=perm_group.perm_start_time,
                             date_expired=perm_group.perm_end_time)

        logging.info("对JumpServer资产-用户组授权结束")

    try:
        index()
    except Exception as err:
        logging.error(f'对JumpServer资产-用户组授权出错 {err}')


def sync_service_trees():
    @deco(RedisLock("async_service_trees_to_cmdb_redis_lock_key"))
    def index():
        # 先同步服务树
        sync_service_tree()
        # 同步服务树主机资产
        sync_service_tree_assets()

    index()


def sync_perm_groups():
    @deco(RedisLock("async_perm_groups_to_cmdb_redis_lock_key"))
    def index():
        # 先同步权限组和权限组成员
        sync_perm_group_and_members()
        # 权限组关联的资产对用户组授权
        grant_perms_for_assets()
    index()


def async_users():
    executor = ThreadPoolExecutor(max_workers=1)
    executor.submit(sync_users)


def async_perm_groups():
    executor = ThreadPoolExecutor(max_workers=1)
    executor.submit(sync_perm_groups)


def async_service_trees():
    executor = ThreadPoolExecutor(max_workers=1)
    executor.submit(sync_service_trees)


def sync_vswitch_cloud_region_id():
    """同步vswitch的cloud_region_id"""
    @deco(RedisLock("sync_vswitch_cloud_region_id_redis_lock_key"))
    def index():
        logging.info(f'开始同步虚拟子网云区域ID!!!')
        with DBContext('w', None, True) as session:
            # 查询云区域规则
            cloud_regions = session.query(CloudRegionModels).filter(CloudRegionModels.asset_group_rules.isnot(None),
                                                                    CloudRegionModels.auto_update_agent_id == "yes").all()
            asset_group_rules = [dict(asset_group_rules=cloud_region.asset_group_rules[0],
                                      cloud_region_id=cloud_region.cloud_region_id) for cloud_region in cloud_regions]

            # 建立云区域规则vpc_id和cloud_region_id的映射
            mapping = {}
            for asset_group_rule in asset_group_rules:
                for rule in asset_group_rule['asset_group_rules']:
                    if rule['query_name'].lower() == 'vpc':
                        mapping[rule['query_value'][-1]] = asset_group_rule["cloud_region_id"]

            # 更新vswitch的cloud_region_id
            vswitches = session.query(AssetVSwitchModels).all()
            for vswitch in vswitches:
                vpc_id = vswitch.vpc_id.strip()
                cloud_region_id = mapping.get(vpc_id)
                if not cloud_region_id:
                    continue
                vswitch.cloud_region_id = cloud_region_id
            session.commit()
        logging.info(f'同步虚拟子网云区域ID结束!!!')

    try:
        index()
    except Exception as err:
        logging.error(f'同步虚拟子网云区域ID出错 {str(err)}')


def sync_server_cloud_region_id():
    """同步server的cloud_region_id"""
    @deco(RedisLock("sync_server_cloud_region_id_redis_lock_key"))
    def index():
        logging.info(f'开始同步server云区域ID!!!')
        with DBContext('w', None, True) as session:
            # 查询自动更新的云区域
            cloud_regions = session.query(CloudRegionModels).filter(CloudRegionModels.asset_group_rules.isnot(None),
                                                                    CloudRegionModels.auto_update_agent_id == "yes").all()

            # 更新server的agent_id
            for cloud_region in cloud_regions:
                update_server_agent_id_by_cloud_region_rules(cloud_region.asset_group_rules,
                                                             cloud_region.cloud_region_id)
            session.commit()
        logging.info(f'同步server云区域ID结束!!!')

    try:
        index()
    except Exception as err:
        logging.error(f'同步server云区域ID出错 {str(err)}')


def async_vswitch_cloud_region_id():
    executor = ThreadPoolExecutor(max_workers=1)
    executor.submit(sync_vswitch_cloud_region_id)


def async_server_cloud_region_id():
    executor = ThreadPoolExecutor(max_workers=1)
    executor.submit(sync_server_cloud_region_id)


def sync_cmdb_to_jms_with_enterprise(perm_group_id=None, with_lock=True):
    """同步配置平台数据到JumpServer企业版和社区版"""

    # @deco(RedisLock("sync_cmdb_to_jms_with_enterprise_redis_lock_key"))
    def index(group_id=None):
        with DBContext('w', None, True) as session:
            try:
                if not group_id:
                    perm_groups = session.query(PermissionGroupModels).all()
                else:
                    perm_groups = session.query(PermissionGroupModels).filter(
                        PermissionGroupModels.id == group_id).all()
            except Exception as err:
                logging.error(f'查询权限分组异常 {err}')
                raise
            for perm_group in perm_groups:
                try:
                    group_id = perm_group.id
                    biz_id = perm_group.biz_id
                    jms_org_id = perm_group.jms_org_id
                    if not jms_org_id:
                        logging.debug(f"堡垒机企业版同步没有配置组织ID, 业务: {biz_id}")
                        continue
                    # 同步用户组和成员
                    sync_perm_group_and_members(perm_group_id=group_id, org_id=jms_org_id)
                    # 同步服务树
                    sync_service_tree(biz_id=biz_id, org_id=jms_org_id)
                    # 同步服务树主机资产
                    sync_service_tree_assets(biz_id=biz_id, org_id=jms_org_id)
                    # 授权
                    grant_perms_for_assets(perm_group_id=group_id, org_id=jms_org_id)
                except Exception as e:
                    logging.error(f"同步配置平台数据到JumpServer企业版出错 {e}")

    try:
        logging.info("开始对同步配置平台数据到JumpServer企业版")
        if with_lock:
            deco(RedisLock("sync_cmdb_to_jms_with_enterprise_redis_lock_key"))(index)(perm_group_id)
        else:
            index(group_id=perm_group_id)
    except Exception as e:
        logging.error(f"同步配置平台数据到JumpServer企业版出错 {e}")
    logging.info("同步配置平台数据到JumpServer企业版结束")


def async_cmdb_to_jms_with_enterprise(perm_group_id=None):
    executor = ThreadPoolExecutor(max_workers=1)
    executor.submit(sync_cmdb_to_jms_with_enterprise, perm_group_id, True)


if __name__ == '__main__':
    pass