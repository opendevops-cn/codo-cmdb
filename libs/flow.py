#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 1084430062@qq.com
Author  : 娄文军
Date    : 2023/7/19 14:59
Desc    :
"""

import requests
import logging
import time
import json

auth_key = ""
# from websdk2.client import AcsClient
# from websdk2.api_set import api_set
#
# client = AcsClient()
#
# xxx = dict(method='POST', url=f'job/v3/notifications/group/',
#            data={})
# response = await client.do_action_with_async(**xxx)


class FlowAPI(object):

    def __init__(self):
        self.try_num = 3
        self.host_name = ""
        self.headers = {"Sdk-Method": "zQtY4sw7sqYspVLrqV", "Cookie": f"auth_key={auth_key}"}

    def request(self, method, url, **kwargs):
        reqs, response = None, None
        if method == "GET":
            reqs = requests.get
        elif method == "POST":
            reqs = requests.post

        for i in range(self.try_num):
            response = reqs(url=url, headers=self.headers, **kwargs)
            logging.info(response.text)
            if response.status_code != 200:
                logging.error(f"flow重试:{i} 回调失败:{response.text}")
                time.sleep(3)
            else:
                break
        return response

    def create_flow(self, data):
        url = f"{self.host_name}/api/job/v1/flow/accept/create/"
        return self.request(method="POST", url=url, data=data)

    def get_flow_create_status(self, flow_id):
        url = f"{self.host_name}/api/job/v1/flow/current/list/"
        params = {
            "filter_map": json.dumps({"id": flow_id})
        }
        return self.request(method="GET", url=url, params=params)

    def get_flow_history_status(self, flow_id):
        url = f"{self.host_name}/api/job/v1/flow/history/list/"
        params = {
            "filter_map": json.dumps({"id": flow_id})
        }
        return self.request(method="GET", url=url, params=params)
