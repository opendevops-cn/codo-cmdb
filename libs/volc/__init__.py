#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import *
from libs.volc.volc_ecs import VolCECS

# 用来标记这是阿里云的作业
DEFAULT_CLOUD_NAME = 'volc'

# 同步的资产对应关系
mapping: Dict[str, dict] = {
    '服务器': {
        "type": "ecs",
        "obj": VolCECS
    }
}
