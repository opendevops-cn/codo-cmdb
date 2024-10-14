#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# @File    :   gcp_nat.py
# @Time    :   2024/10/12 17:11:51
# @Author  :   DongdongLiu
# @Version :   1.0
# @Desc    :   Google Cloud Platform NAT网关实例
from __future__ import print_function
import logging
from datetime import datetime
from typing import *

from google.oauth2 import service_account
from google.cloud import compute_v1

from models.models_utils import vpc_task, mark_expired

class GCPNAT:
    def __init__(self, project_id: str, account_path: str, region: str,
                 account_id: str):
        self.cloud_name = 'gcp'
        self.page_size = 100  # 分页查询时设置的每页行数。最大值：100 默认值：10
        self._region = region
        self.project_id = project_id
        self._account_id = account_id
        self.__credentials = service_account.Credentials.from_service_account_file(
            account_path)
        self.client = compute_v1.NetworksClient(
            credentials=self.__credentials)
        
    
    def get_nat(self, project: str, network: str):
        """
        获取单个nat
        """
        request = compute_v1.GetNetworkRequest(network=network, project=project)
        response = self.client.get(request=request)
        return response
    
    def get_all_nats(self):
        """
        获取所有的nat
        """
        nats = []
        try:
            request = compute_v1.ListNetworksRequest()
            request.project = self.project_id
            request.max_results = self.page_size
            # request.page_token = ""
            page_result = self.client.list(request=request)
            for response in page_result:
                nats.append(self.handle_data(response))
        except Exception as e:
            logging.error(
                f"谷歌云NAT网关调用异常 get_all_nats： {self._account_id} -- {e}")
        return nats