#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/4/17 9:52
# @Author  : Fred Yangxiaofei
# @File    : settings.py
# @Role    : 配置文件

import os
from websdk.consts import const

ROOT_DIR = os.path.dirname(__file__)
debug = True
xsrf_cookies = False
expire_seconds = 365 * 24 * 60 * 60
cookie_secret = '61oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2X6TP1o/Vo='

#这是写库，
DEFAULT_DB_DBHOST = os.getenv('DEFAULT_DB_DBHOST', '172.16.0.223') #修改
DEFAULT_DB_DBPORT = os.getenv('DEFAULT_DB_DBPORT', '3306')   #修改
DEFAULT_DB_DBUSER = os.getenv('DEFAULT_DB_DBUSER', 'root')   #修改
DEFAULT_DB_DBPWD = os.getenv('DEFAULT_DB_DBPWD', 'ljXrcyn7chaBU4F') #修改
DEFAULT_DB_DBNAME = os.getenv('DEFAULT_DB_DBNAME', 'codo_cmdb') #默认

#这是从库，读， 一般情况下是一个数据库即可，需要主从读写分离的，请自行建立好服务
READONLY_DB_DBHOST = os.getenv('READONLY_DB_DBHOST', '172.16.0.223') #修改
READONLY_DB_DBPORT = os.getenv('READONLY_DB_DBPORT', '3306') #修改
READONLY_DB_DBUSER = os.getenv('READONLY_DB_DBUSER', 'root') #修改
READONLY_DB_DBPWD = os.getenv('READONLY_DB_DBPWD', 'ljXrcyn7chaBU4F') #修改
READONLY_DB_DBNAME = os.getenv('READONLY_DB_DBNAME', 'codo_cmdb')  #默认

#这是Redis配置信息，默认情况下和codo-admin里面的配置一致
DEFAULT_REDIS_HOST = os.getenv('DEFAULT_REDIS_HOST', '172.16.0.223') #修改
DEFAULT_REDIS_PORT = os.getenv('DEFAULT_REDIS_PORT', '6379') #修改
DEFAULT_REDIS_DB = 8 #默认和codo-admin保持一致
DEFAULT_REDIS_AUTH = True
DEFAULT_REDIS_CHARSET = 'utf-8'
DEFAULT_REDIS_PASSWORD = os.getenv('DEFAULT_REDIS_PASSWORD', '123456') #修改

# SSH公钥,获取资产使用，一般都是机器默认路径,建议不要修改
PUBLIC_KEY = '/root/.ssh/id_rsa.pub' #默认

# 这里如果配置codo-task的数据库地址，则将数据同步到作业配置--TagTree下面(非必填项)
CODO_TASK_DB_HOST = os.getenv('CODO_TASK_DB_HOST', '172.16.0.223')  #修改
CODO_TASK_DB_PORT = os.getenv('CODO_TASK_DB_PORT', 3306) #修改
CODO_TASK_DB_USER = os.getenv('CODO_TASK_DB_USER', 'root') #修改
CODO_TASK_DB_PWD = os.getenv('CODO_TASK_DB_PWD', 'ljXrcyn7chaBU4F') #修改
CODO_TASK_DB_DBNAME = os.getenv('CODO_TASK_DB_DBNAME', 'do_task') #修改

CODO_TASK_DB_INFO = dict(
    host=CODO_TASK_DB_HOST,
    port=CODO_TASK_DB_PORT,
    user=CODO_TASK_DB_USER,
    passwd=CODO_TASK_DB_PWD,
    db=CODO_TASK_DB_DBNAME
)




try:
    from local_settings import *
except:
    pass

settings = dict(
    debug=debug,
    xsrf_cookies=xsrf_cookies,
    cookie_secret=cookie_secret,
    expire_seconds=expire_seconds,
    app_name='codo_cmdb',
    databases={
        const.DEFAULT_DB_KEY: {
            const.DBHOST_KEY: DEFAULT_DB_DBHOST,
            const.DBPORT_KEY: DEFAULT_DB_DBPORT,
            const.DBUSER_KEY: DEFAULT_DB_DBUSER,
            const.DBPWD_KEY: DEFAULT_DB_DBPWD,
            const.DBNAME_KEY: DEFAULT_DB_DBNAME,
        },
        const.READONLY_DB_KEY: {
            const.DBHOST_KEY: READONLY_DB_DBHOST,
            const.DBPORT_KEY: READONLY_DB_DBPORT,
            const.DBUSER_KEY: READONLY_DB_DBUSER,
            const.DBPWD_KEY: READONLY_DB_DBPWD,
            const.DBNAME_KEY: READONLY_DB_DBNAME,
        }
    },
    redises={
        const.DEFAULT_RD_KEY: {
            const.RD_HOST_KEY: DEFAULT_REDIS_HOST,
            const.RD_PORT_KEY: DEFAULT_REDIS_PORT,
            const.RD_DB_KEY: DEFAULT_REDIS_DB,
            const.RD_AUTH_KEY: DEFAULT_REDIS_AUTH,
            const.RD_CHARSET_KEY: DEFAULT_REDIS_CHARSET,
            const.RD_PASSWORD_KEY: DEFAULT_REDIS_PASSWORD
        }
    }
)
