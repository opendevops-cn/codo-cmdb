#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import *
from libs.aliyun.aliyun_ecs import AliyunEcsClient
from libs.aliyun.aliyun_polardb import AliyunPolarDBClient
from libs.aliyun.aliyun_rds import AliyunRDSClient
from libs.aliyun.aliyun_redis import AliyunRedisClient
from libs.aliyun.aliyun_alb import AliyunALbClient
from libs.aliyun.aliyun_slb import AliyunSLbClient
from libs.aliyun.aliyun_vpc import AliyunVPC
from libs.aliyun.aliyun_vswitch import AliyunVSwitch
from libs.aliyun.aliyun_security_group import AliyunSecurityGroup
from libs.aliyun.aliyun_events import AliyunEventClient

# 用来标记这是阿里云的作业
DEFAULT_CLOUD_NAME = 'aliyun'

# 同步的资产对应关系
mapping: Dict[str, dict] = {
    'ecs': {
        "type": "ecs",
        "obj": AliyunEcsClient
    },
    'polardb': {
        "type": "polardb",
        "obj": AliyunPolarDBClient
    },
    'rds': {
        "type": "rds",
        "obj": AliyunRDSClient
    },
    'redis': {
        "type": "redis",
        "obj": AliyunRedisClient
    },
    'alb': {
        "type": "alb",
        "obj": AliyunALbClient
    },
    'slb': {
        "type": "slb",
        "obj": AliyunSLbClient
    },
    '虚拟局域网': {
        "type": "vpc",
        "obj": AliyunVPC
    },
    '虚拟子网': {
        "type": "vswitch",
        "obj": AliyunVSwitch
    },
    '安全组': {
        "type": "security_group",
        "obj": AliyunSecurityGroup
    },
    'events': {
        "type": "events",
        "obj": AliyunEventClient
    }
}
