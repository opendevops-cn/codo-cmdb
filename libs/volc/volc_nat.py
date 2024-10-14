#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# @File    :   volc_nat.py
# @Time    :   2024/10/12 10:30:42
# @Author  :   DongdongLiu
# @Version :   1.0
# @Desc    :   火山云NAT网关实例


import json
import logging
from typing import *

import volcenginesdkcore
import volcenginesdknatgateway
from volcenginesdkcore.rest import ApiException
from volcenginesdkecs import ECSApi, DescribeInstancesRequest
from volcenginesdknatgateway import DescribeNatGatewaysRequest, DescribeNatGatewayAttributesRequest, DescribeNatGatewaysResponse, \
    DescribeNatGatewayAttributesResponse

from models.models_utils import nat_task, mark_expired
from libs.volc.volc_vpc import VolCVPC
from typing import Optional, List, Dict


def get_run_type(val):
    run_map = {
        "Creating": "创建中",
        "Pending": "操作中",
        "Deleting": "删除中",
        "Available": "可用"
    }
    return run_map.get(val, '未知')

def get_spec_type(val):
    return {
        "Small": "小型",
        "Medium": "中型",
        "Large": "大型",
        "Extra_Large_1": "超大型-1",
        "Extra_Large_2": "超大型-2"
    }.get(val, '未知')


def get_pay_type(val):
    pay_map = {
        1: "包年包月",
        2: "按量计费-按规格计费",
        3: "按量计费-按使用量计费",
    }
    return pay_map.get(val, '未知')

def get_network_type(val):
    return {
        "internet": "公网",
        "intranet": "私网"
    }.get(val, '未知')


class VolNAT:
    def __init__(self, access_id: str, access_key: str, region: str,
                 account_id: str):
        self.cloud_name = 'volc'
        self.page_number = 1  # 实例状态列表的页码。起始值：1 默认值：1
        self.page_size = 100  # 分页查询时设置的每页行数。最大值：100 默认值：10
        self._region = region
        self._account_id = account_id
        self._access_id = access_id
        self._access_key = access_key
        self.api_instance = self.initialize_api_instance(access_id, access_key,
                                                         region)

    @staticmethod
    def initialize_api_instance(access_id, access_key, region):
        configuration = volcenginesdkcore.Configuration()
        configuration.ak = access_id
        configuration.sk = access_key
        configuration.region = region
        volcenginesdkcore.Configuration.set_default(configuration)
        return volcenginesdknatgateway.NATGATEWAYApi()

    def describe_nat_gateways(self) -> Optional[DescribeNatGatewaysResponse]:
        """ 查询NAT网关实例列表
        https://api.volcengine.com/api-docs/view?serviceCode=natgateway&version=2020-04-01&action=DescribeNatGateways
        """
        try:
            instances_request = DescribeNatGatewaysRequest()
            instances_request.page_size = self.page_size
            instances_request.page_number = self.page_number
            resp = self.api_instance.describe_nat_gateways(instances_request)
            return resp
        except ApiException as e:
            logging.error(f"火山云NatGateway调用异常.describe_nat_gateways: {self._account_id} -- {e}")
            return None

    def describe_nat_gateway_detail(self, nat_gateway_id: str) -> Optional[DescribeNatGatewayAttributesResponse]:
        """
        查询nat详细信息
        https://api.volcengine.com/api-docs/view?serviceCode=natgateway&version=2020-04-01&action=DescribeNatGatewayAttributes
        :return:
        """
        try:
            instance_request = DescribeNatGatewayAttributesRequest(nat_gateway_id==nat_gateway_id)
            resp = self.api_instance.describe_nat_gateway_attributes(instance_request)
            return resp
        except ApiException as e:
            logging.error(f"火山云NatGateway调用异常.get_describe_nat_gateway_detail: {self._account_id} -- {e}")
            return None

    def get_all_nat_gateways(self) -> List[Dict[str, str]]:
        """ 
        分页查询所有NAT网关实例并处理数据
        """
        nat_gateways_list = []
        while True:
            response = self.describe_nat_gateways()
            if response is None:
                break
            nat_gateways_list.extend([self.process_nat_gateway(data) for data in response.nat_gateways])
            if response.total_count < self.page_size:
                break
            self.page_number += 1

        return nat_gateways_list

    def process_nat_gateway(self, data) -> Dict[str, str]:
        """
        处理数据
        :param data:
        :return:
        """
        # 定义返回
        res: Dict[str, Any] = dict()
        try:
            network_interface_id = data.network_interface_id
            res['instance_id'] = data.nat_gateway_id
            res['vpc_id'] = data.vpc_id
            res['state'] = get_run_type(data.status)
            res['name'] = data.nat_gateway_name
            res['network_type'] = get_network_type(data.network_type)
            res['network_interface_id'] = network_interface_id
            res['charge_type'] = get_pay_type(data.billing_type)
            res['project_name'] = data.project_name
            res['spec'] = get_spec_type(data.spec)

            # 内外网IP,可能有多个
            eip_addresses = data.eip_addresses
            if isinstance(eip_addresses, list):
                outer_ip = [eip.eip_address for eip in eip_addresses]
            res['outer_ip'] = outer_ip
            res['create_time'] = data.creation_time
            res['expired_time'] = data.expired_time
            res['region'] = self._region
            res['zone'] = data.zone_id
            res['description'] = data.description
            res['subnet_id'] = data.subnet_id

        except Exception as err:
            logging.error(f"火山云 process_nat_gateway err. account_id: {self._account_id},  err:{err}")

        return res

    def sync_cmdb(self, cloud_name: Optional[str] = 'volc',
                  resource_type: Optional[str] = 'nat') -> Tuple[
        bool, str]:
        """
        资产信息更新到DB
        :return:
        """
        all_nat_gateway_list: List[dict] = self.get_all_nat_gateways()
        if not all_nat_gateway_list:
            return False, "Nat列表为空"
        # 更新资源
        ret_state, ret_msg = nat_task(account_id=self._account_id, 
                                      cloud_name=cloud_name,
                                      rows=all_nat_gateway_list)
        # 标记过期
        mark_expired(resource_type=resource_type, account_id=self._account_id)

        return ret_state, ret_msg


if __name__ == '__main__':
    pass
