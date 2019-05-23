#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/4/17 13:48
# @Author  : Fred Yangxiaofei
# @File    : db.py
# @Role    : ORM


from sqlalchemy import Column, String, Integer, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import class_mapper
from datetime import datetime

Base = declarative_base()


def model_to_dict(model):
    model_dict = {}
    for key, column in class_mapper(model.__class__).c.items():
        model_dict[column.name] = getattr(model, key, None)
    return model_dict


class DBTag(Base):
    __tablename__ = 'asset_db_tag'

    id = Column(Integer, primary_key=True, autoincrement=True)
    db_id = Column('db_id', Integer)
    tag_id = Column('tag_id', Integer)


class DB(Base):
    __tablename__ = 'asset_db'
    ### 数据库集群
    id = Column(Integer, primary_key=True, autoincrement=True)
    db_code = Column('db_code', String(50))  ### 名称 代号 编码
    db_host = Column('db_host', String(80), nullable=False)
    db_port = Column('db_port', String(5), nullable=False, default=3306)
    db_user = Column('db_user', String(20), nullable=False, default='root')
    db_pwd = Column('db_pwd', String(30), nullable=False)
    db_env = Column('db_env', String(10), nullable=False, default='写')
    proxy_host = Column('proxy_host', String(35))  ### 代理主机 适配多云
    db_type = Column('db_type', String(10))  ### 标记类型
    db_version = Column('db_version', String(20)) ###版本
    db_mark = Column('db_mark', String(10))  ### 标记读写备
    db_detail = Column('db_detail', String(30))
    all_dbs = Column('all_dbs', String(300))  ### 所有的数据库
    state = Column('state', String(15))
    create_time = Column('create_time', DateTime(), default=datetime.now, onupdate=datetime.now)


# class ProxyInfo(Base):
#     __tablename__ = 'asset_proxy_info'
#
#     ### 代理主机  通过此主机来连接数据库
#     id = Column('id', Integer, primary_key=True, autoincrement=True)
#     proxy_host = Column('proxy_host', String(60), unique=True, nullable=False)
#     inception = Column('inception', String(300))
#     salt = Column('salt', String(300))
#     detail = Column('detail', String(20))
