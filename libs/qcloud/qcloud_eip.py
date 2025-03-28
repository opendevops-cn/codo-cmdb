#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2019/1/6 17:51
Desc    : 腾讯云 EIP
"""

from typing import *
import json
import logging
from tencentcloud.common import credential
from tencentcloud.vpc.v20170312 import vpc_client, models
from models.models_utils import eip_task, mark_expired, mark_expired_by_sync


def get_network_pay_type(val):
    pay_map = {
        "BANDWIDTH_PACKAGE": "共享带宽包",
        "BANDWIDTH_POSTPAID_BY_HOUR": "按小时后付费",
        "BANDWIDTH_PREPAID_BY_MONTH": "按月预付费",
        "TRAFFIC_POSTPAID_BY_HOUR": "流量后付费",
    }
    return pay_map.get(val, '未知')


def get_state_type(val):
    state_map = {
        "UNBIND": "未使用",
        "BIND": "使用",
    }
    return state_map.get(val, '未知')


class QCloudEIP:
    def __init__(self, access_id: str, access_key: str, region: str, account_id):
        self._region = region
        self._offset = 0  # 偏移量,这里拼接的时候必须是字符串
        self._limit = 100  # 官方默认是20，大于100 需要设置偏移量再次请求
        self._account_id = account_id
        self.__cred = credential.Credential(access_id, access_key)
        self.client = vpc_client.VpcClient(self.__cred, self._region)
        self.req = models.DescribeAddressesRequest()

    def get_all_eip1(self):
        try:
            resp = self.client.DescribeAddresses(self.req)
            return resp.AddressSet
        except Exception as err:
            logging.error(f"腾讯云EIP {self._account_id} {err}")
            return False

    def get_all_eip(self) -> list:
        eip_list = []
        limit = self._limit
        offset = self._offset
        try:
            while True:
                params = {
                    "Offset": offset,
                    "Limit": limit
                }
                self.req.from_json_string(json.dumps(params))
                resp = self.client.DescribeAddresses(self.req)
                if not resp.AddressSet:
                    break

                eip_list.extend(map(self.format_data, resp.AddressSet))
                offset += limit
            return eip_list
        except Exception as err:
            logging.error(f"腾讯云EIP {self._account_id} {err}")
            return []

    def format_data(self, data) -> Dict[str, Any]:
        res: Dict[str, Any] = dict()

        res['instance_id'] = data.AddressId
        res['name'] = data.AddressName
        res['address'] = data.AddressIp
        res['binding_instance_id'] = data.InstanceId
        res['binding_instance_type'] = ''
        res['state'] = get_state_type(data.AddressStatus)
        res['region'] = self._region
        res['bandwidth'] = data.Bandwidth
        res['internet_charge_type'] = get_network_pay_type(data.InternetChargeType)
        res['charge_type'] = ''

        res['create_time'] = data.CreatedTime

        return res

    def sync_cmdb(self, cloud_name: Optional[str] = 'qcloud', resource_type: Optional[str] = 'eip') -> Tuple[
        bool, str]:
        """
        同步CMDB
        """
        all_eip_list: List[list, Any, None] = self.get_all_eip()

        if not all_eip_list:
            return False, "弹性公网IP列表为空"
        # 同步资源
        ret_state, ret_msg = eip_task(account_id=self._account_id, cloud_name=cloud_name, rows=all_eip_list)

        # 标记过期
        # mark_expired(resource_type=resource_type, account_id=self._account_id)
        instance_ids = [eip['instance_id'] for eip in all_eip_list]
        mark_expired_by_sync(cloud_name=cloud_name, account_id=self._account_id, resource_type=resource_type,
                             instance_ids=instance_ids, region=self._region)

        return ret_state, ret_msg
