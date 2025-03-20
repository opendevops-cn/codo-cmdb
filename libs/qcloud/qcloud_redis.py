#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date   : 2023/1/27 11:02
Desc   : 腾讯云 Redis
"""

import logging
from typing import *
from models.models_utils import redis_task, mark_expired
import json
from tencentcloud.common import credential
from tencentcloud.redis.v20180412 import redis_client, models


def get_run_type(val):
    """
    #取值来自腾讯云官方Docs:https://cloud.tencent.com/document/api/237/16191#DBInstance
    :param val:
    :return:
    """
    run_map = {
        0: "待初始化",
        1: "流程中",
        2: "运行中",
        -2: "已隔离",
        -3: "待删除",
    }
    return run_map.get(val, '未知')


def get_product_type(val):
    mapping = {
        "standalone": "标准版",
        "cluster": "集群版",
    }
    return mapping.get(val, val)


def get_type_version(val):
    version_map = {
        1: "Redis老集群版",
        2: "2.8主从版",
        3: "CKV主从版",
        4: "CKV集群版",
        5: "2.8单机版",
        6: "4.0主从版",
        7: "4.0集群版",
        8: "5.0主从版",
        9: "5.0集群版",
        15: "6.2标准版",
        16: "6.2集群版",

    }
    return version_map.get(val, val)


def get_pay_type(val):
    pay_map = {
        1: "包年包月",
        0: "按量付费",
        'prepaid': "包年包月",
        'postpaid': "按量付费"
    }
    return pay_map.get(val, '未知')


class QCloudRedis:
    def __init__(self, access_id: Optional[str], access_key: Optional[str], region: Optional[str],
                 account_id: Optional[str]):

        self.cloud_name = 'qcloud'
        self._offset = 0  # 偏移量,这里拼接的时候必须是字符串
        self._limit = 100  # 官方默认是20，大于100 需要设置偏移量再次请求：offset=100,offset={机器总数}
        self._region = region
        self._account_id = account_id
        self.__cred = credential.Credential(access_id, access_key)
        self.client = redis_client.RedisClient(self.__cred, self._region)

    def get_all_redis(self):

        redis_list = []
        limit = self._limit
        offset = self._offset
        req = models.DescribeInstancesRequest()
        try:
            while True:
                params = {
                    "Offset": offset,
                    "Limit": limit
                }
                req.from_json_string(json.dumps(params))
                resp = self.client.DescribeInstances(req)
                if not resp.InstanceSet:
                    break
                redis_list.extend(map(self.format_data, resp.InstanceSet))
                offset += self._limit
            return redis_list
        except Exception as err:
            logging.error(f"腾讯云Redis  get all redis {self._account_id} {err}")
            return []

    def format_data(self, data) -> Dict[str, Any]:
        res: Dict[str, Any] = dict()

        vpc_id = data.UniqVpcId
        network_type = '经典网络' if not vpc_id else '专有网络'

        res['instance_id'] = data.InstanceId
        res['vpc_id'] = vpc_id
        res['vswitch_id'] = data.UniqSubnetId
        res['create_time'] = data.Createtime
        res['charge_type'] = get_pay_type(data.BillingMode)
        res['region'] = self._region
        res['zone'] = self._region
        try:
            res['az_mode'] = data.AzMode
        except Exception as err:
            res['az_mode'] = ''
        res['qps'] = ''
        res['name'] = data.InstanceName
        res['instance_class'] = f'{data.Size}MB'
        res['instance_arch'] = get_product_type(data.ProductType)
        res['instance_type'] = data.Engine
        res['instance_version'] = get_type_version(data.Type)
        res['state'] = get_run_type(data.Status)
        res['network_type'] = network_type
        res['instance_address'] = {
            "items": [
                {
                    "type": "private",
                    "ip": data.WanIp,
                    "domain": "",
                    "port": str(data.Port)
                },
                {
                    "type": "public",
                    "ip": '',
                    "domain": "",
                    "port": ''
                }
            ]
        }

        return res

    def sync_cmdb(self, cloud_name: Optional[str] = 'qcloud', resource_type: Optional[str] = 'redis') -> Tuple[
        bool, str]:
        """
        资产信息更新到DB
        :return:
        """
        all_redis_list: List[dict] = self.get_all_redis()
        if not all_redis_list: return False, "redis列表为空"
        # 更新资源
        ret_state, ret_msg = redis_task(account_id=self._account_id, cloud_name=cloud_name, rows=all_redis_list)
        # 标记过期
        mark_expired(resource_type=resource_type, account_id=self._account_id)

        return ret_state, ret_msg


if __name__ == '__main__':
    pass
