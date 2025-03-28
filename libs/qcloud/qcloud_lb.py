#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date   :  2023/1/27 11:02
Desc   :  腾讯云 CLB
"""

import json
from typing import *
import logging
from tencentcloud.common import credential
from tencentcloud.clb.v20180317 import clb_client, models
from models.models_utils import lb_task, mark_expired, mark_expired_by_sync


def get_run_status(val):
    return {1: "运行中", 0: "创建中"}.get(val, '未知')


def get_endpoint_type(val):
    return {"OPEN": "公网", "INTERNAL": "内网"}.get(val, "未知")


def get_pay_type(val):
    return {"PREPAID": "包年包月", "POSTPAID_BY_HOUR": "按量计费"}.get(val, val)


class QCloudLB:
    def __init__(self, access_id: str, access_key: str, region: str, account_id: str):
        self._offset = 0  # 偏移量,这里拼接的时候必须是字符串
        self._limit = 100  # 官方默认是20，大于100 需要设置偏移量再次请求：offset=100,offset={机器总数}
        self._access_id = access_id
        self._access_key = access_key
        self._region = region
        self._account_id = account_id

        self.region = region
        self.__cred = credential.Credential(self._access_id, access_key)
        self.client = clb_client.ClbClient(self.__cred, self.region)
        self.req = models.DescribeLoadBalancersRequest()

    def format_lb_data(self, row, lb_type: Optional[str] = 'clb') -> Dict[str, Any]:
        # 定义返回
        try:
            zone = row.MasterZone.Zone
        except Exception as err:
            zone = ''
        lb_vips = row.LoadBalancerVips
        try:
            lb_vip = lb_vips[0]
        except Exception as err:
            lb_vip = ''

        dns_name = ''
        try:
            if row.LoadBalancerDomain:
                dns_name = row.LoadBalancerDomain
            elif row.Domain:
                dns_name = row.Domain
        except Exception as err:
            logging.error(err)

        res: Dict[str, Any] = dict()

        res['type'] = lb_type  # slb or alb
        res['name'] = row.LoadBalancerName
        res['instance_id'] = row.LoadBalancerId
        res['create_time'] = row.CreateTime
        res['lb_vip'] = lb_vip  # LoadBalancerVips
        res['region'] = self._region
        res['zone'] = zone
        res['status'] = get_run_status(row.Status)
        res['dns_name'] = dns_name
        res['endpoint_type'] = get_endpoint_type(row.LoadBalancerType)
        res['ext_info'] = {
            "vpc_id": row.VpcId,
            "lb_vips": lb_vips,
            "ip_version": row.AddressIPVersion,
            "charge_type": get_pay_type(row.ChargeType)
        }
        return res

    def get_lb_response(self, offset) -> list:
        try:
            params = {
                "Offset": offset,
                "Limit": self._limit
            }
            self.req.from_json_string(json.dumps(params))

            # 返回的resp是一个DescribeLoadBalancersResponse的实例，与请求对象对应
            resp = self.client.DescribeLoadBalancers(self.req)
            return resp.LoadBalancerSet
        except Exception as err:
            logging.error(err)
            return []

    def get_all_slb(self):
        offset = self._offset
        all_lb_list: List = []
        while True:
            rows = self.get_lb_response(offset)
            if not rows: break
            offset += self._limit

            if not rows: break
            for row in rows:
                data = self.format_lb_data(row)
                all_lb_list.append(data)
            # yield all_lb_list
        return all_lb_list

    def sync_cmdb(self, cloud_name: Optional[str] = 'qcloud', resource_type: Optional[str] = 'lb') -> \
            Tuple[bool, str]:
        """
        同步CMDB
        """
        all_alb_list: List[list, Any, None] = self.get_all_slb()
        if not all_alb_list:  return False, "CLB列表为空"
        # 同步资源
        ret_state, ret_msg = lb_task(account_id=self._account_id, cloud_name=cloud_name, rows=all_alb_list)

        # 标记过期
        # mark_expired(resource_type=resource_type, account_id=self._account_id)
        instance_ids = [lb['instance_id'] for lb in all_alb_list]
        mark_expired_by_sync(cloud_name=cloud_name, account_id=self._account_id, resource_type=resource_type,
                             instance_ids=instance_ids, region=self._region)

        return ret_state, ret_msg
