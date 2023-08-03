#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/2/15 14:59
Desc    : 云配置
"""

from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from models.base import TimeBaseModel

Base = declarative_base()


class CloudSettingModels(TimeBaseModel):
    __tablename__ = 't_cloud_settings'  # 云账户配置信息
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column('account_id', String(100), unique=True, nullable=False,
                        comment='AccountUUID')  # 云厂商ID,UUID
    name = Column('name', String(120), nullable=False, comment='名称')
    cloud_name = Column('cloud_name', String(120), nullable=False,
                        comment='云厂商Name')  # aliyun /qcloud /aws / ucloud / dnspod
    region = Column('region', String(255), nullable=False, comment='区域')
    access_id = Column('access_id', String(120), nullable=False, comment='IAM角色访问密钥')
    access_key = Column('access_key', String(255), nullable=False, comment='IAM角色访问密钥')
    is_enable = Column('is_enable', Boolean(), default=False, comment='是否开启')
    interval = Column(Integer, nullable=False, default=30, comment='同步间隔(单位：minutes)')
    detail = Column('detail', Text(), comment='备注')


class SyncLogModels(Base):
    __tablename__ = 't_sync_log'  # server 资产同步Log
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column('name', String(120), nullable=False, comment='名称')
    cloud_name = Column('cloud_name', String(120), nullable=False, comment='云厂商Name')
    account_id = Column('account_id', String(120), nullable=False, index=True, comment='AccountUUID')
    sync_type = Column('sync_type', String(120), comment='主机or数据库')
    sync_region = Column('sync_region', String(120), comment='区域')
    sync_state = Column('sync_state', String(120), comment='同步状态')
    sync_consum = Column('sync_consum', String(120), comment='同步耗时')
    sync_time = Column('sync_time', DateTime(), default=datetime.now, index=True, comment='同步时间')
    loginfo = Column('loginfo', Text(), comment='log')
