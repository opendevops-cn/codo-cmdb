#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/2/15 14:59
Desc    : 云区域
"""

from models.base import TimeBaseModel
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, Integer, Text, UniqueConstraint, JSON

Base = declarative_base()


class CloudRegionModels(TimeBaseModel):
    __tablename__ = 't_cloud_region'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column('name', String(100), unique=True, comment='规则名称')
    cloud_region_id = Column('cloud_region_id', String(30), unique=True, nullable=False, comment='代理ID、云区域ID')
    proxy_ip = Column('proxy_ip', String(180), comment='代理地址 一般是内网地址')
    ssh_user = Column('ssh_user', String(30), default="root", comment='ssh user')
    ssh_ip = Column('ssh_ip', String(180), default="", comment='ssh ip 通过SSH链接地址')
    ssh_port = Column('ssh_port', Integer, default=22220, comment='SSH端口')
    ssh_key = Column('ssh_key', Text(), default="", comment='SSH网域密钥')
    ssh_pub_key = Column('ssh_pub_key', Text(), default="", comment='SSH网域公钥')
    asset_group_rules = Column('asset_group_rules', JSON(), nullable=False, default=[], comment='资产组规则')
    auto_update_agent_id = Column('auto_update_agent_id', String(30), default='no', comment='自动更新server AgentID')

    jms_org_id = Column('jms_org_id', String(80), default="", comment='对应跳板机组织ID')
    jms_account_template = Column('jms_account_template', String(255), default="", comment='对应跳板机账号模版')
    jms_domain_id = Column('jms_domain_id', String(255), default="", comment='对应跳板机网域ID')
    accounts = Column('accounts', JSON(), default=[], comment='对应跳板机账号模板组')
    state = Column('state', String(10), default="online", comment='代理状态')
    detail = Column('detail', String(500), comment='备注')

    __table_args__ = (
    )


class CloudRegionAssetModels(Base):
    __tablename__ = 't_cloud_region_asset'  # 云区域&资产关联表
    id = Column(Integer, primary_key=True, autoincrement=True)
    region_id = Column(Integer, nullable=False, comment='云区域关联ID')
    cloud_region_id = Column('cloud_region_id', String(50), comment='代理ID、云区域ID')
    asset_type = Column('asset_type', String(20), default="server", comment='资产类型')
    asset_id = Column(Integer, nullable=False, comment='资产ID')
    __table_args__ = (
        UniqueConstraint('region_id', 'asset_type', 'asset_id', name='region_id_and_asset_id_unique'),
    )
