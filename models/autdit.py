# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/5/11
# @Description: 审计日志

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, Integer, Text

from models.base import TimeBaseModel

Base = declarative_base()


class AuditModels(Base, TimeBaseModel):
    __tablename__ = 't_audit_log'
    id = Column('id', Integer, primary_key=True, autoincrement=True)
    exec_uuid = Column('exec_uuid', String(100), index=True, comment='操作ID')
    log_type = Column('log_type', String(64), nullable=False, default='用户日志', comment='日志类型')
    business_name = Column('business_name', String(180), nullable=True, default='', comment='业务')
    module_name = Column('module_name', String(180), nullable=True, default='', comment='模块')
    message = Column('message', Text())
    operator = Column('operator', String(128), nullable=True, comment='操作人')

    __mapper_args__ = {
        "order_by": - id
    }
