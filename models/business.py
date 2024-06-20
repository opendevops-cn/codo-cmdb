#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/2/15 14:59
Desc    : 业务表
"""

from datetime import datetime
from models import asset_type_enum, des_rule_type_enum
from models.base import TimeBaseModel, BizBaseModel
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, Integer, DateTime, JSON, UniqueConstraint

Base = declarative_base()


# class BizModels(Base):
#     __tablename__ = 't_biz_list'  # 业务
#     biz_id = Column('biz_id', Integer, primary_key=True, autoincrement=True)
#     biz_cn_name = Column('biz_cn_name', String(128), unique=True, nullable=False, comment='中文名')
#     biz_en_name = Column('biz_en_name', String(128), comment='英文名称')
#     biz_opser = Column('biz_opser', String(500), comment='运维人员')
#     biz_developer = Column('biz_developer', String(500), comment='开发人员')
#     biz_tester = Column('biz_tester', String(500), comment='测试人员')
#     biz_life_cycle = Column('biz_life_cycle', String(128), comment='生命周期')
#     create_time = Column('create_time', DateTime(), default=datetime.now, comment='创建时间')  # 创建时间
#     update_time = Column('update_time', DateTime(), default=datetime.now, onupdate=datetime.now,
#                          comment='更新时间')  # 记录更新时间


class BizModels(TimeBaseModel, Base):
    __tablename__ = 'biz_list'

    id = Column('id', Integer, primary_key=True, autoincrement=True)
    biz_id = Column('biz_id', String(15), index=True, unique=True)
    biz_en_name = Column('biz_en_name', String(80), unique=True, index=True)  ###业务英文命
    biz_cn_name = Column('biz_cn_name', String(80), index=True, default='')  ###业务中文名
    resource_group = Column('resource_group', String(80), index=True, default='')  ###资源组名 / 资源隔离名
    # maintainer = Column('maintainer', JSON(), default="")
    biz_opser = Column('biz_opser', String(500), comment='运维人员')
    biz_developer = Column('biz_developer', String(500), comment='开发人员')
    biz_tester = Column('biz_tester', String(500), comment='测试人员')

    corporate = Column('corporate', String(255), default="")  ### 公司实体
    sort = Column('sort', Integer, default=10, index=True)  ### 排序
    life_cycle = Column('life_cycle', String(15), default='开发', index=True, comment='生命周期')  ###
    description = Column('description', String(255), default='')  ### 描述、备注

    __mapper_args__ = {"order_by": (sort, biz_en_name)}


class SetTempModels(TimeBaseModel):
    __tablename__ = 't_set_temp'  # 集群模板，为了方便快速创建
    id = Column(Integer, primary_key=True, autoincrement=True)
    temp_name = Column('temp_name', String(128), unique=True, nullable=True, comment='模板名称')
    temp_data = Column('temp_data', JSON(), nullable=True, comment='包含的模块')
    create_user = Column('create_user', String(128), comment='创建人')


class DynamicGroupModels(BizBaseModel):
    __tablename__ = 't_dynamic_group'  # 业务动态分组
    id = Column(Integer, primary_key=True, autoincrement=True)
    exec_uuid = Column('exec_uuid', String(100), index=True, comment='查询ID')
    dynamic_group_name = Column('dynamic_group_name', String(80), nullable=True, comment='名称')
    dynamic_group_type = Column('dynamic_group_type', String(20), default='normal', nullable=True, comment='类型')
    # asset_type = Column('asset_type', String(50), default='server', nullable=True, comment='资源类型')
    ###
    env_name = Column('env_name', String(128), comment='环境/大区')
    region_name = Column('region_name', String(500), comment='区服/集群/机房')
    module_name = Column('module_name', String(500), comment='模块/服务/机架/机柜')

    dynamic_group_detail = Column('dynamic_group_detail', String(255), comment='备注')
    dynamic_group_rules = Column('dynamic_group_rules', JSON(), nullable=True, comment='条件')
    modify_user = Column('modify_user', String(128), nullable=True, comment='修改人')

    # 联合键约束 (业务ID+名称必须是唯一的)
    __table_args__ = (
        UniqueConstraint('biz_id', 'dynamic_group_name', name='biz_id_and_name_unique'),
    )


class DynamicRulesModels(TimeBaseModel):
    __tablename__ = 't_dynamic_rules'  # 动态规则

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column('name', String(100), unique=True, comment='规则名称')
    asset_type = Column(asset_type_enum, comment='资产类型')
    condition_list = Column('condition_list', JSON, default={}, comment='匹配条件')
    des_type = Column('des_type', des_rule_type_enum, nullable=False, comment='业务拓扑/标签')
    des_data = Column('des_data', JSON, nullable=False, comment='目标数据')
    interval = Column('interval', String(10), default="no", comment='循环刷新')
    modify_user = Column('modify_user', String(128), nullable=True, comment='修改人')

    __table_args__ = (
        # UniqueConstraint('biz_id', 'dynamic_group_name', name='biz_id_and_name_unique'),
    )


class PermissionGroupModels(BizBaseModel):
    __tablename__ = 't_permission_group'  # 业务权限分组
    id = Column(Integer, primary_key=True, autoincrement=True)
    exec_uuid = Column('exec_uuid', String(100), index=True, comment='查询ID')
    perm_group_name = Column('perm_group_name', String(80), nullable=True, comment='名称')
    perm_type = Column('perm_type', String(20), default='dev', nullable=True, comment='权限类型')
    user_group = Column('user_group', JSON, comment='用户组', default=[])
    env_name = Column('env_name', String(128), comment='环境/大区')
    region_name = Column('region_name', String(500), comment='区服/集群/机房')
    module_name = Column('module_name', String(500), comment='模块/服务/机架/机柜')
    perm_group_detail = Column('perm_group_detail', String(255), comment='备注')
    modify_user = Column('modify_user', String(128), nullable=True, comment='修改人')

    # 联合键约束 (业务ID+名称必须是唯一的)
    __table_args__ = ()


class PermissionTypeMapping(BizBaseModel):
    __tablename__ = 't_permission_type_mapping'  # 权限类型和jms账号映射
    id = Column(Integer, primary_key=True, autoincrement=True)
    perm_type = Column('perm_type', String(20), default='dev', nullable=True, comment='权限类型')
    jms_org_id = Column('jms_org_id', String(80), default="", comment='堡垒机组织ID')
    jms_account_template_id = Column('jms_account_template_id', String(255), default="", comment='堡垒机账号模版ID')
    jms_account_template = Column('jms_account_template', String(255), default="", comment='堡垒机账号模版')
    jms_domain_id = Column('jms_domain_id', String(80), default="", comment='堡垒机网域ID')
    jms_domain_name = Column('jms_domain_name', String(80), default="", comment='堡垒机网域名')

    # 联合键约束 (业务ID+权限类型+堡垒机组织ID+网域ID必须是唯一的)
    __table_args__ = (
        UniqueConstraint('biz_id', 'perm_type', 'jms_org_id', 'jms_account_template_id',
                         'jms_domain_id', name='permission_type_unique'),
    )