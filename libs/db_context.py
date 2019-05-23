#!/usr/bin/env python
# -*-coding:utf-8-*-
'''
Author : SS
date   : 2017年10月17日17:23:19
role   : 数据库连接
'''
import sys
import pymysql
from urllib.parse import quote_plus
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import sessionmaker
from websdk.consts import const

sys.path.append("..")
from settings import settings


def get_db_engine(db_key):
    databases = settings.get('databases', 0)
    db_conf = databases[db_key]
    dbuser = db_conf['user']
    dbpwd = db_conf['pwd']
    dbhost = db_conf['host']
    dbport = db_conf.get('port', 0)
    dbname = db_conf['name']
    return create_engine('mysql+pymysql://{user}:{pwd}@{host}:{port}/{dbname}?charset=utf8'
                         .format(user=dbuser, pwd=quote_plus(dbpwd), host=dbhost, port=dbport, dbname=dbname),
                         logging_name=db_key, pool_pre_ping=True) #pool_size=10  poolclass=NullPool, pool_recycle=60

class DBContext(object):
    def __init__(self, rw='r', db_key=None):
        self.__db_key = db_key
        if not self.__db_key:
            if rw == 'w':
                self.__db_key = const.DEFAULT_DB_KEY
            elif rw == 'r':
                self.__db_key = const.READONLY_DB_KEY
        engine = get_db_engine(self.__db_key)
        self.__engine = engine

    def __enter__(self):
        self.__session = sessionmaker(bind=self.__engine)()
        return self.__session

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__session.close()

    def get_session(self):
        return self.__session
