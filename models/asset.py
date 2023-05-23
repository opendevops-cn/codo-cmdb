#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/2/15 14:59
Desc    : 基础资产Models
"""

from datetime import datetime
from models.base import TimeBaseModel
from sqlalchemy import Column, String, Integer, Boolean, JSON, TEXT, UniqueConstraint, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class AssetBaseModel(TimeBaseModel, Base):
    """资产模型基类"""
    __abstract__ = True
    id = Column(Integer, primary_key=True, autoincrement=True, info={'order': 'DESC'})
    cloud_name = Column('cloud_name', String(120), nullable=False, comment='云厂商名称', index=True)  # 云厂商信息
    account_id = Column('account_id', String(120), nullable=False, index=True, comment='AccountID')  # 账号信息
    instance_id = Column('instance_id', String(120), unique=True, nullable=False, comment='实例ID,唯一ID')
    region = Column('region', String(120), comment='regionID')  # 位置信息
    zone = Column('zone', String(120), comment='可用区id')  # 位置信息
    is_expired = Column('is_expired', Boolean(), default=False, comment='True表示已过期')
    ext_info = Column('ext_info', JSON(), comment='扩展字段存JSON')


class AssetServerModels(AssetBaseModel):
    """"基础主机"""
    __tablename__ = 't_asset_server'  # server 基础主机
    name = Column('name', String(250), comment='名称', index=True)
    # hostname = Column('hostname', String(180), nullable=False, comment='主机名')
    inner_ip = Column('inner_ip', String(120), comment='内网IP', index=True)
    outer_ip = Column('outer_ip', String(120), comment='外网IP')
    state = Column('state', String(30), comment='主机状态', index=True)
    agent_id = Column('agent_id', String(160), index=True, comment='AgentID')
    agent_status = Column('agent_status', String(20), index=True, default='1', comment='Agent状态')  # 1在线 2离线
    is_product = Column("is_product", Integer, default=0, comment="标记是否上线", index=True)
    # 联合键约束
    __table_args__ = (
        UniqueConstraint('region', 'inner_ip', 'is_expired', name='host_key'),
    )


class AssetMySQLModels(AssetBaseModel):
    """"基础数据库"""
    __tablename__ = 't_asset_mysql'  # server 基础主机
    name = Column('name', String(180), nullable=False, comment='名称', index=True)
    state = Column('state', String(50), comment='状态', index=True)
    db_class = Column('db_class', String(120), comment='类型/规格')
    db_engine = Column('db_engine', String(120), comment='引擎mysql/polardb')
    db_version = Column('db_version', String(120), comment='MySQL版本')
    db_address = Column('db_address', JSON(), comment='json地址')


class AssetRedisModels(AssetBaseModel):
    """基础Redis"""
    __tablename__ = 't_asset_redis'  # server 基础主机
    name = Column('name', String(180), nullable=False, comment='实例名称')
    instance_status = Column('instance_status', String(120), comment='状态')
    instance_class = Column('instance_class', String(120), comment='类型/规格')
    instance_arch = Column('instance_arch', String(120), comment='Arch 集群/标准')
    instance_type = Column('instance_type', String(120), comment='Redis/Memcache')
    instance_version = Column('instance_version', String(120), comment='版本')
    instance_address = Column('instance_address', JSON(), comment='json地址')

    # # 联合键约束
    # __table_args__ = (
    #     UniqueConstraint('region', 'instance_id', name='redis_key'),
    # )


class AssetLBModels(AssetBaseModel):
    __tablename__ = 't_asset_lb'  # 负载均衡
    name = Column('name', String(255), nullable=False, comment='实例名称')
    type = Column('type', String(120), comment='LB类型, SLB/ALB/NLB')
    status = Column('status', String(120), comment='状态')
    dns_name = Column('dns_name', String(255), comment='DNS解析记录 7层有')
    lb_vip = Column('lb_vip', String(255), comment='vip')
    endpoint_type = Column('endpoint_type', String(255), comment='标记内网/外网')


class AssetEIPModels(AssetBaseModel):
    """弹性公网"""
    __tablename__ = 't_asset_eip'

    name = Column('name', String(128), nullable=True, index=True, comment='实例名称')
    address = Column('address', String(80), index=True, nullable=True, comment='IP地址')
    state = Column('state', String(80), index=True, nullable=True, comment='实例状态')
    bandwidth = Column('bandwidth', Integer, comment='带宽值')
    charge_type = Column('charge_type', String(20), default='Other', comment='实例计费方式')
    internet_charge_type = Column('internet_charge_type', String(20), index=True, default='Other',
                                  comment='网络计费方式')

    binding_instance_id = Column('binding_instance_id', String(80), comment='绑定实例ID')
    binding_instance_type = Column('binding_instance_type', String(80), comment='绑定实例类型')
    # domain_records  ManyToMany


class AssetUserFieldModels(TimeBaseModel):
    """基础Redis"""
    __tablename__ = 't_user_fields'  # server 基础主机
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_name = Column('user_name', String(120), nullable=False, comment='用户名')
    user_type = Column('user_type', String(120), comment='资产类型')
    user_fields = Column('user_fields', TEXT(), comment='收藏字段')
    # 联合键约束
    __table_args__ = (
        UniqueConstraint('user_name', 'user_type', name='user_field_key'),
    )


class AssetVPCModels(AssetBaseModel):
    """VPC"""
    __tablename__ = 't_asset_vpc'  # VPC
    id = Column(Integer, primary_key=True, autoincrement=True)
    vpc_name = Column('vpc_name', String(120), nullable=False, comment='VPC名称')
    cidr_block_v4 = Column('cidr_block_v4', String(255), index=True, comment='网段V4')
    cidr_block_v6 = Column('cidr_block_v6', String(255), index=True, comment='网段V6')
    vpc_router = Column('vpc_router', String(255), comment='路由表')
    vpc_switch = Column('vpc_switch', String(1000), comment='交换机')
    is_default = Column('is_default', Boolean(), default=False, comment='是否是默认')


class AssetVSwitchModels(AssetBaseModel):
    """交换机"""
    __tablename__ = 't_asset_vswitch'  # VSwitch
    id = Column(Integer, primary_key=True, autoincrement=True)
    vpc_id = Column('vpc_id', String(120), index=True, nullable=False, comment='VPC ID')
    vpc_name = Column('vpc_name', String(120), nullable=False, comment='VPC名称')

    name = Column('name', String(120), nullable=False, comment='虚拟交换机的名称')
    cidr_block_v4 = Column('cidr_block_v4', String(255), index=True, comment='网段V4')
    cidr_block_v6 = Column('cidr_block_v6', String(255), index=True, comment='网段V6')
    address_count = Column('address_count', String(80), comment='可用的IP地址数量')
    route = Column('route', String(255), comment='网关')
    route_id = Column('route_id', String(255), comment='路由表')
    description = Column('description', String(255), comment='交换机的描述信息')
    cloud_region_id = Column('cloud_region_id', String(50), comment='云区域ID，后置变更')
    is_default = Column('is_default', Boolean(), default=False, comment='是否是默认')


#
#
class SecurityGroupModels(AssetBaseModel):
    """安全组"""
    __tablename__ = 't_asset_security_group'
    id = Column(Integer, primary_key=True, autoincrement=True)
    vpc_id = Column('vpc_id', String(120), index=True, default='', comment='VPC ID')
    security_group_name = Column('security_group_name', String(120), nullable=False, comment='安全组名')
    security_group_type = Column('security_group_type', String(120), default='normal', comment='安全组类型')
    security_info = Column('security_info', JSON(), comment='安全组规则存JSON')
    ref_info = Column('ref_info', JSON(), comment='安全组关联存JSON')
    description = Column('description', String(255), default='', comment='详情简介')

# class SecurityGroupInfoModel(TimeBaseModel, Base):
#     """安全组规则"""
#     # TODO 感觉没必要创建表 思考中
#     __tablename__ = 't_asset_security_group_info'
#     id = Column(Integer, primary_key=True, autoincrement=True)
# security_group_id = Column('security_group_id', String(120), index=True, nullable=False, comment='安全组ID')
#
# dest_cidr_ip = Column('dest_cidr_ip', String(255), default='', comment='目标IP地址段')
# dest_group_id = Column('dest_group_id', String(128), default='', comment='目标安全组')
# dest_group_name = Column('dest_group_name', String(128), default='', comment='目的端安全组名称')
# dest_group_owner_account = Column('dest_group_owner_account', String(128), default='',
#                                   comment='目标安全组所属账户ID')
# direction = Column('direction', String(128), default='', comment='授权方向')
#
# ip_protocol = Column('ip_protocol', String(128), default='', comment='IP协议')
# ipv6_dest_cidr_ip = Column('ipv6_dest_cidr_ip', String(128), default='', comment='目的IPv6地址段')
# ipv6_source_cidr_ip = Column('ipv6_source_cidr_ip', String(128), default='', comment='源IPv6地址段')
#
# nic_type = Column('nic_type', String(50), default='', comment='网络类型')
# policy = Column('policy', String(50), default='', comment='授权策略')
#
# port_range = Column('port_range', String(150), default='', comment='端口范围')
# priority = Column('priority', String(20), default='', comment='规则优先级')
#
# source_cidr_ip = Column('source_cidr_ip', String(50), default='', comment='源IP地址段')
# source_group_id = Column('source_group_id', String(128), default='', comment='源安全组')
#
# source_group_name = Column('source_group_name', String(250), default='', comment='源端安全组名称')
# source_port_range = Column('source_port_range', String(128), default='', comment='源端端口范围')
# source_group_owner_account = Column('source_group_owner_account', String(128), default='',
#                                     comment='源安全组所属云账户ID')
# description = Column('description', String(250), default='', comment='描述信息')
# creation_time = Column('creation_time', String(50), default='', comment='安全组创建时间')


# class SecurityGroupRefModel(TimeBaseModel, Base):
#     """安全组关联"""
#     __tablename__ = 't_asset_security_group_ref'
#     id = Column(Integer, primary_key=True, autoincrement=True)
#     security_group_id = Column('security_group_id', String(120), index=True, nullable=False, comment='安全组ID')
#     ref_security_groups = Column('ref_security_groups', String(120), index=True, comment='关联的安全组')

#
# class CDNModel(AssetBaseModel):
#     pass
#
#
# class StorageModel(AssetBaseModel):
#     pass
