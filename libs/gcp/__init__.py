#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import *
from libs.gcp.gcp_ecs import GCPECS

# 用来标记这是云的作业
DEFAULT_CLOUD_NAME = 'gcp'

# 同步的资产对应关系
mapping: Dict[str, dict] = {
    '服务器': {
        "type": "ecs",
        "obj": GCPECS
    }
}
