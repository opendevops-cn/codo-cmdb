#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2019/4/15 14:59
Desc    : 配置文件
"""

import os

from websdk2.consts import const

ROOT_DIR = os.path.dirname(__file__)
debug = True
xsrf_cookies = False
expire_seconds = 365 * 24 * 60 * 60
cookie_secret = os.getenv("DEFAULT_COOKIE_SECRET", "61oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2X6TP1o/Vo=")
sword_secret = os.getenv("DEFAULT_SWORD_SECRET", "feflCCJLWlpGvfyrrTezkfwSgKx_AEuP2_xy0J6RvQI=")

# 这是写库，
DEFAULT_DB_DBHOST = os.getenv("DEFAULT_DB_DBHOST", "")  # 修改
DEFAULT_DB_DBPORT = os.getenv("DEFAULT_DB_DBPORT", "3306")  # 修改
DEFAULT_DB_DBUSER = os.getenv("DEFAULT_DB_DBUSER", "root")  # 修改
DEFAULT_DB_DBPWD = os.getenv("DEFAULT_DB_DBPWD", "")  # 修改
DEFAULT_DB_DBNAME = os.getenv("DEFAULT_DB_DBNAME", "codo-cmdb")  # 默认

# 这是从库，读， 一般情况下是一个数据库即可，需要主从读写分离的，请自行建立好服务
READONLY_DB_DBHOST = os.getenv("READONLY_DB_DBHOST", "")  # 修改
READONLY_DB_DBPORT = os.getenv("READONLY_DB_DBPORT", "3306")  # 修改
READONLY_DB_DBUSER = os.getenv("READONLY_DB_DBUSER", "root")  # 修改
READONLY_DB_DBPWD = os.getenv("READONLY_DB_DBPWD", "")  # 修改
READONLY_DB_DBNAME = os.getenv("READONLY_DB_DBNAME", "codo-cmdb")  # 默认

# 这是Redis配置信息，默认情况下和codo-admin里面的配置一致
DEFAULT_REDIS_HOST = os.getenv("DEFAULT_REDIS_HOST", "localhost")  # 修改
DEFAULT_REDIS_PORT = os.getenv("DEFAULT_REDIS_PORT", "6379")  # 修改
DEFAULT_REDIS_DB = os.getenv("DEFAULT_REDIS_DB", 9)
DEFAULT_REDIS_AUTH = os.getenv("DEFAULT_REDIS_AUTH", True)
DEFAULT_REDIS_CHARSET = os.getenv("DEFAULT_REDIS_CHARSET", "utf-8")
DEFAULT_REDIS_PASSWORD = os.getenv("DEFAULT_REDIS_PASSWORD", "")  # 修改

# consul 为Prometheus提供数据 选填
DEFAULT_CONSUL_HOST = os.getenv("DEFAULT_CONSUL_HOST", "")  # 修改
DEFAULT_CONSUL_PORT = os.getenv("DEFAULT_CONSUL_PORT", 8500)  # 修改
DEFAULT_CONSUL_TOKEN = os.getenv("DEFAULT_CONSUL_TOKEN", None)  # 修改
DEFAULT_CONSUL_SCHEME = os.getenv("DEFAULT_CONSUL_SCHEME", "http")  # 修改

# 和其他系统交互使用
api_gw = os.getenv("CODO_API_GW", "")  # 网关
settings_auth_key = os.getenv("CODO_AUTH_KEY", "")  # 服务之间认证token
# 资产变更通知webhook
asset_change_notify = {}

# JumpServer配置
JMS_API_BASE_URL = os.getenv("JMS_API_BASE_URL", "")
JMS_API_KEY_ID = os.getenv("JMS_API_KEY_ID", "")
JMS_API_KEY_SECRET = os.getenv("JMS_API_KEY_SECRET", "")

# 内网交换机配置
SWITCH_COMMUNITY = os.getenv("SWITCH_COMMUNITY", "")  # 交换机 公共团体字符串
SWITCH_MODEL_OID = os.getenv("SWITCH_MODEL_OID", "")  #  交换机型号Oid
SWITCH_NAME_OID = os.getenv("SWITCH_NAME_OID", "")  # 交换机设备名Oid
SWITCH_SN_OID = os.getenv("SWITCH_SN_OID", "")  # 交换机序列号oid

# kafka配置
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "")
KAFKA_CLIENT_ID = os.getenv("KAFKA_CLIENT_ID", "")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "")

# Sync GCP to CMDB
GCP_SYNC = os.getenv("GCP_SYNC", "no")

# 服务树告警忽略配置. e.g: "item1,,,item2,,,item3"
INGORE_TREE_ALERT_KEYWORDS = os.getenv("IGNORE_TREE_ALERT_ITEMS", "tke-,,,node-00,,,as-tke-,,,k8s-")

try:
    from local_settings import *
except ImportError:
    print("local_settings.py  No Found.")

settings = dict(
    debug=debug,
    xsrf_cookies=xsrf_cookies,
    cookie_secret=cookie_secret,
    sword_secret=sword_secret,
    expire_seconds=expire_seconds,
    api_gw=api_gw,
    asset_change_notify=asset_change_notify,
    settings_auth_key=settings_auth_key,
    switch_community=SWITCH_COMMUNITY,
    switch_model_oid=SWITCH_MODEL_OID,
    switch_name_oid=SWITCH_NAME_OID,
    switch_sn_oid=SWITCH_SN_OID,
    kafka_bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    kafka_client_id=KAFKA_CLIENT_ID,
    ignore_tree_alert_keywords=INGORE_TREE_ALERT_KEYWORDS,
    kafka_topic=KAFKA_TOPIC,
    gcp_sync=GCP_SYNC,
    app_name="cmdb",
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
        },
    },
    redises={
        const.DEFAULT_RD_KEY: {
            const.RD_HOST_KEY: DEFAULT_REDIS_HOST,
            const.RD_PORT_KEY: DEFAULT_REDIS_PORT,
            const.RD_DB_KEY: DEFAULT_REDIS_DB,
            const.RD_AUTH_KEY: DEFAULT_REDIS_AUTH,
            const.RD_CHARSET_KEY: DEFAULT_REDIS_CHARSET,
            const.RD_PASSWORD_KEY: DEFAULT_REDIS_PASSWORD,
        }
    },
    consuls={
        const.DEFAULT_CS_KEY: {
            const.CONSUL_HOST_KEY: DEFAULT_CONSUL_HOST,
            const.CONSUL_PORT_KEY: DEFAULT_CONSUL_PORT,
            const.CONSUL_TOKEN_KEY: DEFAULT_CONSUL_TOKEN,
            const.CONSUL_SCHEME_KEY: DEFAULT_CONSUL_SCHEME,
        }
    },
    jmss={
        const.DEFAULT_JMS_KEY: {
            const.JMS_API_BASE_URL: JMS_API_BASE_URL,
            const.JMS_API_KEY_ID: JMS_API_KEY_ID,
            const.JMS_API_KEY_SECRET: JMS_API_KEY_SECRET,
        }
    },
)
