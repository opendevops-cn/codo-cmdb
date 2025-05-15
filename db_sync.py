#!/usr/bin/env python
# -*- coding: utf-8 -*-
from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL

from models.business import Base as BusinessBase
from models.base import Base as ABase
from models.cloud import Base as CloudBase
from models.asset import Base as ServerBase
from models.event import Base as EventBase
from models.tag import Base as TagBase
from models.tree import Base as TreeBase
from models.cloud_region import Base as CloudRegionBase
from models.domain import Base as DomainBase
from models.order_model import Base as OrderBase
from models.autdit import Base as AuditBase
from websdk2.consts import const
from settings import settings as app_settings
from models.env import Base as EnvBase
from models.secret import Base as SecretBase
from models.agent import Base as AgentBase
from models.cbb_area import Base as CbbAreaBase


default_configs = app_settings[const.DB_CONFIG_ITEM][const.DEFAULT_DB_KEY]
url_object = URL.create(
    drivername='mysql+pymysql',
    username=default_configs.get(const.DBUSER_KEY),
    password=default_configs.get(const.DBPWD_KEY),
    host=default_configs.get(const.DBHOST_KEY),
    port=int(default_configs.get(const.DBPORT_KEY)),
    database=default_configs.get(const.DBNAME_KEY),
    query={'charset': 'utf8mb4'}
)
engine = create_engine(url_object, echo=True)

def create():
    ABase.metadata.create_all(engine)
    CloudBase.metadata.create_all(engine)
    ServerBase.metadata.create_all(engine)
    EventBase.metadata.create_all(engine)
    BusinessBase.metadata.create_all(engine)
    TagBase.metadata.create_all(engine)
    TreeBase.metadata.create_all(engine)
    CloudRegionBase.metadata.create_all(engine)
    DomainBase.metadata.create_all(engine)
    OrderBase.metadata.create_all(engine)
    AuditBase.metadata.create_all(engine)
    EnvBase.metadata.create_all(engine)
    SecretBase.metadata.create_all(engine)
    AgentBase.metadata.create_all(engine)
    CbbAreaBase.metadata.create_all(engine)
    print('[Success] 表结构创建成功!')


def drop():
    ABase.metadata.drop_all(engine)
    CloudBase.metadata.drop_all(engine)
    ServerBase.metadata.drop_all(engine)
    EventBase.metadata.drop_all(engine)
    BusinessBase.metadata.drop_all(engine)
    TagBase.metadata.drop_all(engine)
    TreeBase.metadata.drop_all(engine)
    CloudRegionBase.metadata.drop_all(engine)
    DomainBase.metadata.drop_all(engine)


if __name__ == '__main__':
    create()
