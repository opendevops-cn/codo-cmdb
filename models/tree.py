#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/2/15 14:59
Desc    : 树形关系
"""

from models.base import BizBaseModel
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, Integer, Enum, UniqueConstraint, Boolean, JSON

Base = declarative_base()

asset_type_enum = Enum(
    'server',
    'process',
    'mysql',
    'redis',
    'lb',
    'vpc',
    'disk',
    'switch',
    'domain',
    'oss',
    'cdn',
    'eip'
)


class TreeModels(BizBaseModel):
    __tablename__ = 't_tree_list'  # 业务树
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column('title', String(128), comment='标题名称')
    node_type = Column(Integer, comment='节点类型,0:cmdb, 1: env, 2: set，, 3: module')
    node_sort = Column(Integer, default=100, comment="排序,字数越小越靠前")
    grand_node = Column('grand_node', String(128), default='', comment='TopNode节点,标记上上级')
    parent_node = Column('parent_node', String(128), default='', comment='TopNode节点,标记上级')
    detail = Column('detail', String(128), default='', comment='备注')
    expand = Column('expand', Boolean(), default=False, comment='是否展开')
    contextmenu = Column('contextmenu', Boolean(), default=True, comment='点击右键弹出菜单')
    ext_info = Column('ext_info', JSON(), default={}, comment='扩展字段')
    # 联合键约束(一个业务下父节点+名称+type肯定是唯一的)
    __table_args__ = (
        UniqueConstraint('biz_id', 'title', 'node_type', 'grand_node', 'parent_node', name='idx_tree_name'),
    )


class TreeAssetModels(BizBaseModel):
    __tablename__ = 't_tree_asset'  # 树&资产关联表
    id = Column(Integer, primary_key=True, autoincrement=True)
    is_enable = Column(Integer, nullable=True, default=1, comment='是否上线 0:下线 1:上线')
    env_name = Column('env_name', String(128), comment='环境/大区')
    region_name = Column('region_name', String(128), comment='区服/集群/机房')
    module_name = Column('module_name', String(128), comment='模块/服务/机架/机柜')
    asset_type = Column(asset_type_enum, comment='资产类型')
    asset_id = Column(Integer, nullable=False, comment='资产ID')
    ext_info = Column('ext_info', JSON(), default={}, comment='扩展字段')  # 预留,可以存业务信息

    __table_args__ = (
        UniqueConstraint('biz_id', 'env_name', 'region_name', 'module_name', 'asset_type', 'asset_id',
                         name='idx_tree_asset_name'),
    )
