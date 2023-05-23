#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/2/15 14:59
Desc    : 维护事件 Models
"""

from models.base import TimeBaseModel
from sqlalchemy import Column, String, Integer, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class AwsHealthEventModels(TimeBaseModel):
    __tablename__ = 't_aws_event'
    id = Column('id', Integer, primary_key=True, autoincrement=True)  # ID自增长
    event_arn = Column('event_arn', Text())  # arn唯一标识符，这玩意还很长...
    event_service = Column('event_service', String(120), comment='服务类型')
    event_account_id = Column('event_account_id', String(120), comment='账号ID')
    event_instance_id = Column('event_instance_id', String(120), comment='实例ID')
    event_hostname = Column('event_hostname', String(120), comment='主机名')
    event_type = Column('event_type', String(150), comment='事件类型')
    event_region = Column('event_region', String(150), comment='地区')
    event_start_time = Column(DateTime)
    event_end_time = Column(DateTime)
    event_status = Column('event_status', String(120), comment='状态')  # upcoming 计划维护，closed: 关闭
    event_detail = Column('event_detail', String(120), comment='备注')


# class AliyunEventsModels(TimeBaseModel):
#     __tablename__ = 't_aliyun_event'
#     id = Column('id', Integer, primary_key=True, autoincrement=True)  # ID自增长
#     event_id = Column('event_id', String(120), index=True, comment='EventID')
#     event_account = Column('event_account', String(120), comment='账号')
#     event_service = Column('event_service', String(120), comment='服务类型')
#     event_type = Column('event_type', String(150), comment='事件类型')
#     event_status = Column('event_status', String(120), comment='状态')
#     event_instance_id = Column('event_instance_id', String(120), index=True, comment='实例ID')
#     event_instance_name = Column('event_instance_name', String(120), comment='主机名')
#     event_start_time = Column(DateTime)
#     event_end_time = Column(DateTime)
#     event_detail = Column('event_detail', Text(), comment='备注')


class CloudEventsModels(TimeBaseModel):
    # 云事件
    __tablename__ = 't_cloud_events'
    id = Column('id', Integer, primary_key=True, autoincrement=True)  # ID自增长
    cloud_name = Column('cloud_name', String(120), nullable=False, comment='云厂商Name', index=True)  # 云厂商信息
    account_id = Column('account_id', String(120), nullable=False, index=True, comment='AccountID')  # 账号信息
    region = Column('region', String(120), comment='regionID')  # 位置信息

    event_id = Column('event_id', String(120), index=True, comment='EventID')
    event_service = Column('event_service', String(120), comment='服务类型')
    event_type = Column('event_type', String(150), comment='事件类型')
    event_status = Column('event_status', String(120), comment='状态')
    event_instance_id = Column('event_instance_id', String(120), index=True, comment='实例ID')
    event_instance_name = Column('event_instance_name', String(120), comment='主机名')
    event_start_time = Column(DateTime)
    event_end_time = Column(DateTime)
    event_detail = Column('event_detail', Text(), comment='备注')
