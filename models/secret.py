# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/12/19
# @Description: 欢乐剑

from sqlalchemy import Column, String, Integer, TEXT
from sqlalchemy.ext.declarative import declarative_base

from models.base import TimeBaseModel

Base = declarative_base()


class SecretModels(TimeBaseModel):
    __tablename__ = 't_sword_secret'  # 欢乐剑密钥
    id = Column('id', Integer, primary_key=True, autoincrement=True, comment='自增ID')
    uuid = Column("uuid", String(255), unique=True, index=True, comment='密钥ID')
    secret = Column("secret", TEXT(), comment="密钥内容")