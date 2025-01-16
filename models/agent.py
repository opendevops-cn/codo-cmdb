#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# @File    :   agent.py
# @Time    :   2024/12/26 09:57:33
# @Author  :   DongdongLiu
# @Version :   1.0
# @Desc    :   agent server 模块
from sqlalchemy import Column,String,Integer,JSON
from sqlalchemy.ext.declarative import declarative_base

from models.base import TimeBaseModel

Base = declarative_base()


class AgentModels(TimeBaseModel):
    __tablename__ = 't_agent'  # agent列表
    id = Column('id', Integer, primary_key=True, autoincrement=True, comment='自增ID')
    ip = Column('ip', String(50), comment='agent ip')
    hostname = Column('hostname', String(50), comment='agent hostname')
    proxy_id = Column('proxy_id', String(50), comment='proxy id')
    version = Column('version', String(50), comment='agent版本')
    agent_id = Column('agent_id', String(150), comment='agent id')
    workspace = Column('workspace', String(500), comment='工作空间')
    ext_info = Column("ext_info", JSON(), comment="扩展字段存JSON")
    asset_server_id = Column(Integer, comment='主机资产ID', index=True, default=0)
    biz_ids = Column('biz_ids', JSON(), comment='业务ID列表', default=[])
    