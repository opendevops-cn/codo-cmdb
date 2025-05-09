# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2025/2/13
# @Description: Description

import datetime
import logging
from collections import Counter, defaultdict
from typing import Dict, List, Set

from websdk2.api_set import api_set
from websdk2.client import AcsClient
from websdk2.configs import configs
from websdk2.db_context import DBContext
from websdk2.tools import RedisLock

from libs import deco
from libs.scheduler import scheduler
from models import TreeAssetModels
from models.agent import AgentModels
from models.asset import AgentBindStatus, AssetServerModels
from services.asset_server_service import get_unique_servers
from services.cloud_region_service import get_servers_by_cloud_region_id
from settings import settings

if configs.can_import:
    configs.import_dict(**settings)


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


def bind_agent_tasks():
    """
    检查agent是否能绑定主机
    如果能绑定则更新agent的asset_server_id，同时更新server的agent_id
    """

    @deco(RedisLock("agent_binding_tasks_redis_lock_key"), release=True)
    def index():
        logging.info("开始agent绑定主机！！！")
        bind_agents()
        logging.info("agent绑定主机结束！！！")

    try:
        index()
    except Exception as err:
        logging.error(f"agent绑定主机出错 {str(err)}")


def bind_agents() -> Set[str]:
    """
    绑定agent到服务器
    :return: 未绑定的agent ID集合
    """
    unbound_agents = set()
    with DBContext("w", None, True) as session:
        agents = session.query(AgentModels).all()
        unique_servers = get_unique_servers()
        for agent in agents:
            # 若agent已绑定，则跳过
            if agent.asset_server_id:
                continue
            try:
                matched_server = find_matched_server(agent, unique_servers)
                if not matched_server:
                    unbound_agents.add(f"【{agent.hostname}|{agent.ip}|{agent.agent_id}】")
                    continue

                # 更新agent的asset_server_id
                agent.asset_server_id = matched_server.id
                agent.agent_bind_status = AgentBindStatus.AUTO_BIND
                # 更新server的agent_id 只更新增量数据, 忽略存量数据
                if matched_server.agent_id == "0":
                    server = session.query(AssetServerModels).filter(AssetServerModels.id == matched_server.id).first()
                    server.agent_id = agent.agent_id
                    server.agent_bind_status = AgentBindStatus.AUTO_BIND
            except Exception as err:
                logging.error(f"更新agent出错 {str(err)}")
        session.commit()
    return unbound_agents


def find_matched_server(agent: AgentModels, unique_servers: Dict[str, AssetServerModels]) -> AssetServerModels:
    """
    查找匹配的服务器
    :param agent: Agent对象
    :param unique_servers: 唯一服务器字典
    :return: 匹配的服务器对象或None
    """
    # 查找云区域关联的云主机, 且云主机没有设置主agent，已绑定主agent的云主机不再绑定
    servers = get_servers_by_cloud_region_id(agent.proxy_id)
    for server in servers:
        if server.inner_ip == agent.ip and server.state == "运行中" and not server.has_main_agent:
            return server

    # 若 servers 没匹配到，则在 unique_servers 里找
    return unique_servers.get(agent.ip)


def notify_unbound_agents_tasks(unbound_agents: Set[str] = None) -> None:
    """
    发送未匹配agent的告警
    :param unbound_agents: 未匹配的agent ID集合
    """

    @deco(RedisLock("notify_unbound_agents_tasks_redis_lock_key", release=True))
    def index():
        unbound_agents = bind_agents()
        if unbound_agents:
            body = {
                "agent_ids": "\n".join(list(unbound_agents)),
                "alert_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "title": "【CMDB】agent未匹配主机",
            }
            send_router_alert(params={"cmdb_agent_not_match": 1}, body=body)

    try:
        index()
    except Exception as err:
        logging.error(f"发送未匹配agent告警出错 {str(err)}")


def filter_ingore_tree_alert_servers(servers: List[AssetServerModels]) -> List[AssetServerModels]:
    """
    过滤掉不需要发送告警的服务器
    :param servers: 服务器列表
    :return: 过滤后的服务器列表
    """
    ingore_keywords = configs.get("ignore_tree_alert_keywords", [])
    if not ingore_keywords:
        return servers
    if not isinstance(ingore_keywords, str):
        return servers
    ingore_keywords_list = ingore_keywords.split(",,,")
    if not ingore_keywords_list:
        return servers
    return [server for server in servers if not any(keyword in server.name for keyword in ingore_keywords_list)]


def get_unbound_servers(session):
    """
    获取未绑定服务树的服务器
    :param session: 数据库会话
    :return: 未绑定服务树的服务器列表
    """
    tree_asset_ids = session.query(TreeAssetModels.asset_id).filter(TreeAssetModels.asset_type == "server").all()
    tree_asset_ids = [item[0] for item in tree_asset_ids]

    servers = (
        session.query(AssetServerModels)
        .filter(
            AssetServerModels.state == "运行中",
            AssetServerModels.is_expired.is_(False),
            AssetServerModels.id.notin_(tree_asset_ids),
        )
        .all()
    )

    # 过滤掉不需要发送告警的服务器
    return filter_ingore_tree_alert_servers(servers)


def bind_server_tasks():
    """
    检查server是否绑定服务树, 如果未绑定则发送告警
    # todo: 抽象通知中心告警，发送不同类型的告警逻辑
    :return:
    """

    @deco(RedisLock("server_binding_tasks_redis_lock_key"), release=True)
    def index():
        logging.info("开始检查server是否绑定服务树！！！")
        with DBContext("w", None, True) as session:
            # 获取所有绑定服务树的server
            servers = get_unbound_servers(session)
            if servers:
                # 1. 归类（基于前10个字符）
                grouped_servers = defaultdict(list)
                for server in servers:
                    prefix = server.name[:10] if len(server.name) >= 10 else server.name  # 截取前10个字符
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
                        "alert_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "servers": "\n".join(
                            [f"【{server.name}|{server.inner_ip}】" for server in ready_to_send_servers]
                        ),
                        "title": "【CMDB】主机未绑定服务树",
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
    scheduler.add_job(
        notify_unbound_agents_tasks,
        "cron",
        hour="9-23",
        minute=0,
        id="notify_unbound_agents_tasks",
    )
    scheduler.add_job(bind_agent_tasks, "cron", minute="*/3", id="bind_agents_tasks", max_instances=1)
    scheduler.add_job(bind_server_tasks, "cron", hour=10, minute=0, id="bind_server_tasks", max_instances=1)
