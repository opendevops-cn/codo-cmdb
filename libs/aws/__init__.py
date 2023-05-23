#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/1/27 11:02
"""

from typing import *
from libs.aws.aws_ec2 import AwsEc2Client
from libs.aws.aws_rds import AwsRDSClient
from libs.aws.aws_redis import AwsRedisClient
from libs.aws.aws_elb import AwsLbClient
from libs.aws.aws_health_events import AwsHealthClient

DEFAULT_CLOUD_NAME = 'aws'

# 同步的资产对应关系
mapping: Dict[str, dict] = {
    'ec2': {
        "type": "ec2",
        "obj": AwsEc2Client
    },
    'rds': {
        "type": "rds",
        "obj": AwsRDSClient
    },
    'redis': {
        "type": "redis",
        "obj": AwsRedisClient
    },
    'alb': {
        "type": "alb",
        "obj": AwsLbClient
    },
    'events': {
        "type": "events",
        "obj": AwsHealthClient
    }
}
