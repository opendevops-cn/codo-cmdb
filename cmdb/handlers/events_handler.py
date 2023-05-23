#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/2/15 14:59
Desc    : 事件管理
"""

from abc import ABC
from tornado.web import RequestHandler
from services.event_service import get_aws_event_list, get_aliyun_event_list,get_qcloud_event_list


class AwsHealthEventsHandler(RequestHandler, ABC):
    def get(self):
        params = {k: self.get_argument(k) for k in self.request.arguments}
        res = get_aws_event_list(**params)
        return self.write(res)


class AliyunEventsHandler(RequestHandler, ABC):
    def get(self):
        params = {k: self.get_argument(k) for k in self.request.arguments}
        res = get_aliyun_event_list(**params)
        return self.write(res)


class QcloudEventsHandler(RequestHandler, ABC):
    def get(self):
        params = {k: self.get_argument(k) for k in self.request.arguments}
        res = get_qcloud_event_list(**params)
        return self.write(res)


events_urls = [
    (r"/api/v2/cmdb/events/aws/", AwsHealthEventsHandler),
    (r"/api/v2/cmdb/events/aliyun/", AliyunEventsHandler),
    (r"/api/v2/cmdb/events/qcloud/", QcloudEventsHandler),
]
