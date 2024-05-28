#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 1084430062@qq.com
Author  : 娄文军
Date    : 2023/7/19 14:59
Desc    : 资源采购
"""

from models.base import TimeBaseModel
from sqlalchemy import Column, String, Integer, JSON, TEXT, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy_utils.types.choice import ChoiceType
from models import ORDER_STATUS_MAP, RES_TYPE_MAP, CLOUD_VENDOR_MAP
from datetime import datetime

Base = declarative_base()


# class TemplateModel(TimeBaseModel, Base):
#     """资源模板"""
#     __tablename__ = 'resource_order_template'
#     id = Column(Integer, primary_key=True, autoincrement=True)
#     name = Column('name', String(120), nullable=False, comment='名称', index=True)
#     account_id = Column('account_id', String(120), nullable=False, comment='云账号ID', index=True)
#     vendor = Column(ChoiceType(CLOUD_VENDOR_MAP, String(32)), nullable=False, comment='云厂商', index=True)
#     cloud_region_id = Column('cloud_region_id', String(120), nullable=False, comment='云区域ID', index=True)
#     cloud_region_name = Column('cloud_region_name', String(120), comment='云区域名称')
#     res_type = Column(ChoiceType(RES_TYPE_MAP, String(32)), comment='类型', index=True)
#     region = Column('region', String(120), comment='地域', index=True)
#     zone = Column('zone', String(120), comment='可用区', index=True)
#     image_id = Column('image_id', String(120), comment='镜像ID', index=True)
#     image_name = Column('image_name', String(120), comment='镜像名称')
#     cpu = Column('cpu', Integer, comment='cpu')
#     memory = Column('memory', Integer, comment='内存')
#     inner_ip = Column('inner_ip', String(120), comment='私有IP')
#     instance_type = Column('instance_type', String(120), comment='实例类型')
#     system_disk_size = Column('system_disk_size', Integer, comment='系统磁盘大小')
#     system_disk_type = Column('system_disk_type', String(120), comment='系统磁盘类型')
#     security_groups = Column('security_groups', JSON(), comment='安全组')
#     tags = Column('tags', JSON(), comment='标签')
#     vpc_id = Column('vpc_id', String(120), comment='私有网络ID')
#     vpc_name = Column('vpc_name', String(120), comment='私有网络名称')
#     subnet_id = Column('subnet_id', String(120), comment='私有子网')
#     subnet_name = Column('subnet_name', String(120), comment='私有子网名称')
#     max_flow_out = Column('max_flow_out', Integer, comment='外网带宽限制（M）')
#     image_passwd = Column('image_passwd', String(120), comment='镜像密码')
#     instance_charge_type = Column('instance_charge_type', String(120), comment='实例计费模式')
#     internet_charge_type = Column('internet_charge_type', String(120), comment='网络计费类型')
#     is_eip = Column('is_eip', String(5), default="0", comment='是否购买EIP')
#     bandwidth_pkg_id = Column('bandwidth_pkg_id', String(120), comment='带宽包ID')
#     data_disk = Column('data_disk', JSON(), comment='数据磁盘')
#     description = Column('description', TEXT(), comment='描述')
#     last_time = Column(DateTime, nullable=False, default=datetime.now)
#     update_time = Column(DateTime, nullable=False, default=datetime.now)  # 记录的更新时间

class TemplateModel(TimeBaseModel, Base):
    """资源模板"""
    __tablename__ = 'resource_order_template'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column('name', String(120), nullable=False, comment='名称', index=True)
    account_id = Column('account_id', String(120), nullable=False, comment='云账号ID', index=True)
    vendor = Column(ChoiceType(CLOUD_VENDOR_MAP, String(32)), nullable=False, comment='云厂商', index=True)
    cloud_region_id = Column('cloud_region_id', String(120), nullable=True, comment='云区域ID', index=True)
    cloud_region_name = Column('cloud_region_name', String(120), comment='云区域名称')
    vpc_id = Column('vpc_id', String(120), comment='私有网络ID')
    vpc_name = Column('vpc_name', String(120), comment='私有网络名称')
    subnet_id = Column('subnet_id', String(120), comment='私有子网')
    subnet_name = Column('subnet_name', String(120), comment='私有子网名称')
    res_type = Column(ChoiceType(RES_TYPE_MAP, String(32)), comment='类型', index=True)
    region = Column('region', String(120), comment='地域', index=True)
    zone = Column('zone', String(120), comment='可用区', index=True)
    content = Column('content', TEXT(), nullable=False, comment='实例配置')     # 实例配置
    description = Column('description', TEXT(), comment='描述')
    last_time = Column(DateTime, nullable=False, default=datetime.now)
    update_time = Column(DateTime, nullable=False, default=datetime.now)  # 记录的更新时间
    modify_user = Column('modify_user', String(128), nullable=True, comment='修改人')
    tags = Column('tags', JSON(), comment='标签')


class OrderInfoModel(TimeBaseModel, Base):
    """资源订单"""
    __tablename__ = 'resource_order_info'
    id = Column(Integer, primary_key=True, autoincrement=True)
    flow_id = Column('flow_id', Integer, comment='任务ID', index=True)
    name = Column('name', String(120), nullable=False, comment='名称', index=True)
    instance_name = Column('instance_name', String(120), nullable=False, comment='实例名称', index=True)
    res_type = Column(ChoiceType(RES_TYPE_MAP, String(32)), comment='类型', index=True)
    vendor = Column(ChoiceType(CLOUD_VENDOR_MAP, String(32)), comment='云厂商', index=True)
    status = Column(ChoiceType(ORDER_STATUS_MAP, String(32)), default="0", comment='任务运行状态')
    data = Column('data', JSON(), comment='数据')
