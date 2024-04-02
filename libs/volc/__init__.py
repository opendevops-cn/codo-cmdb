#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import *
from libs.volc.volc_ecs import VolCECS
from libs.volc.volc_redis import VolCRedis
from libs.volc.volc_rds import VolCRDS
from libs.volc.volc_clb import VolCCLB
from libs.volc.volc_vpc import VolCVPC

# 用来标记这是火山云的作业
DEFAULT_CLOUD_NAME = 'volc'

# 同步的资产对应关系
mapping: Dict[str, dict] = {
    '服务器': {
        "type": "ecs",
        "obj": VolCECS
    },
    'Redis': {
        "type": "redis",
        "obj": VolCRedis
    },
    'CDB': {
        "type": "cdb",
        "obj": VolCRDS
    },
    '负载均衡': {
        "type": "lb",
        "obj": VolCCLB
    },
    '虚拟局域网': {
        "type": "vpc",
        "obj": VolCVPC
    },
}
