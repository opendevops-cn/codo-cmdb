#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023-2-08
"""

from typing import Dict
from libs.qcloud.qcloud_cvm import QCloudCVM
from libs.qcloud.qcloud_cdb import QCloudCDB
from libs.qcloud.qcloud_redis import QCloudRedis
from libs.qcloud.qcloud_lb import QCloudLB
from libs.qcloud.qcloud_eip import QCloudEIP
from libs.qcloud.qcloud_vpc import QCloudCVPC
from libs.qcloud.qcloud_vswitch import QcloudVSwitch
from libs.qcloud.qcloud_security_group import QCloudSecurityGroup
from libs.qcloud.qcloud_events import QCloudEventClient
from libs.qcloud.qcloud_img import QCloudCImg

DEFAULT_CLOUD_NAME = 'qcloud'
# 同步的资产对应关系
mapping: Dict[str, dict] = {
    '云主机': {
        "type": "cvm",
        "obj": QCloudCVM
    },
    'CDB': {
        "type": "cdb",
        "obj": QCloudCDB
    },
    'Redis': {
        "type": "redis",
        "obj": QCloudRedis
    },
    '负载均衡': {
        "type": "lb",
        "obj": QCloudLB
    },
    '弹性IP': {
        "type": "eip",
        "obj": QCloudEIP
    },
    '虚拟局域网': {
        "type": "vpc",
        "obj": QCloudCVPC
    },
    '虚拟子网': {
        "type": "vswitch",
        "obj": QcloudVSwitch
    },
    '安全组': {
        "type": "security_group",
        "obj": QCloudSecurityGroup
    },
    '系统镜像': {
        "type": "image",
        "obj": QCloudCImg
    },
    '维修任务': {
        "type": "events",
        "obj": QCloudEventClient
    }
}
