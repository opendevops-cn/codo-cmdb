#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2019/6/12 16:18
Desc    : 阿里云 OSS
"""

import json
import logging
from typing import *
import oss2


class OssApi:

    def __init__(self, access_id: Optional[str], access_key: Optional[str], region: Optional[str],
                 account_id: Optional[str]):
        self._region = region
        self._account_id = account_id

        self.endpoint = 'http://oss-cn-hangzhou.aliyuncs.com'
        self.auth = oss2.Auth(access_id, access_key)
        self.service = oss2.Service(self.auth, self.endpoint)

    def tz_get_buckets(self):
        try:
            return [b.name for b in oss2.BucketIterator(self.service)]
        except Exception as err:
            logging.error(f"阿里云对象存储 get_region_cdn{self._account_id} {err}")
            return False

    def index(self):
        if not self.tz_get_buckets(): return False

        for bucket_name in self.tz_get_buckets():
            try:
                bucket = oss2.Bucket(self.auth, self.endpoint, bucket_name)
                bucket_info = bucket.get_bucket_info()
                # intranet_endpoint = bucket_info.intranet_endpoint
                # extranet_endpoint = bucket_info.extranet_endpoint
                # print(intranet_endpoint,extranet_endpoint)
                # bucket = oss2.Bucket(self.auth, bucket_info.intranet_endpoint, bucket_name)
                # result = bucket.get_bucket_tagging()
                # print('get_bucket_tagging',result)
            except Exception as err:
                logging.error(f"阿里云对象存储  {self._account_id} {err}")
                return False
