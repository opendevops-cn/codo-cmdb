#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/1/27 11:02
Desc    : 阿里云SLB
"""

import json
import logging
from typing import *
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.auth.credentials import AccessKeyCredential
from aliyunsdkslb.request.v20140515.DescribeLoadBalancersRequest import DescribeLoadBalancersRequest
from models.models_utils import lb_task, mark_expired, mark_expired_by_sync


def get_run_status(val):
    return {
        "inactive": "已停止",
        "active": "运行中",
        "locked": "已锁定"
    }.get(val, '未知')


def get_endporint_type(val):
    return {
        "internet": "公网",
        "intranet": "内网"
    }.get(val, "未知")


def get_internet_charge_type(val):
    return {
        "paybybandwidth": "带宽计费",
        "paybytraffic": "流量计费"
    }.get(val, "未知")


def get_pay_type(val):
    return {"PayOnDemand": "按量付费", "PrePay": "包年包月"}.get(val, "未知")


class AliyunSLbClient:
    def __init__(self, access_id: str, access_key: str, region: str, account_id: str):
        self.page_number = 1
        self.page_size = 100
        self._access_id = access_id
        self._access_key = access_key
        self._region = region
        self._accountID = account_id
        self.__client = self._create_client()

    def _create_client(self) -> AcsClient:
        credentials = AccessKeyCredential(self._access_id, self._access_key)
        return AcsClient(region_id=self._region, credential=credentials)

    def get_slb_response(self) -> Tuple[bool, str, dict]:
        """
        获取传统型负载均衡
        :return:
        """
        # 定义返回
        ret_state, ret_msg, ret_date = True, "获取Response成功", {}
        try:
            request = DescribeLoadBalancersRequest()
            request.set_accept_format('json')
            request.set_PageNumber(self.page_number)
            request.set_PageSize(self.page_size)
            response = self.__client.do_action_with_exception(request)
            ret_date = json.loads(str(response, encoding="utf8"))
        except Exception as error:
            ret_state, ret_msg, ret_date = True, error, {}
        return ret_state, ret_msg, ret_date

    def get_all_slb(self) -> List[Dict[str, Any]]:
        """
        获取所有的传统负载均衡 SLB
        :return:
        """
        self.page_number = 1
        all_slb_list: List = []
        while True:
            is_success, msg, response = self.get_slb_response()
            if not is_success or not response:
                logging.error(msg)
                break
            if 'LoadBalancers' not in response:
                logging.error(msg)
                break
            self.page_number += 1
            rows = response["LoadBalancers"]["LoadBalancer"]
            if not rows: break
            for row in rows:
                data = self.format_slb_data(row)
                all_slb_list.append(data)
        return all_slb_list

    @staticmethod
    def format_slb_data(row: dict, type: Optional[str] = 'slb') -> Dict[str, Any]:
        """
        处理下需要入库的数据
        :param type:
        :param row: {"ResourceGroupId": "rg-dglv4m7a","AddressIPVersion": "ipv4"...}
        :return:
        """
        # 定义返回
        res: Dict[str, Any] = dict()

        res['type'] = type  # slb or alb
        res['name'] = row.get('LoadBalancerName')
        res['instance_id'] = row.get('LoadBalancerId')
        res['region'] = row.get('RegionId')
        res['zone'] = row.get('MasterZoneId')
        res['status'] = get_run_status(row.get('LoadBalancerStatus'))
        res['dns_name'] = row.get('Address')
        res['endpoint_type'] = get_endporint_type(row.get('AddressType'))
        res['ext_info'] = {
            "vpc_id": row.get("VpcId"),
            "switch_id": row.get("VSwitchId"),
            "create_time": row.get('CreateTime'),
            "class_type": row.get('LoadBalancerSpec'),
            "charge_type": get_pay_type(row.get("PayType")),
            "network_type": row.get('NetworkType'),
            "address_ip_version": row.get('AddressIPVersion'),
            "internet_charge_type": get_internet_charge_type(row.get("InternetChargeType"))
        }
        return res

    def sync_cmdb(self, cloud_name: Optional[str] = 'aliyun', resource_type: Optional[str] = 'lb') -> Tuple[
        bool, str]:
        """
        同步CMDB
        """
        all_slb_list: List[Dict[str, Any]] = self.get_all_slb()
        if not all_slb_list: return False, "SLB列表为空"
        # 同步资源
        ret_state, ret_msg = lb_task(account_id=self._accountID, cloud_name=cloud_name, rows=all_slb_list)
        # 标记过期
        # mark_expired(resource_type=resource_type, account_id=self._accountID)
        instance_ids = [row['instance_id'] for row in all_slb_list]
        mark_expired_by_sync(cloud_name=cloud_name, account_id=self._accountID, resource_type=resource_type,
                             instance_ids=instance_ids, region=self._region)

        return ret_state, ret_msg


if __name__ == '__main__':
    pass
