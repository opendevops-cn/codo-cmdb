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
import time
from shortuuid import uuid
from concurrent.futures import ThreadPoolExecutor
from settings import settings
from loguru import logger
from websdk2.tools import RedisLock
from websdk2.configs import configs
from websdk2.cache_context import cache_conn
##
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.model_utils import insert_or_update
from websdk2.client import AcsClient
from websdk2.api_set import api_set

from models.business import BizModels, PermissionGroupModels
from models.asset import AssetServerModels
from models.cloud import SyncLogModels

from libs.api_gateway.jumpserver.user import UserAPI
from libs.api_gateway.jumpserver.user_group import UserGroupAPI
from libs.api_gateway.jumpserver.asset import AssetAPI
from libs.api_gateway.jumpserver.asset_hosts import AssetHostsAPI
from libs.api_gateway.jumpserver.asset_perms import AssetPermissionsAPI
from libs.api_gateway.jumpserver.asset_accounts import AssetAccountsAPI

from services.tree_service import get_tree_by_api
from services.tree_asset_service import get_tree_assets

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

            # all_info = []
            # for asset_id, agent_id, agent_status, in __info:
            #     if agent_status == '1' and agent_id not in agent_list:  # 如果状态在线  但是agent找不到
            #         ins_log.read_log('info', f'{agent_id}改为离线  {asset_id}')
            #         all_info.append(dict(id=asset_id, agent_status='2'))
            #         # session.query(model).filter(model.id == asset_id).update(**dict(agent_status='2'))
            #     elif (agent_status == '2' or not agent_status) and agent_id in agent_list:  # 如果状态离线  但是agent存在
            #         all_info.append(dict(id=asset_id, agent_status='1'))
            #         ins_log.read_log('info', f'{agent_id}改为在线  { {asset_id} }')
            #         # session.query(model).filter(model.id == asset_id).update(**dict(agent_status='1'))
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


def users_sync():
    # 同步用户
    def _sync_main(user):
        """
        主逻辑
        :return:
        """
        username = user['username']
        user['name'] = user['nickname']
        is_exists = UserAPI().get(username=username)
        if is_exists:
            logging.debug(f'JumpServer用户{username}已存在')
            return
        res = UserAPI().create(**user)
        if res:
            logging.debug(f'同步用户: {username} 到JumpServer成功')
        else:
            logging.error(f'同步用户: {username} 到JumpServer失败: {res}')

    def index():
        logging.info(f'开始同步codo用户到JumpServer')
        client = AcsClient()
        resp = client.do_action_v2(**api_set.get_users)
        if resp.status_code != 200:
            return
        resp = resp.json()
        users = resp['data']
        if not users:
            return
        users = [user for user in users if user['source'] == 'ucenter' and user['status'] == "0"]  # 过滤
        for user in users:
            _sync_main(user)

    try:
        index()
    except Exception as e:
        logging.error(f'同步codo用户到JumpServer出错 {e}')


def user_groups_sync():
    # 同步用户组
    def _sync_main(user_role):
        """
        :param user_role:
        :return:
        """
        name = user_role['role_name']
        is_exists = UserGroupAPI().get(name=name)
        if is_exists:
            logging.debug(f'JumpServer用户组{name}已存在')
            return
        res = UserGroupAPI().create(name=name)
        if res:
            logging.info(f'同步用户组: {name} 到JumpServer成功')
        else:
            logging.error(f'同步用户组: {name} 到JumpServer失败: {res}')

    def index():
        logging.info("开始同步codo用户组到JumpServer")
        client = AcsClient()
        resp = client.do_action_v2(**api_set.get_normal_role_list)
        if resp.status_code != 200:
            return
        resp = resp.json()
        res = resp['data']
        for user_role in res:
            _sync_main(user_role)

    index()


def user_group_members_sync():
    # 同步用户组成员
    def _sync_main(user_group_name: str, members_dict: dict):
        """
        :param user_group_name:
        :param members_dict:
        :return:
        """
        user_group = UserGroupAPI().get(name=user_group_name)
        user_ids = []
        if user_group:
            members = members_dict.keys()
            for user_member in members:
                name = user_member.split('(')[0]
                user = UserAPI().get(username=name)
                if user:
                    user_id = user[0]['id']
                    user_ids.append(user_id)
                else:
                    logging.info(f'JumpServer没有该用户: {name}')
        else:
            logging.info(f'JumpServer没有该用户组: {user_group_name}')
            return
        res = UserGroupAPI().update(name=user_group_name, users=user_ids)
        if res:
            logging.info(f'同步用户组成员: {user_group_name} 到JumpServer成功')
        else:
            logging.error(
                f'同步用户组成员: {user_group_name} 到JumpServer失败: {res}')

    def index():
        logging.info("开始同步codo用户组到JumpServer")
        client = AcsClient()
        resp = client.do_action_v2(**api_set.get_all_role_user_v4)
        if resp.status_code != 200:
            return
        resp = resp.json()
        res = resp['data']
        for user_group_name, members_dict in res.items():
            _sync_main(user_group_name, members_dict)

    index()


def perm_groups_sync(perm_group_id=None):
    # 同步权限组
    def _sync_main(name: str):
        """

        :param name:
        :return:
        """
        is_exists = UserGroupAPI().get(name=name)
        if is_exists:
            logging.info(f'JumpServer权限组{name}已存在')
            return
        res = UserGroupAPI().create(name=name)
        if res:
            logging.info(f'同步权限组: {name} 到JumpServer成功')
        else:
            logging.error(f'同步权限组: {name} 到JumpServer失败: {res}')

    def index():
        logging.info("开始同步codo权限组到JumpServer")
        with DBContext('w', None, True) as session:
            try:
                if not perm_group_id:
                    perm_groups = session.query(PermissionGroupModels).all()
                else:
                    perm_groups = session.query(PermissionGroupModels).filter(PermissionGroupModels.id == perm_group_id)
            except Exception as err:
                logging.error(f'查询权限分组异常 {err}')
            for perm_group in perm_groups:
                _sync_main(perm_group.perm_group_name)

    index()


def perm_group_members_sync():
    # 同步权限组成员
    # 权限组对应jumpServer用户组

    def _sync_main(user_group_name: str, members_dict: dict):
        """
        :param user_group_name:
        :param members_dict:
        :return:
        """
        user_group = UserGroupAPI().get(name=user_group_name)
        user_ids = []
        if user_group:
            members = members_dict.keys()
            for user_member in members:
                name = user_member.split('(')[0]
                user = UserAPI().get(username=name)
                if user:
                    user_id = user[0]['id']
                    user_ids.append(user_id)
                else:
                    logging.info(f'JumpServer没有该用户: {name}')
        else:
            logging.debug(f'JumpServer没有该权限组: {user_group_name}')

        res = UserGroupAPI().update(name=user_group_name, users=user_ids)
        if res:
            logging.info(f'同步权限组成员: {user_group_name} 到JumpServer成功')
        else:
            logging.error(
                f'同步权限组成员: {user_group_name} 到JumpServer失败: {res}')

    def index():
        logging.info("开始同步codo权限组到JumpServer")
        client = AcsClient()
        resp = client.do_action_v2(**api_set.get_all_role_user_v4)
        if resp.status_code != 200:
            return
        resp = resp.json()
        res = resp['data']

        with DBContext('w', None, True) as session:
            try:
                perm_groups = session.query(PermissionGroupModels).all()
            except Exception as err:
                logging.error(f'查询权限分组异常 {err}')
            for perm_group in perm_groups:
                user_group = perm_group.user_group
                user_groups = user_group.split(',')
                for user_group_name in user_groups:
                    members_dict = res.get(user_group_name)
                    if not members_dict:
                        continue
                    _sync_main(perm_group.perm_group_name, members_dict)

    index()


def service_tree_sync(biz_id=None):
    """
    同步服务树
    :return:
    """
    def _sync_main(nodes):
        for node in nodes:
            time.sleep(0.1)
            title = node.get('title')
            children = node.get('children', [])
            full_name = node.get('full_name')
            jump_server_node = AssetAPI().get(name=full_name)
            if not jump_server_node:
                # 当前节点不存在，查询父节点ID创建当前节点
                parent_name = full_name.rsplit('/', 1)[0]
                jump_server_parent_node = AssetAPI().get(name=parent_name)
                if not jump_server_parent_node:
                    logging.info(f'父节点不存在：{parent_name}')
                    continue
                parent_id = jump_server_parent_node[0]['id']
                jump_server_node = AssetAPI().create(name=title, parent_id=parent_id)
                if jump_server_node:
                    logging.info(f'节点创建成功：{full_name}')
                else:
                    # jmss 存在同名节点创建异常的bug，这里用创建临时节点然后修改节点名称的方式兼容
                    name = f'新建节点-{str(uuid())}'
                    jump_server_node = AssetAPI().create(name=name, parent_id=parent_id)
                    if jump_server_node:
                        res = AssetAPI().update(node_id=jump_server_node['id'], name=title, value=title,
                                                full_value=full_name)
                        if res:
                            logging.info(f"节点更新失败：{full_name}")
                        else:
                            logging.error(f"节点更新失败：{full_name}")
                    else:
                        logging.error(f"节点创建失败：{name}, parent_id: {parent_id}, full_name: {full_name}")
            else:
                logging.info(f'节点已存在: {full_name}')

            # 递归创建子节点
            _sync_main(children)

    def _handle_data(nodes, parent_name='/Default/'):
        """
        资产节点数据处理 方便精确查找父节点
        :param nodes:
        :param parent_name:
        :return:
        """
        for node in nodes:
            title = node.get('title')
            children = node.get('children', [])
            if not parent_name.endswith('/'):
                parent_name += '/'
            full_name = f'{parent_name}{title}'
            node.update(full_name=full_name)
            if children:
                _handle_data(children, full_name)
        return nodes

    def index():
        logging.info("开始同步服务树到JumpServer")
        if not biz_id:
            data = get_tree_by_api(**{})
        else:
            data = get_tree_by_api(biz_id=biz_id)
        nodes = data['data']
        nodes = _handle_data(nodes)
        _sync_main(nodes)

    index()


def service_tree_assets_sync(biz_id=None):
    # 同步服务树主机资产

    def _handle_data(assets, org_name='/Default/'):
        """

        :param assets:
        :param org_name:
        :return:
        """
        for asset in assets:
            with DBContext('w', None, True) as session:
                biz_obj = session.query(BizModels).filter(
                    BizModels.biz_id == asset['biz_id']).first()
                if not biz_obj:
                    continue
                biz_cn_name = biz_obj.biz_cn_name
                env_name = asset['env_name']
                region_name = asset['region_name']
                module_name = asset['module_name']
                full_name = f'{org_name}{biz_cn_name}/{env_name}/{region_name}/{module_name}'
                asset.update(biz_cn_name=biz_cn_name, full_name=full_name)
        return assets

    def _sync_main(asset: dict):
        """
        创建资产
        :param asset:
        :return:
        """
        name = asset['name']
        inner_ip = asset['inner_ip']
        full_name = asset.get('full_name')
        if not full_name:
            return
        asset_name = full_name.split('/Default/')[1] + f'/{name}'
        jump_server_asset = AssetHostsAPI().get(name=asset_name, address=inner_ip)
        if not jump_server_asset:
            # 查找节点创建资产
            jump_server_node = AssetAPI().get(name=full_name)
            if jump_server_node:
                node_id = jump_server_node[0]['id']
                jump_server_asset = AssetHostsAPI().create(name=asset_name,
                                                           address=inner_ip,
                                                           nodes=[node_id])
                if jump_server_asset:
                    logging.info(f"资产创建成功:{inner_ip} -- {asset_name}")

        else:
            logging.debug(f'资产已存在: {inner_ip} -- {name}')

    def index():
        logging.info("开始同步服务树主机资产到JumpServer")
        if not biz_id:
            assets, count = get_tree_assets(params={"page_size": 9999})
        else:
            assets, count = get_tree_assets(params={"page_size": 9999, "biz_id": biz_id})
        assets = _handle_data(assets)
        for asset in assets:
            _sync_main(asset)

    index()


def grant_perms_for_assets(perm_group_id=None):

    def _sync_main(name, nodes, user_groups, jmss_accounts):
        nodes_ids = []
        user_group_ids = []
        accounts = []
        # 资产节点
        for node in nodes:
            jump_server_node = AssetAPI().get(name=node)
            if jump_server_node:
                nodes_ids.append(jump_server_node[0]['id'])
        # 用户组
        for user_group in user_groups:
            jump_server_user_group = UserGroupAPI().get(name=user_group)
            if jump_server_user_group:
                user_group_ids.append(jump_server_user_group[0]['id'])
        # 账号
        for jmss_account in jmss_accounts:
            jump_server_assets_account = AssetAccountsAPI().get(username=jmss_account)
            if jump_server_assets_account:
                account_obj = jump_server_assets_account.get('results')
                if account_obj:
                    accounts.append(jmss_account)
        is_exists = AssetPermissionsAPI().get(name=name)
        # 指定账号
        if accounts:
            accounts.append("@SPEC")
        if is_exists:
            logging.debug(f'资产授权已存在: {name}, 执行更新操作')
            res = AssetPermissionsAPI().update(assets_permissions_id=is_exists[0]['id'], name=name, nodes=nodes_ids,
                                               user_groups=user_group_ids, accounts=accounts)
            if res:
                logging.info(f'资产授权更新成功: {name}')

            return
        res = AssetPermissionsAPI().create(name=name, nodes=nodes_ids, user_groups=user_group_ids, accounts=accounts)
        if res:
            logging.info(f"资产授权成功:{name} -- {user_groups}")
        else:
            logging.error(f"资产授权失败:{name} -- {user_groups}")

    def _get_asset_nodes(biz_cn_name: str, env_name: str, region_name: str,
                         module_name: str, org_name='/Default/'):
        """
        资产节点列表
        :param biz_cn_name:
        :param env_name:
        :param region_name:
        :param module_name:
        :return:
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
                    perm_groups = session.query(PermissionGroupModels).filter(PermissionGroupModels.id == perm_group_id)
            except Exception as err:
                logging.error(f'查询权限分组异常 {err}')
            for perm_group in perm_groups:
                biz_obj = session.query(BizModels).filter(
                    BizModels.biz_id == perm_group.biz_id).first()
                if not biz_obj:
                    logging.info(f'查询业务ID异常 {err}')
                    continue
                biz_cn_name = biz_obj.biz_cn_name
                user_group = perm_group.user_group
                env_name = perm_group.env_name
                region_name = perm_group.region_name
                module_name = perm_group.module_name
                nodes = _get_asset_nodes(biz_cn_name, env_name, region_name,
                                         module_name)
                user_groups = user_group.split(',')
                jmss_accounts = perm_group.jmss_account.split(',')
                _sync_main(perm_group.perm_group_name, nodes, user_groups, jmss_accounts)

    index()


def sync_user_info():
    @deco(RedisLock("async_users_to_cmdb_redis_lock_key"))
    def index():
        # 先同步用户
        users_sync()
        # 再同步用户组
        user_groups_sync()
        # 同步用户组成员
        user_group_members_sync()

    index()


def sync_service_trees():
    @deco(RedisLock("async_service_trees_to_cmdb_redis_lock_key"))
    def index():
        # 先同步服务树
        service_tree_sync()
        # 同步主机资产
        service_tree_assets_sync()

    index()


def sync_perm_groups():
    @deco(RedisLock("async_perm_groups_to_cmdb_redis_lock_key"))
    def index():
        # 先同步权限组
        perm_groups_sync()
        # 同步权限组成员
        perm_group_members_sync()
        # 权限组关联的资产对用户组授权
        grant_perms_for_assets()

    index()


def async_user_info():
    executor = ThreadPoolExecutor(max_workers=1)
    executor.submit(sync_user_info)


def async_perm_groups():
    executor = ThreadPoolExecutor(max_workers=1)
    executor.submit(sync_perm_groups)


def async_service_trees():
    executor = ThreadPoolExecutor(max_workers=1)
    executor.submit(sync_service_trees)


if __name__ == '__main__':
    pass
