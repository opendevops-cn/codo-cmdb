#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2019/6/12 16:18
Desc    : 阿里云 EIP
"""

import json
import logging
from typing import *
import json
from aliyunsdkcore.client import AcsClient
from aliyunsdkvpc.request.v20160428.DescribeEipAddressesRequest import DescribeEipAddressesRequest


class EIPApi:
    def __init__(self, access_id: Optional[str], access_key: Optional[str], region: Optional[str],
                 account_id: Optional[str]):
        self._region = region
        self._account_id = account_id
        self.request_eip = DescribeEipAddressesRequest()
        self.request_eip.set_accept_format('json')
        self.client = AcsClient(access_id, access_key, 'cn-hangzhou')

    def get_region_eip(self, page_number=1, page_size=20):
        try:
            self.request_eip.set_PageNumber(page_number)
            self.request_eip.set_PageSize(page_size)
            response = self.client.do_action_with_exception(self.request_eip)

            return json.loads(str(response, encoding="utf8"))['EipAddresses']
        except Exception as err:
            logging.error(f"阿里云EIP  get region eip {self._account_id} {self._region} {err}")
            return False

    def get_eip_all(self):
        page_num = 1
        while True:
            data = self.get_region_eip(page_num)
            if not data or 'EipAddress' not in data: break
            if not data['EipAddress']: break
            page_num += 1
            row = data['EipAddress']
            if not row: break
            yield row

    def index(self):
        eip_all = self.get_eip_all()
        if not eip_all: return False

        for eip_set in eip_all:

            for eip in eip_set:
                print(eip)
