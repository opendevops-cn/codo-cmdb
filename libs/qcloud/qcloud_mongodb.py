# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2025/3/10
# @Description: 腾讯云MongoDB

from __future__ import print_function

import logging
from typing import List, Union

from tencentcloud.common import credential
from tencentcloud.mongodb.v20190725 import mongodb_client, models

from models.models_utils import mongodb_task, mark_expired


class QcloudMongoDB:
    def __init__(self, access_id: str, access_key: str, region: str, account_id: str) -> None:
        self._offset = 0  # 偏移量,这里拼接的时候必须是字符串
        self._limit = 100  # 官方默认是20，大于100 需要设置偏移量再次请求：offset=100,offset={机器总数}
        self._access_id = access_id
        self._access_key = access_key
        self._region = region
        self._account_id = account_id

        self.region = region
        self.__cred = credential.Credential(self._access_id, access_key)
        self.client = mongodb_client.MongodbClient(self.__cred, self.region)
        self.req = models.DescribeDBInstancesRequest()

    def describe_mongodb_instance(self, offset: int) -> Union[models.DescribeDBInstancesResponse, None]:
        """获取mongodb实例
        Args:
            offset: 偏移量
        Return:
            models.DescribeDBInstancesResponse: mongodb实例响应
        """
        try:
            req = models.DescribeDBInstancesRequest()
            req.Limit = self._limit
            req.Offset = offset
            response = self.client.DescribeDBInstances(req)
            return response
        except Exception as e:
            logging.error(f"获取mongodb实例失败: {e}")
            return

    def describe_mongo_endpoint(self, instance_id: str) -> Union[models.DescribeDBInstanceURLRequest, None]:
        """获取mongodb实例的连接地址
        """
        req = models.DescribeDBInstanceURLRequest()
        req.InstanceId = instance_id
        try:
            response = self.client.DescribeDBInstanceURL(req)
            return response
        except Exception as e:
            logging.error(f"获取mongodb实例的连接地址失败: {e}")

    def get_all_mongodb_instance(self) -> List:
        all_mongodb_instance = []
        offset = self._offset
        while True:
            response = self.describe_mongodb_instance(offset)
            if not response:
                break
            instances = response.InstanceDetails
            if not instances:
                break
            all_mongodb_instance.extend([self.process_mongodb(data) for data in instances])
            if response.TotalCount < self._limit:
                break
            offset += self._limit
        return all_mongodb_instance

    @staticmethod
    def get_mongodb_class(val):
        return {
            0: "副本集",
            1: "分片集群"
        }.get(val, '未知')

    @staticmethod
    def get_mongodb_status(val):
        return {
            0: "创建中",
            1: "流程中",
            2: "运行中",
            -2: "已过期"
        }.get(val, '未知')

    @staticmethod
    def get_uri_type(uri_type: str) -> str:
        """获取MongoDB URI类别描述
        Args:
            uri_type: URI类型代码
        Return:
            str: URI类型描述
        """
        return {
            "CLUSTER_ALL": "主节点(读写)",
            "CLUSTER_READ_READONLY": "只读节点",
            "CLUSTER_READ_SECONDARY": "从节点",
            "CLUSTER_READ_SECONDARY_AND_READONLY": "只读从节点",
            "CLUSTER_PRIMARY_AND_SECONDARY": "主从节点",
            "MONGOS_ALL": "Mongos节点(读写)",
            "MONGOS_READ_READONLY": "Mongos只读节点",
            "MONGOS_READ_SECONDARY": "Mongos从节点",
            "MONGOS_READ_PRIMARY_AND_SECONDARY": "Mongos主从节点",
            "MONGOS_READ_SECONDARY_AND_READONLY": "Mongos从节点和只读节点"
        }.get(uri_type, "未知类型")

    @staticmethod
    def get_storage_engine(version: str) -> str:
        """获取存储引擎类型
        Args:
            version: 版本号字符串
        Return:
            str: 存储引擎名称
        """
        if '_WT' in version:
            return 'WiredTiger'
        if '_ROCKS' in version:
            return 'RocksDB'
        if '_INMEM' in version:
            return 'In-Memory'
        if '_MMAP' in version:
            return 'MMAPv1'
        return ''

    @staticmethod
    def format_mongo_version(version: str) -> str:
        """格式化MongoDB版本号
        Args:
            version: 原始版本号 (如 'MONGO_50_WT')
        Return:
            str: 格式化后的版本号 (如 '5.0 WiredTiger')
        """
        if not version:
            return ''
        try:
            parts = version.split('_')
            if len(parts) < 2:
                return version

            # 转换版本号
            version_num = f"{parts[1][0]}.{parts[1][1]}"

            # 添加存储引擎信息
            engine = QcloudMongoDB.get_storage_engine(version)
            if engine:
                return f"{version_num} {engine}"
            return version_num
        except Exception:
            return version

    def process_mongodb(self, data):
        """处理mongodb实例
        Args:
            data: mongodb实例数据
        Return:
            dict: 处理后的mongodb实例数据
        """
        db_addresses = []
        urls = self.describe_mongo_endpoint(data.InstanceId)
        if urls:
            db_addresses = [url.Address for url in urls.Urls if url.URLType=='CLUSTER_DEFAULT']


        tags = []
        if data.Tags:
            tags = [{"Key": tag.TagKey, "Value": tag.TagValue} for tag in data.Tags]

        try:
            db_version = self.format_mongo_version(data.MongoVersion)
        except Exception as e:
            logging.error(f"处理MongoDB版本号时出错: {e}")
            db_version = ''
        return {
            "instance_id": data.InstanceId,
            "name": data.InstanceName,
            "state": data.InstanceStatusDesc,
            "region": data.Region,
            "vpc_id": data.VpcId,
            "db_version": db_version,
            "subnet_id": data.SubnetId,
            "project_name": '',
            "db_class": self.get_mongodb_class(data.ClusterType),
            "storage_type": '',
            "db_address": db_addresses,
            'zone': data.Zone,
            "tags": tags,
        }

    def sync_cmdb(self, cloud_name: str = 'qcloud', resource_type: str = 'mongodb'):
        """同步mongodb实例到CMDB
        """
        all_mongodb_instance = self.get_all_mongodb_instance()
        if not all_mongodb_instance:
            return False, "mongodb实例列表为空"
        # 更新资源
        ret_state, ret_msg = mongodb_task(account_id=self._account_id,
                                          cloud_name=cloud_name,
                                          rows=all_mongodb_instance)
        # 标记过期
        mark_expired(resource_type=resource_type, account_id=self._account_id)
        return ret_state, ret_msg


if __name__ == '__main__':
    pass

