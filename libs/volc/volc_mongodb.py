# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2025/3/10
# @Description: 火山云mongodb

from __future__ import print_function

import logging
from typing import Optional, Tuple

import volcenginesdkcore
from volcenginesdkcore.rest import ApiException
from volcenginesdkmongodb import MONGODBApi, DescribeDBInstancesRequest, DescribeDBEndpointRequest

from models.models_utils import mongodb_task, mark_expired


def get_mongodb_status(val):
    status_mapping = {
        'Running': '运行中',
    }
    return status_mapping.get(val, '未知')


def get_mongodb_class(val):
    class_mapping = {
        "ReplicaSet": "副本集",
        "ShardedCluster": "分片集群"
    }
    return class_mapping.get(val, '未知')


class VolcMongoDB:
    def __init__(self, access_id: str, access_key: str, region: str, account_id: str) -> None:
        self.cloud_name = 'volc'
        self.page_number = 1  # 实例状态列表的页码。起始值：1 默认值：1
        self.page_size = 100  # 分页查询时设置的每页行数。最大值：100 默认值：10
        self._region = region
        self._account_id = account_id
        self.api_instance = self.__initialize_api_instance(access_id, access_key, region)

    @staticmethod
    def __initialize_api_instance(access_id: str, access_key: str, region: str):
        """
        初始化api实例对象
        https://api.volcengine.com/api-sdk/view?serviceCode=mongodb&version=2022-01-01&language=Python
        :param access_id:
        :param access_key:
        :param region:
        :return:
        """
        configuration = volcenginesdkcore.Configuration()
        configuration.ak = access_id
        configuration.sk = access_key
        configuration.region = region
        return MONGODBApi(volcenginesdkcore.ApiClient(configuration))

    def get_mongodb(self):
        """
        获取mongodb实例
        """
        request = DescribeDBInstancesRequest(page_number=self.page_number, page_size=self.page_size)
        try:
            api_response = self.api_instance.describe_db_instances(request)
            return api_response
        except ApiException as e:
            logging.error(f"火山云调用mongodb实例列表异常 get_mongodb: {self._account_id} -- {e}")
            return None

    def describe_mongodb_endpoint(self, instance_id):
        """
        获取mongodb实例的连接地址
        Args:
            instance_id: 实例id
        Returns:
            dict: mongodb实例详情
        """
        request = DescribeDBEndpointRequest(instance_id=instance_id)
        try:
            api_response = self.api_instance.describe_db_endpoint(request)
            return api_response
        except ApiException as e:
            logging.error(f"火山云调用mongodb实例详情异常 describe_mongodb_endpoint: {self._account_id} -- {e}")
            return

    def get_all_mongodb(self):
        mongodb_list = []
        while True:
            data = self.get_mongodb()
            if data is None:
                break
            instances = data.db_instances
            if not instances:
                break
            mongodb_list.extend([self.process_mongodb(instance) for instance in instances])
            if data.total < self.page_size:
                break
            self.page_number += 1
        return mongodb_list

    def process_mongodb(self, data) -> dict:
        """
        处理mongodb数据
        Args:
            data: mongodb实例数据
        Returns:
            dict: 处理后的数据
        """
        db_addresses = []
        try:
            if endpoint := self.describe_mongodb_endpoint(data.instance_id):
                for item in endpoint.db_endpoints:
                    if item.network_type == 'Private':
                        db_addresses.extend(item.endpoint_str.split(','))
        except Exception as e:
            logging.warning(f"处理MongoDB连接地址时出错: {e}")

        tags = []
        if data.tags:
            tags = [{'key': tag.key, 'value': tag.value} for tag in data.tags]
        return {
            "instance_id": data.instance_id,
            "name": data.instance_name,
            "state": get_mongodb_status(data.instance_status),
            "region": self._region,
            "vpc_id": data.vpc_id,
            "db_version": data.db_engine_version_str,
            "subnet_id": data.subnet_id,
            "project_name": data.project_name,
            "db_class": get_mongodb_class(data.instance_type),
            "storage_type": data.storage_type,
            "db_address": list(set(db_addresses)),
            'zone': data.zone_id,
            "tags": tags,
        }

    def sync_cmdb(self, cloud_name: Optional[str] = 'volc', resource_type: Optional[str] = 'mongodb') -> Tuple[
        bool, str]:
        """
        资产信息更新到DB
        :param cloud_name:
        :param resource_type:
        :return:
        """
        all_mongodb = self.get_all_mongodb()
        if not all_mongodb:
            return False, "mongodb实例列表为空"
        # 更新资源
        ret_state, ret_msg = mongodb_task(account_id=self._account_id,
                                          cloud_name=cloud_name,
                                          rows=all_mongodb)
        # 标记过期
        mark_expired(resource_type=resource_type, account_id=self._account_id)
        return ret_state, ret_msg


if __name__ == '__main__':
    pass
