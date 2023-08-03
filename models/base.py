#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/2/15 14:59
Desc    : Base类
"""

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class TimeBaseModel(Base):
    """模型基类，为模型补充创建时间与更新时间"""
    __abstract__ = True
    create_time = Column(DateTime, nullable=False, default=datetime.now)  # 记录的创建时间
    update_time = Column(DateTime, nullable=False, default=datetime.now, index=True, onupdate=datetime.now)  # 记录的更新时间


class BizBaseModel(TimeBaseModel, Base):
    """业务模型基类"""
    __abstract__ = True
    biz_id = Column(String(15), comment='业务/项目ID', index=True, nullable=True)
