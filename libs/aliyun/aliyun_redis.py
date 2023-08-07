#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date   :  2023/1/27 11:02
Desc   :  阿里云 Redis
"""

import json
import logging
from typing import *
from models.models_utils import redis_task, mark_expired
from aliyunsdkcore.client import AcsClient
from aliyunsdkr_kvstore.request.v20150101.DescribeInstancesRequest import DescribeInstancesRequest
from aliyunsdkr_kvstore.request.v20150101.DescribeDBInstanceNetInfoRequest import DescribeDBInstanceNetInfoRequest


def get_run_type(val):
    run_map = {
        "Creating": "创建中",
        "Normal": "运行中",
        "Released": "已释放",
        "Inactive": "被禁用",
        "Unavailable": "服务停止",
        "Error": "创建失败",
        "Migrating": "迁移中",
        "Transforming": "转换中",
        "Flushing": "清除中",
        "Changing": "修改中",
        "BackupRecovering": "备份恢复中",
        "MinorVersionUpgrading": "小版本升级中",
        "NetworkModifying": "网络变更中",
        "SSLModifying": "SSL变更中",
        "MajorVersionUpgrading": "大版本升级中"
    }
    return run_map.get(val, '未知')


def get_paymeny_type(val):
    pay_map = {
        "PrePaid": "包年包月",
        "PostPaid": "按量付费"
    }
    return pay_map.get(val, '未知')


def get_network_type(val):
    network_map = {
        "CLASSIC": "经典网络",
        "VPC": "专有网络"
    }
    return network_map.get(val, '未知')


def get_arch_type(val):
    arch_map = {
        "cluster": "集群版",
        "standard": "标准版",
        "SplitRW": "读写分离版"
    }
    return arch_map.get(val, '未知')


# 转换type
def get_endpoint_type(val):
    type_map = {
        "Public": "public",
        "Private": "private",
        "Inner": "private",
    }
    return type_map.get(val, val)


class AliyunRedisClient:
    def __init__(self, access_id: Optional[str], access_key: Optional[str], region: Optional[str],
                 account_id: Optional[str]):
        self.page_number = 1  # 实例状态列表的页码。起始值：1 默认值：1
        self.page_size = 100  # 分页查询时设置的每页行数。最大值：100 默认值：10
        self._access_id = access_id
        self._access_key = access_key
        self._region = region
        self._accountID = account_id
        self.__client = AcsClient(self._access_id, self._access_key, self._region)

    def get_redis_response(self) -> Tuple[bool, dict]:
        try:
            request = DescribeInstancesRequest()
            request.set_accept_format('json')
            request.set_PageNumber(self.page_number)
            request.set_PageSize(self.page_size)
            response = self.__client.do_action_with_exception(request)
            response = json.loads(str(response, encoding="utf8"))
            # redis_total = response.get('TotalCount')
            # logging.info(f'Aliyun account: {self._accountID} {self._region} redis total is {redis_total}')
        except Exception as error:
            logging.error(f'Get redis response error: {error}')
            return False, {}
        return True, response

    def get_all_redis(self) -> List[dict]:
        """
        获取所有redis信息
        :return:
        """
        self.page_number = 1
        all_redis_list: List[Dict] = []
        while True:
            is_success, response = self.get_redis_response()
            if not is_success or not response: break
            if 'Instances' not in response: break
            self.page_number += 1
            rows = response.get('Instances').get('KVStoreInstance')
            if not rows: break
            for data in rows:
                redis_data = self._format_data(data)
                all_redis_list.append(redis_data)

        return all_redis_list

    def get_redis_endpoints(self, instance_id: Optional[str]) -> Dict[str, List[dict]]:
        """
        调用DescribeDBInstanceNetInfo查看Redis实例的网络信息。
        :param instance_id:
        :return:
        """
        request = DescribeDBInstanceNetInfoRequest()
        request.set_accept_format('json')
        request.set_InstanceId(instance_id)
        response = self.__client.do_action_with_exception(request)
        response = json.loads(str(response, encoding="utf8"))
        try:
            endpoints = response['NetInfoItems']['InstanceNetInfo']
        except KeyError as err:
            logging.error(f'Get redis endpoints error: {err}')
            return {}
        mapping = {
            "type": "IPType",
            "port": "Port",
            "ip": "IPAddress",
            "domain": "ConnectionString"
        }
        instance_address: Dict[str, List[Dict]] = {"items": []}
        instance_address['items'].extend([
            {
                k: get_endpoint_type(data[v])
                for k, v in mapping.items()
            }
            for data in endpoints
        ])
        return instance_address

    def _format_data(self, data: Optional[Dict]) -> Dict[str, Any]:
        res: Dict[str, Any] = dict()
        res['instance_id'] = data.get('InstanceId')
        res['create_time'] = data.get('CreateTime')
        res['charge_type'] = get_paymeny_type(data.get('ChargeType'))
        res['region'] = data.get('RegionId')
        res['zone'] = data.get('ZoneId')
        res['qps'] = data.get('QPS')
        res['name'] = data.get('InstanceName')
        res['instance_class'] = data.get('InstanceClass')
        res['instance_arch'] = get_arch_type(data.get('ArchitectureType'))
        res['instance_type'] = data.get('InstanceType')
        res['instance_version'] = data.get('EngineVersion')
        res['state'] = get_run_type(data.get('InstanceStatus'))
        res['network_type'] = get_network_type(data.get('NetworkType'))
        res['instance_address'] = self.get_redis_endpoints(data.get('InstanceId'))
        return res

    def sync_cmdb(self, cloud_name: Optional[str] = 'aliyun', resource_type: Optional[str] = 'redis') -> Tuple[
        bool, str]:
        # 获取数据
        all_redis_list: List[dict] = self.get_all_redis()
        if not all_redis_list: return False, "Redis列表为空"
        # 更新资源
        ret_state, ret_msg = redis_task(account_id=self._accountID, cloud_name=cloud_name, rows=all_redis_list)
        # 标记过期
        mark_expired(resource_type=resource_type, account_id=self._accountID)

        return ret_state, ret_msg


if __name__ == '__main__':
    pass
