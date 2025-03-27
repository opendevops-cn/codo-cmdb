#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date   :  2023/1/27 11:02
Desc   :  AWS Elasticache
Docs   :  https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/elasticache.html#ElastiCache.Client.describe_replication_groups
"""

import logging
import boto3
from typing import *
from models.models_utils import redis_task, mark_expired, mark_expired_by_sync


class AwsRedisClient:
    def __init__(self, access_id: Optional[str], access_key: Optional[str], region: Optional[str],
                 account_id: Optional[str]):
        self._access_id = access_id
        self._access_key = access_key
        self._region = region
        self._accountID = account_id
        self.__client = self.create_client()

    def create_client(self) -> Union[None, boto3.client]:
        try:
            client = boto3.client('elasticache', region_name=self._region, aws_access_key_id=self._access_id,
                                  aws_secret_access_key=self._access_key)
        except Exception as err:
            logging.error(f'aws elasticache boto3 create client error:{err}')
            client = None
        return client

    def get_all_redis(self) -> List[Dict[str, Any]]:
        """
        Docs:https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/elasticache.html#ElastiCache.Client.describe_replication_groups
        :return:
        """
        try:
            # rsp : List[Dict[str, str]]
            response = self.__client.describe_replication_groups(MaxRecords=100)
            redis_clusters = response.get('ReplicationGroups')
            if not redis_clusters: return []
            redis_list = list(map(self._format_data, redis_clusters))
        except Exception as err:
            logging.error(f'get aws redis error, {err}')
            return []
        return redis_list

    def _format_data(self, data: dict) -> Dict[str, Any]:
        res: Dict[str, Any] = dict()
        res['instance_id'] = data.get('ReplicationGroupId')
        res['name'] = data.get('ReplicationGroupId')
        res['state'] = '运行中' if data.get('Status') == 'available' else data.get('Status')
        res['instance_class'] = data.get('CacheNodeType')
        res['charge_type'] = '按量付费'
        res['instance_network'] = '专有网络'
        res['region'] = self._region
        res['zone'] = self._region
        res['instance_type'] = 'Redis'
        res['instance_arch'] = 'unknown'
        res['instance_version'] = 'unknown'
        res['instance_address'] = self.get_redis_endpoints(data.get('NodeGroups'))
        return res

    @staticmethod
    def get_redis_endpoints(endpoints: Optional[List[Dict]]) -> Dict[str, List[dict]]:
        redis_address = {"items": []}
        for _endpoint in endpoints:
            _dict = {
                "type": "private",
                "domain": _endpoint.get('PrimaryEndpoint').get('Address'),  # 只拿了主地址(访问地址)
                "ip": "",
                "port": _endpoint.get('PrimaryEndpoint').get('Port')
            }
            redis_address['items'].append(_dict)
        return redis_address

    def sync_cmdb(self, cloud_name: Optional[str] = 'aws', resource_type: Optional[str] = 'redis') -> Tuple[
        bool, str]:
        # 获取数据
        all_redis_list: List[dict] = self.get_all_redis()
        if not all_redis_list: return False, "Redis列表为空"

        # 更新资源
        ret_state, ret_msg = redis_task(account_id=self._accountID, cloud_name=cloud_name, rows=all_redis_list)
        # 标记过期
        # mark_expired(resource_type=resource_type, account_id=self._accountID)
        instance_ids = [row['instance_id'] for row in all_redis_list]
        mark_expired_by_sync(cloud_name=cloud_name, account_id=self._accountID, resource_type=resource_type,
                             instance_ids=instance_ids, region=self._region)

        return ret_state, ret_msg


if __name__ == '__main__':
    pass
