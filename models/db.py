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
    idc = Column('idc', String(128))  # IDC
    db_instance_id = Column('db_instance_id', String(128))  #RDS实例ID
    db_code = Column('db_code', String(255))  ### 名称 代号 编码
    db_class = Column('db_class', String(255))  ### DB实例类型
    db_host = Column('db_host', String(255), nullable=False) ### DB主机地址
    db_public_ip = Column('db_public_ip', String(255)) ### DB主机外网地址,只有少量的才会开启
    db_port = Column('db_port', String(10), nullable=False, default=3306)  ### DB端口
    db_user = Column('db_user', String(128), nullable=False, default='root') ### DB用户
    db_pwd = Column('db_pwd', String(128))   ### DB的密码
    db_disk = Column('db_disk', String(128))  ### DB的磁盘，主要RDS有
    db_region = Column('db_region', String(128)) ### DB的区域 可用区
    db_env = Column('db_env', String(128), default='release')  ### 环境/release/dev
    db_type = Column('db_type', String(128))  ### 标记类型如：MySQL/Redis
    db_version = Column('db_version', String(128)) ###DB版本
    db_mark = Column('db_mark', String(255))  ### 标记读写备
    state = Column('state', String(128))   ### DB的状态
    db_detail = Column('db_detail', String(255))  ### 描述
    proxy_host = Column('proxy_host', String(128))  ### 代理主机 适配多云,预留
    create_time = Column('create_time', DateTime(), default=datetime.now)  # 创建时间
    update_time = Column('update_time', DateTime(), default=datetime.now, onupdate=datetime.now)  # 记录更新时间



# class ProxyInfo(Base):
#     __tablename__ = 'asset_proxy_info'
#
#     ### 代理主机  通过此主机来连接数据库
#     id = Column('id', Integer, primary_key=True, autoincrement=True)
#     proxy_host = Column('proxy_host', String(60), unique=True, nullable=False)
#     inception = Column('inception', String(300))
#     salt = Column('salt', String(300))
#     detail = Column('detail', String(20))
