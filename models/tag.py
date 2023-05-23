#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File  : tag.py
# @Author: 
# @Date  : 2022/9/7
# @Role  : 标签管理模型

from models.base import TimeBaseModel
from sqlalchemy import Column, String, Integer, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class TagModels(TimeBaseModel):
    __tablename__ = 't_tag_list'  # 标签管理，参考大多数AWS/阿里云的标签管理做法
    id = Column(Integer, primary_key=True, autoincrement=True, index=True, comment='TagID自增')  # ID自增长
    tag_key = Column('tag_key', String(120), primary_key=True, nullable=False, comment='标签Key')  # Key唯一
    tag_value = Column('tag_value', String(120), nullable=False, comment='标签Value')  # 不同Key下的Value可以相同
    tag_detail = Column('tag_detail', String(120), comment='备注')
    # 联合键约束
    __table_args__ = (
        UniqueConstraint('tag_key', 'tag_value', name='tag_unique'),
    )


class TagAssetModels(TimeBaseModel):
    __tablename__ = 't_tag_asset'  # 资产标签关系
    id = Column('id', Integer, primary_key=True, autoincrement=True, comment='自增ID')
    tag_id = Column(Integer, ForeignKey(TagModels.id), nullable=False, comment='外键TagID')
    asset_type = Column(
        Enum('server', 'process', 'mysql', 'redis', 'lb', 'vpc', 'disk', 'switch', 'domain', 'oss', 'cdn', 'eip'),
        comment='资产类型')
    asset_id = Column(Integer, comment='资产ID')
