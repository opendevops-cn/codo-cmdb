#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2019年5月7日
Desc    : 云解析管理数据库ORM
"""

from models.base import BizBaseModel
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class DomainName(Base):
    __tablename__ = 'cloud_dns_name'
    id = Column('id', Integer, primary_key=True, autoincrement=True)

    domain_id = Column('domain_id', String(128), index=True, unique=True, nullable=False)
    account = Column('account', String(128), index=True)
    cloud_name = Column('cloud_name', String(80), nullable=False, default='unknown')

    domain_name = Column('domain_name', String(180), index=True, unique=True, nullable=False)
    record_count = Column('record_count', Integer, index=True, default=0)
    domain_state = Column('domain_state', String(20), default='running')
    version = Column('version', String(80), default='普通版')
    remark = Column('remark', String(255), default='unknown')
    star_mark = Column('star_mark', Boolean(), index=True, default=False, comment='标星')  # 标星
    record_end_time = Column('record_end_time', DateTime(), default=datetime.now)
    create_time = Column('create_time', DateTime(), default=datetime.now)
    update_time = Column('update_time', DateTime(), default=datetime.now, onupdate=datetime.now)

    __mapper_args__ = {
        "order_by": -star_mark
    }


class DomainRecords(BizBaseModel):
    __tablename__ = 'cloud_dns_records'
    id = Column('id', Integer, primary_key=True, autoincrement=True)
    domain_name = Column('domain_name', String(180), index=True, nullable=False)
    account = Column('account', String(80), index=True)
    record_id = Column('record_id', String(128), index=True, unique=True)  # 解析记录ID
    domain_rr = Column('domain_rr', String(128), index=True, default='www')  # 主机记录。
    domain_type = Column('domain_type', String(20), default='A')  # 记录类型
    domain_value = Column('domain_value', String(500), default='')  # 记录值。
    domain_ttl = Column('domain_ttl', Integer, default=600)  # 生存时间
    domain_mx = Column('domain_mx', Integer, default=5)  # MX记录的优先级。
    weight = Column('weight', String(10), default=None)  # 权重 企业版功能。
    line = Column('line', String(50), default='default')  # 解析线路  默认/境外
    state = Column('state', String(50), default='default', index=True)  # 当前的解析记录状态
    remark = Column('remark', String(255), default='unknown')  # 备注

    biz_id = Column('biz_id', String(15), index=True, default='502', comment='业务/项目ID')
    biz_cn_name = Column('biz_cn_name', String(20), index=True, default='', comment='业务/项目 用来展示')
    update_user = Column('update_user', String(100), default='unknown')  # 最后修改人
    update_time = Column('update_time', DateTime(), default=datetime.now, index=True, onupdate=datetime.now)


class DomainOptLog(Base):
    __tablename__ = 'cloud_dns_opt_log'

    # 操作日志
    id = Column('id', Integer, primary_key=True, autoincrement=True)
    domain_name = Column('domain_name', String(180), index=True, nullable=False)
    username = Column('username', String(100))  # 执行人
    action = Column('action', String(20))  # 操作方法
    record = Column('record', Text())  # 记录
    state = Column('状态', String(50), default='error')
    update_time = Column('update_time', DateTime(), default=datetime.now, onupdate=datetime.now, index=True)
    __mapper_args__ = {
        "order_by": -update_time
    }


class DomainSyncLog(Base):
    __tablename__ = 'cloud_dns_sync_log'

    ### 日志
    id = Column('id', Integer, primary_key=True, autoincrement=True)
    present = Column('present', String(50), default='unknown')
    alias_name = Column('别名', String(128), default='unknown')
    access_id = Column('access_id', String(128), default='unknown')
    record = Column('record', Text())  # 记录
    state = Column('状态', String(20), default='错误')
    update_time = Column('update_time', DateTime(), default=datetime.now, onupdate=datetime.now, index=True)
    __mapper_args__ = {
        "order_by": -update_time
    }

# class DomainCheckSSL(Base):
#     __tablename__ = 'domain_check_ssl'
#     id = Column('id', Integer, primary_key=True, autoincrement=True)
#
#     domain_name = Column('domain_name', String(128), index=True, unique=True, nullable=False)
#     record = Column('record', Text())  ## 记录
#     port_list = Column('port', Text())
#     is_valid = Column('是否启用', String(50), index=True, default='yes')
#     update_user = Column('最后修改人', String(50), default='unknown')  ### 最后修改人
#     update_time = Column('update_time', DateTime(), default=datetime.now, onupdate=datetime.now)
