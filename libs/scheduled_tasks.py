# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2025/2/13
# @Description: Description

import logging
import datetime
from collections import defaultdict, Counter

from websdk2.client import AcsClient
from websdk2.api_set import api_set
from websdk2.db_context import DBContext

from models import TreeAssetModels
from models.asset import AssetServerModels
from models.agent import AgentModels
from libs import deco
from libs.scheduler import scheduler
from websdk2.tools import RedisLock
from services.asset_server_service import get_unique_servers
from services.cloud_region_service import get_servers_by_cloud_region_id


def send_router_alert(params: dict, body: dict):
    """
    发送告警
    """
    client = AcsClient()
    api_set.send_router_alert.update(
        params=params,
        body=body,
    )
    try:
        resp = client.do_action_v2(**api_set.send_router_alert)
        if resp.status_code != 200:
            logging.error(f"发送告警到NOC失败 {resp.status_code}")
    except Exception as err:
        logging.error(f"发送告警到NOC出错 {err}")


def get_unmatched_agents(session):
    """
    获取所有未匹配主机的agent
    :param session: 数据库会话
    :return: 未匹配主机的agent列表
    """
    unmatched_agent_ids = set()
    agents = session.query(AgentModels).all()
    unique_servers = get_unique_servers()

    for agent in agents:
        matched_server = None
        # 查找云区域关联的云主机
        servers = get_servers_by_cloud_region_id(agent.proxy_id)
        for server in servers:
            if server.inner_ip == agent.ip and server.state == "运行中":
                matched_server = server
                break
        if not matched_server:
            matched_server = unique_servers.get(agent.ip)

        if not matched_server:
            unmatched_agent_ids.add(f"【{agent.hostname}|{agent.ip}|{agent.agent_id}】")

    return unmatched_agent_ids


def agent_binding_tasks():
    """
    检查agent是否能绑定主机
    a.如果能绑定则更新agent的asset_server_id，同时更新server的agent_id
    b.如果不能绑定则发送告警
    """

    @deco(RedisLock("agent_binding_tasks_redis_lock_key"))
    def index():
        logging.info("开始更新agent！！！")
        unmatched_agent_ids = set()
        with DBContext("w", None, True) as session:
            agents = session.query(AgentModels).all()
            unique_servers = get_unique_servers()
            for agent in agents:
                try:
                    matched_server = None
                    # 查找云区域关联的云主机
                    servers = get_servers_by_cloud_region_id(agent.proxy_id)
                    for server in servers:
                        if (
                            server.inner_ip == agent.ip
                            and server.state == "运行中"
                        ):
                            matched_server = server
                            break
                    #  若 servers 没匹配到，则在 unique_servers 里找
                    if not matched_server:
                        matched_server = unique_servers.get(agent.ip)

                    # 如果仍未找到 server，则记录 unmatched_agent_id
                    if not matched_server:
                        unmatched_agent_ids.add(
                            f"【{agent.hostname}|{agent.ip}|{agent.agent_id}】"
                        )
                        continue

                    # 更新agent的asset_server_id
                    agent.asset_server_id = matched_server.id
                    # 更新server的agent_id 只更新增量数据, 忽略存量数据
                    if matched_server.agent_id == "0":
                        server = (
                            session.query(AssetServerModels)
                            .filter(AssetServerModels.id == matched_server.id)
                            .first()
                        )
                        server.agent_id = agent.agent_id
                except Exception as err:
                    logging.error(f"更新agent出错 {str(err)}")
            session.commit()
        if unmatched_agent_ids:
            body = {
                "agent_ids": "\n".join(list(unmatched_agent_ids)),
                "alert_time": datetime.datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                'title': "【CMDB】agent未匹配主机",
            }
            send_router_alert(params={"cmdb_agent_not_match": 1}, body=body)
        logging.info("更新agent结束！！！")

    try:
        index()
    except Exception as err:
        logging.error(f"更新agent出错 {str(err)}")


def get_unbound_servers(session):
    """
    获取未绑定服务树的服务器
    :param session: 数据库会话
    :return: 未绑定服务树的服务器列表
    """
    tree_asset_ids = session.query(TreeAssetModels.asset_id).filter(TreeAssetModels.asset_type == "server").all()
    tree_asset_ids = [item[0] for item in tree_asset_ids]

    servers = session.query(AssetServerModels).filter(
        AssetServerModels.state == "运行中",
        AssetServerModels.is_expired.is_(False),
        AssetServerModels.id.notin_(tree_asset_ids)
    ).all()

    # 排除不需要发送告警的服务器
    return [
        server for server in servers
        if not server.name.startswith(("tke-", "node-", "as-tke-"))
    ]

def server_binding_tasks():
    """
    检查server是否绑定服务树, 如果未绑定则发送告警
    :return:
    """

    @deco(RedisLock("server_binding_tasks_redis_lock_key"))
    def index():
        logging.info("开始检查server是否绑定服务树！！！")
        with DBContext("w", None, True) as session:
            # 获取所有绑定服务树的server
            servers = get_unbound_servers(session)
            if servers:
                # 1. 归类（基于前10个字符）
                grouped_servers = defaultdict(list)
                for server in servers:
                    prefix = (
                        server.name[:10] if len(server.name) >= 10 else server.name
                    )  # 截取前10个字符
                    grouped_servers[prefix].append(server)

                # 2. 统计每个分组的数量
                group_counts = {k: len(v) for k, v in grouped_servers.items()}

                # 3. 取 Top 3 最大分组
                top_3_groups = Counter(group_counts).most_common(3)
                ready_to_send_servers = []
                for prefix, size in top_3_groups:
                    ready_to_send_servers += grouped_servers[prefix]

                # 4. 发送告警
                if ready_to_send_servers:
                    body = {
                        "alert_time": datetime.datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                        "servers": "\n".join(
                            [
                                f"【{server.name}|{server.inner_ip}】"
                                for server in ready_to_send_servers
                            ]
                        ),
                        'title': "【CMDB】主机未绑定服务树",
                    }
                    send_router_alert(params={"cmdb_server_not_bind_tree": 1}, body=body)

            logging.info("检查server是否绑定服务树结束！！！")

    try:
        index()
    except Exception as err:
        logging.error(f"检查server是否绑定服务树出错 {str(err)}")


def init_scheduled_tasks():
    """
    初始化定时任务
    """
    scheduler.add_job(agent_binding_tasks, 'cron', minute=0, id='agent_binding_tasks')
    scheduler.add_job(server_binding_tasks, 'cron', hour=10, minute=0, id='server_binding_tasks')