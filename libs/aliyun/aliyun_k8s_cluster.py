#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# @File    :   aliyun_k8s_cluster.py
# @Time    :   2025/03/26 16:36:09
# @Author  :   DongdongLiu
# @Version :   1.0
# @Desc    :   阿里云k8s集群

import json
import logging
from typing import Any, Union
from aliyunsdkcore.client import AcsClient
from aliyunsdkcs.request.v20151215.DescribeClustersV1Request import DescribeClustersV1Request


class AliyunK8sCluster:
    def __init__(self, access_id: str, access_key: str, region: str, account_id: str):
        self.page_number = 1  # 实例状态列表的页码。起始值：1 默认值：1
        self.page_size = 100  # 分页查询时设置的每页行数。最大值：100 默认值：10
        self._access_id = access_id
        self._access_key = access_key
        self._region = region
        self._accountID = account_id
        self.__client = AcsClient(self._access_id, self._access_key, self._region)

    
    def get_k8s_cluster_instance(self) -> Union[Any]:
        """获取k8s集群实例"""
        try:
            request = DescribeClustersV1Request()
            request.set_page_number(self.page_number)
            request.set_page_size(self.page_size)
            response = self.__client.do_action_with_exception(request)
            response_data = json.loads(str(response, encoding="utf8"))
            return response_data
        except Exception as err:
            logging.error(f"获取k8s集群实例失败:{err}")
            return

    def get_all_k8s_cluster_instance(self):
        """获取所有k8s集群实例"""
        all_k8s_cluster_instance = []
        while True:
            response = self.get_k8s_cluster_instance()
            if not response:
                break
            clusters = response.get("clusters", {}).get("cluster", [])
            if not clusters:
                break
            all_k8s_cluster_instance.extend(clusters)
            if response.get("TotalCount", 0) < self.page_size:
                break
            self.page_number += 1
        return all_k8s_cluster_instance

    def process_k8s_cluster_instance(self, data: dict):
        """处理k8s集群实例"""
        return data


if __name__ == "__main__":
    pass
