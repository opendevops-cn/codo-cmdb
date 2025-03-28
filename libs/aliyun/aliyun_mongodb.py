#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# @File    :   aliyun_mongodb.py
# @Time    :   2025/03/26 14:17:06
# @Author  :   DongdongLiu
# @Version :   1.0
# @Desc    :   阿里云mongoDb

import json
import logging
from typing import Dict, Union, Any

from aliyunsdkcore.client import AcsClient
from aliyunsdkdds.request.v20151201.DescribeDBInstancesRequest import DescribeDBInstancesRequest


class AliyunMongoDBClient:
    def __init__(self, access_id: str, access_key: str, region: str, account_id: str):
        self.page_number = 1  # 实例状态列表的页码。起始值：1 默认值：1
        self.page_size = 100  # 分页查询时设置的每页行数。最大值：100 默认值：10
        self._access_id = access_id
        self._access_key = access_key
        self._region = region
        self._accountID = account_id
        self.__client = AcsClient(self._access_id, self._access_key, self._region)

    def get_mongodb_instance(self) -> Union[Any]:
        """获取MongoDB实例"""
        try:
            request = DescribeDBInstancesRequest()
            request.set_PageNumber(self.page_number)
            request.set_PageSize(self.page_size)
            response = self.__client.do_action_with_exception(request)
            response_data = json.loads(str(response, encoding="utf8"))
        except Exception as err:
            logging.error(f"获取MongoDB信息失败:{err}")
            return
        return response_data

    def get_all_mongodb_instance(self) -> list:
        self.page_number = 1
        all_mongodb_instances = []
        while True:
            response = self.get_mongodb_instance()
            if not response:
                break
            db_instances = response.get("DBInstances", {}).get("DBInstance", [])
            if not db_instances:
                break
            all_mongodb_instances.extend([self.process_mongodb(item) for item in db_instances])
            if response.get("TotalCount", 0) < self.page_size:
                break
            self.page_number += 1
        return all_mongodb_instances

    def process_mongodb(self, data: Dict[Any]) -> Dict[Any]:
        """处理mongodb实例
        Args:
            data: mongodb实例数据
        Return:
            dict: 处理后的mongodb实例数据
        """
        return data


if __name__ == "__main__":
    pass
