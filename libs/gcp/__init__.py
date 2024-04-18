#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import *
from libs.gcp.gcp_ecs import GCPECS
from libs.gcp.gcp_cdb import GCPCDB
from libs.gcp.gcp_lb import GCPLB
from libs.gcp.gcp_redis import GCPRedis
from libs.gcp.gcp_security_group import GCPSecurityGroup
from libs.gcp.gcp_vpc import GCPVPC
from libs.gcp.gcp_vswitch import GCPSubnet

# 用来标记谷歌云的作业
DEFAULT_CLOUD_NAME = 'gcp'

# 同步的资产对应关系
mapping: Dict[str, dict] = {
    '服务器': {
        "type": "ecs",
        "obj": GCPECS
    },
    'Redis': {
        "type": "redis",
        "obj": GCPRedis
    },
    'CDB': {
        "type": "cdb",
        "obj": GCPCDB
    },
    '负载均衡': {
        "type": "lb",
        "obj": GCPLB
    },
    '虚拟局域网': {
        "type": "vpc",
        "obj": GCPVPC
    },
    '虚拟子网': {
        "type": "vswitch",
        "obj": GCPSubnet
    },
    '安全组': {
        "type": "security_group",
        "obj": GCPSecurityGroup
    },
}
