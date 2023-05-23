#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2019/6/12 16:18
Desc    : 阿里云CDN
"""

import json
import logging
from typing import *
from aliyunsdkcore.client import AcsClient
from aliyunsdkcdn.request.v20180510.DescribeUserDomainsRequest import DescribeUserDomainsRequest


class CDNApi:
    def __init__(self, access_id: Optional[str], access_key: Optional[str], region: Optional[str],
                 account_id: Optional[str]):
        self._region = region
        self._account_id = account_id
        self.client = AcsClient(access_id, access_key, 'cn-hangzhou')

    def get_region_cdn(self, page_number=1, page_size=50):
        try:
            request = DescribeUserDomainsRequest()
            request.set_accept_format('json')
            request.set_PageNumber(page_number)
            request.set_PageSize(page_size)
            response = self.client.do_action_with_exception(request)
            return json.loads(str(response, encoding="utf8"))
        except Exception as err:
            logging.error(f"阿里云CDN  get_region_cdn{self._account_id} {err}")
            return False

    def get_cdn_all(self):
        page_num = 1
        while True:
            data = self.get_region_cdn(page_num)
            if not data or 'Domains' not in data: break
            page_num += 1
            row = data['Domains']['PageData']
            if not row: break
            yield row

    def index(self):
        """
        入库
        :return:
        """
        cdn_info_list = self.get_cdn_all()
        if not cdn_info_list: return False

        for data in cdn_info_list:
            for i in data:
                print(i)
