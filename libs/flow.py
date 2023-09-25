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
from websdk2.client import AcsClient
from websdk2.api_set import api_set


class FlowAPI:
    
    @staticmethod
    def create_flow(data):

        client = AcsClient()
        api_set.create_jobs["body"] = data
        response = client.do_action(**api_set.create_jobs)
        return json.loads(response)

    @staticmethod
    def get_flow_create_status(flow_id):
        params = {
            "filter_map": json.dumps({"id": flow_id})
        }
        client = AcsClient()
        api_set.get_current_order_list["params"] = params
        response = client.do_action(**api_set.get_current_order_list)
        return json.loads(response)

    @staticmethod
    def get_flow_history_status(flow_id):
        params = {
            "filter_map": json.dumps({"id": flow_id})
        }
        client = AcsClient()
        api_set.get_history_order_list ["params"] = params
        response = client.do_action(**api_set.get_history_order_list )
        return json.loads(response)



