#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/2/15 14:59
Desc    : 事件管理
"""

from abc import ABC
from libs.base_handler import BaseHandler
from services.event_service import get_aws_event_list, get_aliyun_event_list, get_qcloud_event_list


class AwsHealthEventsHandler(BaseHandler, ABC):
    def get(self):
        res = get_aws_event_list(**self.params)
        return self.write(res)


class AliyunEventsHandler(BaseHandler, ABC):
    def get(self):
        res = get_aliyun_event_list(**self.params)
        return self.write(res)


class QcloudEventsHandler(BaseHandler, ABC):
    def get(self):
        res = get_qcloud_event_list(**self.params)
        return self.write(res)


events_urls = [
    (r"/api/v2/cmdb/events/aws/", AwsHealthEventsHandler,
     {"handle_name": "配置平台-云商-事件管理-AWS", "method": ["ALL"]}),
    (r"/api/v2/cmdb/events/aliyun/", AliyunEventsHandler,
     {"handle_name": "配置平台-云商-事件管理-阿里云", "method": ["ALL"]}),
    (r"/api/v2/cmdb/events/qcloud/", QcloudEventsHandler,
     {"handle_name": "配置平台-云商-事件管理-腾讯云", "method": ["ALL"]}),
]
