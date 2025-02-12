# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/12/24
# @Description: Description
import ipaddress
import json
from enum import unique
from typing import List, Dict, Union
import logging

from pydantic import BaseModel, ValidationError, field_validator, model_validator
from sqlalchemy import or_, event, and_
from sqlalchemy.sql.elements import BooleanClauseList
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.sqlalchemy_pagination import paginate
from websdk2.model_utils import CommonOptView
from websdk2.client import AcsClient
from websdk2.configs import configs

from models import AssetServerModels
from services.tree_asset_service import get_biz_ids_by_server_ip
from services.cloud_region_service import get_servers_by_cloud_region_id
from services.asset_server_service import get_unique_servers
from services import CommonResponse
from models.agent import AgentModels
from settings import settings

opt_obj = CommonOptView(AgentModels)

if configs.can_import: configs.import_dict(**settings)

class Agent(BaseModel):
    ip: str
    hostname: str
    proxy_id: str
    agent_id: str
    version: str
    workspace: str
    biz_ids: List[str] = []
    asset_server_id: int = None
    agent_type: str 

    @model_validator(mode="before")
    def val_must_not_null(cls, values):
        if "ip" not in values or not values.get("ip"):
            raise ValueError("ip不能为空")
        if "proxy_id" not in values or not values.get("proxy_id"):
            raise ValueError("proxy_id不能为空")
        if "agent_id" not in values or not values.get("agent_id"):
            raise ValueError("agent_id不能为空")
        if "hostname" not in values or not values.get("hostname"):
            raise ValueError("hostname不能为空")
        if "version" not in values or not values.get("version"):
            raise ValueError("version不能为空")
        if "agent_type" not in values or not values.get("agent_type"):
            raise ValueError("agnet_type不能为空")
        return values

    
    @field_validator("ip")
    def check_ip(cls, v):
        try:
            ipaddress.ip_address(v)
        except ValueError:
            raise ValueError("ip地址格式错误")
        return v

    @field_validator("proxy_id")
    def check_proxy_id(cls, v):
        try:
            int(v)
        except ValueError:
            raise ValueError("proxy_id格式错误")
        return v


class SetAgentServerId(BaseModel):
    id : int
    asset_server_id: int

    @model_validator(mode="before")
    def val_must_not_null(cls, values):
        if "id" not in values or not values.get("id"):
            raise ValueError("agent id不能为空")
        if "asset_server_id" not in values or not values.get("asset_server_id"):
            raise ValueError("server id不能为空")
        return values

def exist_agent(agent_id: str) -> bool:
    """判断agent是否存在
    Args:
        agent_id (str): agent_id
    Returns:
        bool: 是否存在
    """
    try:
        with DBContext('r') as session:
            return (
                session.query(AgentModels)
                .filter(AgentModels.agent_id == agent_id)
                .count() > 0
            )
    except Exception as e:
        return False


# 监听 biz_id 字段变更
@event.listens_for(AgentModels.biz_ids, 'set')
def watch_biz_id_changed(target, value, oldvalue, initiator):
    if oldvalue != value and oldvalue is not None:
        target._biz_id_changed = True

@event.listens_for(AgentModels, 'before_insert')
def before_insert_listener(mapper, connection, target):
    pass


@event.listens_for(AgentModels, 'after_update')
def after_update_listener(mapper, connection, target):
    """更新后处理"""
    if getattr(target, '_biz_id_changed', False):
        callback = AgentCallback(target)
        callback.on_update()
        if hasattr(target, '_biz_id_changed'):
            delattr(target, '_biz_id_changed')

@event.listens_for(AgentModels, 'after_delete')
def after_delete_listener(mapper, connection, target):
    """删除后处理"""
    pass

def register_agent_for_api(**data) -> CommonResponse:
    """注册agent
    Args:
        data (dict): agent信息
    Returns:
        int: 业务id
    """
    # 参数校验
    try:
        agent = Agent(**data)
    except ValidationError as e:
        return CommonResponse(code=-1, msg=f"参数错误:{str(e)}")
    
    if agent.agent_type.upper() != "NORMAL":
        # 非normal类型的节点直接返回
        return CommonResponse(code=0, msg="注册成功", data=['0'])
    del agent.agent_type
    # 查询主机所属业务
    biz_ids = get_biz_ids_by_server_ip(agent.ip)
    if exist_agent(agent.agent_id):
        return CommonResponse(code=0, msg=f"agent已存在:{agent.agent_id}", data=biz_ids)

    # 查询云区域关联的主机
    matched_server = None
    servers = get_servers_by_cloud_region_id(agent.proxy_id)
    for server in servers:
        if server.inner_ip == agent.ip and server.state == "运行中":
            matched_server = server
            break

    if not matched_server:
        unique_servers = get_unique_servers()
        matched_server = unique_servers.get(agent.ip)

    if matched_server:
        agent.asset_server_id = matched_server.id

    agent.biz_ids = json.dumps(biz_ids, ensure_ascii=False)

    # 创建agent
    try:
        with DBContext('w', None, True) as session:
            agent_model = AgentModels(**agent.model_dump())
            session.add(agent_model)
    except Exception as e:
        return CommonResponse(code=-1, msg=f"注册失败:{str(e)}")
    return CommonResponse(code=0, msg="注册成功", data=biz_ids)


def _get_agent_by_val(value: str = None):
    """
    查询agent条件
    :param value:
    :return:
    """
    if not value:
        return True
    return or_(
        AgentModels.ip.like(f'%{value}%'), AgentModels.hostname.like(f'%{value}%'),
        AgentModels.proxy_id.like(f'%{value}%'), AgentModels.agent_id.like(f'%{value}%'),
    )


def _get_agent_by_filter(search_filter: str = None) -> List[Union[bool, BooleanClauseList]]:
    """获取agent查询过滤条件

    Args:
        search_filter: 过滤类型
            - yes: 已关联服务器
            - no: 未关联服务器
            - None: 无过滤条件

    Returns:
        查询过滤条件列表
    """
    if not search_filter:
        return [True]

    filters = {
        "yes": [
            and_(
                AgentModels.asset_server_id.isnot(None),
                AgentModels.asset_server_id != ""
            )
        ],
        "no": [
            or_(
                AgentModels.asset_server_id.is_(None),
                AgentModels.asset_server_id == ""
            )
        ]
    }

    return filters.get(search_filter, [True])


def get_agent_list_for_api(**params) -> CommonResponse:
    """获取agent列表
    Args:
        params (dict): 参数
    Returns:
        dict: agent列表
    """
    value = params.get('searchValue') or params.get('searchVal')
    filter_map = params.pop('filter_map', {})
    if 'page_size' not in params:
        params['page_size'] = 300  # 默认获取到全部数据
    if 'order' not in params:
        params['order'] = 'descend'
    search_filter = params.pop('search_filter', None)
    with DBContext('r') as session:
        page = paginate(session.query(AgentModels).filter(*_get_agent_by_filter(search_filter),
                                                          _get_agent_by_val(value)).filter_by(**filter_map), **params)
    return CommonResponse(msg='获取成功', code=0, count=page.total, data=page.items)


def update_agent_for_api(data: dict) -> CommonResponse:
    """更新agent
    Args:
        data (dict): agent信息
    Returns:
        dict: 更新结果
    """
    try:
        agent = Agent(**data)
    except ValidationError as e:
        return CommonResponse(code=-1, msg=f"参数错误: {str(e)}")
    try:
        with DBContext('w', None, True) as session:
            agent_obj = session.query(AgentModels).filter(AgentModels.agent_id == agent.agent_id).first()
            if not agent_obj:
                return CommonResponse(code=-1, msg=f"agent不存在：{agent.agent_id}")
            # 显示更新字段
            for key, value in agent.model_dump().items():
                setattr(agent_obj, key, value)
            session.commit()
    except Exception as e:
        return CommonResponse(code=-1, msg=f"更新agent失败：{str(e)}")
    return CommonResponse(code=0, msg="更新成功")


def set_asset_server_id_for_api(data: dict) -> CommonResponse:
    """设置agent关联的服务器
    Args:
        data (dict): agent信息
    Returns:
        dict: 更新结果
    """
    try:
        model = SetAgentServerId(**data)
    except ValidationError as e:
        return CommonResponse(code=-1, msg=f"参数错误: {str(e)}")
    try:
        with DBContext('w', None, True) as session:
            agent_obj = session.query(AgentModels).filter(AgentModels.id == model.id).first()
            if not agent_obj:
                return CommonResponse(code=-1, msg=f"agent不存在：{model.agent_id}")
            server = session.query(AssetServerModels).filter(AssetServerModels.id == model.asset_server_id).first()
            if not server:
                return CommonResponse(code=-1, msg=f"服务器不存在：{model.asset_server_id}")
            agent_obj.asset_server_id = model.asset_server_id
            server.agent_id = agent_obj.agent_id
            session.commit()
    except Exception as e:
        return CommonResponse(code=-1, msg=f"设置agent关联的服务器失败：{str(e)}")
    return CommonResponse(code=0, msg="设置成功")


def delete_agent_for_api(data: dict) -> CommonResponse:
    """删除agent
    Args:
        data (dict): agent信息
    Returns:
        dict: 删除结果
    """
    try:
        agent = Agent(**data)
    except ValidationError as e:
        return CommonResponse(code=-1, msg=f"参数错误: {str(e)}")

    try:
        with DBContext('w', None, True) as session:
            query = session.query(AgentModels).filter(AgentModels.agent_id == agent.agent_id).first()
            session.delete(query)
            session.commit()
    except Exception as e:
        return CommonResponse(code=-1, msg=f"删除agent失败：{str(e)}")
    return CommonResponse(code=0, msg="删除成功")


class AgentCallback:
    """
    agent回调
    """
    def __init__(self, agent: Agent) -> None:
        self.agent = agent
        self.client = AcsClient()


    def send_request(self, body: Dict[str, Union[str, List[str]]]):
        """
        发送请求
        :return:
        """
        try:
            response = self.client.do_action_v2(url="/api/agent/v1/hook/agent-biz-change", method="post", body=body)
            if response.status_code != 200:
                logging.error(f"agent回调请求状态码非200: {response.text}")
                return
            resp = response.json()
            if resp.get("status") != 0:
                logging.error(f"agent回调请求失败: {resp}")
                return
            logging.info(f"agent回调请求成功: {resp}")
        except Exception as e:
            logging.error(f"agent回调请求失败: {str(e)}")

    def on_update(self):
        """
        更新成功回调
        :return:
        """
        body = {
            "agent_id": self.agent.agent_id,
            "biz_ids": json.loads(self.agent.biz_ids) if (self.agent.biz_ids and isinstance(self.agent.biz_ids, str)) else []
        }
        self.send_request(body)

