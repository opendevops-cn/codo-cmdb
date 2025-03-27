#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author: shenshuo
Date  : 2023/2/25
Desc  : 首都在线redis同步
"""

from models.models_utils import redis_task, mark_expired, mark_expired_by_sync
import logging
from typing import *
from . import CDSApi


def get_run_type(val: str) -> str:
    run_map = {
        "CREATING": "创建中",
        "RUNNING": "运行中",
        "stop": "关机",
    }
    return run_map.get(val, '未知')


class CDSRedisApi(CDSApi):
    def __init__(self, access_id: str, access_key: str, region: str, account_id: str):
        self._access_id = access_id
        self._access_key = access_key
        self._region = region
        self._account_id = account_id
        super(CDSRedisApi, self).__init__(access_id, access_key, region, account_id)

    def format_data(self, data: Optional[dict]) -> Dict[str, Any]:
        """
        处理数据
        :param data:
        :return:
        """
        # logging.error(f"__info {data}")
        res: Dict[str, Any] = dict()
        res['instance_id'] = data.get('InstanceUuid')
        res['account_id'] = self._account_id
        res['state'] = get_run_type(data['Status'])
        res['charge_type'] = data.get('InstanceType')
        res['instance_class'] = f"{float(data['Ram'])}MB"
        # res['instance_address'] = data['IP']
        res['memory'] = float(data['Ram'])
        res['name'] = data.get('InstanceName')
        res['region'] = data.get('RegionId')
        res['zone'] = data.get('RegionId')
        res['instance_version'] = data.get('Version')
        res['instance_arch'] = data.get('SubProductName')
        res['instance_address'] = {
            "items": [
                {
                    "endpoint_type": "Primary",
                    "type": "private",
                    "port": data.get('Port'),
                    "ip": data.get('IP'),
                    "domain": "",
                },
                {
                    "endpoint_type": "Primary",
                    "type": "public",
                    "port": "",
                    "ip": "",
                    "domain": "",
                },
            ]
        }
        res['create_time'] = data.get('CreatedTime')
        return res

    def fetch_redis_instances(self):
        params = {
            "action": "DescribeDBInstances",
            "method": "GET",
            "url": "http://cdsapi.capitalonline.net/redis"
        }
        res = self.make_requests(method="GET", params=params)
        row = res["Data"]
        return map(self.format_data, row)

    def sync_cmdb(self, cloud_name: Optional[str] = 'cds', resource_type: Optional[str] = 'redis') -> Tuple[
        bool, str]:
        """
        同步CMDB
        :return:
        """
        # 机器比较少 根本用不上迭代器
        all_redis = self.fetch_redis_instances()
        all_redis_list: List[dict] = []
        for _server_map in all_redis:
            all_redis_list.append(_server_map)

        if not all_redis_list: return False, "Redis列表为空"
        # # 更新资源
        ret_state, ret_msg = redis_task(account_id=self._account_id, cloud_name=cloud_name, rows=all_redis_list)
        # 标记过期
        # mark_expired(resource_type=resource_type, account_id=self._account_id)
        instance_ids = [redis['instance_id'] for redis in all_redis_list]
        mark_expired_by_sync(cloud_name=cloud_name, account_id=self._account_id, resource_type=resource_type,
                             instance_ids=instance_ids, region=self._region)
        return ret_state, ret_msg
