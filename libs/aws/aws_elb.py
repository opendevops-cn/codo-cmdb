#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/1/27 11:02
Desc    : AWS ELB
"""

import logging
import boto3
from typing import *
from models.models_utils import lb_task, mark_expired


def get_lb_type(val: str):
    return {"network": "nlb", "application": "alb", "gateway": "gateway"}.get(val, "未知")


def get_run_status(val: str):
    return {"active": "运行中", "provisioning": "初始状态", "failed": "设置失败"}.get(val, val)


def get_endporint_type(val: str):
    return {"internet-facing": "公网", "internal": "内网"}.get(val, "未知")


def get_instance_id(arn: str):
    """
    因为AWS没有直接返回InstanceID，通过ARN取最后的ID
    :param arn:
    :return:
    """
    return arn.split('/')[-1]


class AwsLbClient:
    def __init__(self, access_id: str, access_key: str, region: str, account_id: str):
        self._access_id = access_id
        self._access_key = access_key
        self._region = region
        self._accountID = account_id
        self.__client = self.create_client()

    def create_client(self) -> Union[None, boto3.client]:
        try:
            client = boto3.client('elbv2', region_name=self._region, aws_access_key_id=self._access_id,
                                  aws_secret_access_key=self._access_key)
        except Exception as err:
            logging.error(f'aws elbv2 boto3 create client error:{err}')
            client = None
        return client

    def get_all_elb(self) -> List[dict]:
        """
        Docs:https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/elbv2.html
        :return:
        """
        # ret_state, ret_msg, ret_data = True, '获取成功', []

        try:
            response = self.__client.describe_load_balancers()
            elb_clusters = response.get('LoadBalancers')
            if not elb_clusters:
                logging.info("AWS ELB资产为空")
                return []
            all_elb_list = list(map(self._format_data, elb_clusters))
        except Exception as err:
            logging.info(f'get aws elb error, {err}')
            return []
        return all_elb_list

    def _format_data(self, row: dict) -> Dict[str, Any]:
        res: Dict[str, Any] = {}
        res['type'] = get_lb_type(row.get('Type'))
        res['name'] = row.get('LoadBalancerName')
        res['instance_id'] = get_instance_id(row.get('LoadBalancerArn'))
        res['create_time'] = row.get('CreatedTime')
        res['region'] = self._region
        res['status'] = get_run_status(row['State']['Code'])
        res['dns_name'] = row.get('DNSName')
        res['endpoint_type'] = get_endporint_type(row.get('Scheme'))
        res['ext_info'] = {
            'zone': row.get("AvailabilityZones"),
            'address_type': row.get('IpAddressType')
        }
        return res

    def sync_cmdb(self, cloud_name: Optional[str] = 'aws', resource_type: Optional[str] = 'lb') -> Tuple[
        bool, str]:
        # 获取数据
        all_elb_list: List[dict] = self.get_all_elb()
        if not all_elb_list: return False, "ELB列表为空"

        # 同步资源
        ret_state, ret_msg = lb_task(account_id=self._accountID, cloud_name=cloud_name, rows=all_elb_list)

        # 标记过期
        mark_expired(resource_type=resource_type, account_id=self._accountID)

        return ret_state, ret_msg


if __name__ == '__main__':
    pass
