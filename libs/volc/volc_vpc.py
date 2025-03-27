# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/4/1
# @Description: 火山云虚拟局域网

from __future__ import print_function
import logging
from typing import *

import volcenginesdkcore
from volcenginesdkcore.rest import ApiException
from volcenginesdkvpc import VPCApi, DescribeVpcsRequest, DescribeVpcAttributesRequest

from models.models_utils import vpc_task, mark_expired, mark_expired_by_sync

VPCStatusMapping = {
    "Creating": "创建中",
    "Pending": "配置中",
    "Available": "可用"
}

class VolCVPC:
    def __init__(self, access_id: str, access_key: str, region: str, account_id: str):
        self.cloud_name = 'volc'
        self.page_number = 1  # 实例状态列表的页码。起始值：1 默认值：1
        self.page_size = 100  # 分页查询时设置的每页行数。最大值：100 默认值：10
        self._region = region
        self._account_id = account_id
        self.api_instance = self.__initialize_api_instance(access_id, access_key, region)

    @staticmethod
    def __initialize_api_instance(access_id: str, access_key: str, region: str):
        """
        初始化api实例对象
        https://api.volcengine.com/api-sdk/view?serviceCode=vpc&version=2020-04-01&language=Python
        :param access_id:
        :param access_key:
        :param region:
        :return:
        """
        configuration = volcenginesdkcore.Configuration()
        configuration.ak = access_id
        configuration.sk = access_key
        configuration.region = region
        # configuration.client_side_validation = False
        # set default configuration
        volcenginesdkcore.Configuration.set_default(configuration)
        return VPCApi()

    def get_describe_vpc(self):
        """
        查询vpc实例的基本信息
        Doc: https://api.volcengine.com/api-docs/view?serviceCode=vpc&version=2020-04-01&action=DescribeVpcs
        :return:
        """
        try:
            instances_request = DescribeVpcsRequest(page_size=self.page_size, page_number=self.page_number)
            resp = self.api_instance.describe_vpcs(instances_request)
            return resp
        except ApiException as e:
            logging.error(f"火山云调用虚拟网络列表异常 get_describe_vpc: {self._account_id} -- {e}")

            return None

    def get_describe_vpc_detail(self, vpc_id: str):
        """
        查询vpc详细信息
        Doc: https://api.volcengine.com/api-docs/view?serviceCode=vpc&version=2020-04-01&action=DescribeVpcAttributes
        :return:
        """
        try:
            instances_request = DescribeVpcAttributesRequest(vpc_id=vpc_id)
            resp = self.api_instance.describe_vpc_attributes(instances_request)
            return resp
        except ApiException as e:
            logging.error(f"火山云调用虚拟网络详情异常 get_describe_vpc_detail: {self._account_id} -- {e}")

            return None


    def handle_data(self, data) -> Dict[str, Any]:
        """
        数据处理
        :param data:
        :return:
        """
        res: Dict[str, Any] = dict()
        res['instance_id'] = data.vpc_id
        res['vpc_name'] = data.vpc_name
        res['region'] = self._region
        res['create_time'] = data.creation_time
        res['is_default'] = data.is_default
        res['cidr_block_v4'] = data.cidr_block

        detail = self.get_describe_vpc_detail(vpc_id=data.vpc_id)
        if detail is not None:
            res['cidr_block_v6'] = detail.ipv6_cidr_block
            res['ext_info'] = {
                "subnet_ids": detail.subnet_ids,
                "status": VPCStatusMapping.get(detail.status, "Unknown"),
                "network_acl_num": detail.network_acl_num,
                "route_table_ids": detail.route_table_ids,
                "security_group_ids": detail.security_group_ids
            }

        return res

    def get_all_vpcs(self) -> Union[List[Dict[str, Any]], List]:
        """
        分页查询所有vpc
        :return:
        """
        vpcs = []
        try:
            while True:
                data = self.get_describe_vpc()
                if data is None:
                    break

                instances = data.vpcs
                if not instances:
                    break
                vpcs.extend([self.handle_data(data) for data in instances])
                if data.total_count < self.page_size:
                    break
                self.page_number += 1
        except Exception as e:
            logging.error(f"火山云虚拟网络调用异常 get_all_vpcs： {self._account_id} -- {e}")
        return vpcs


    def sync_cmdb(self, cloud_name: Optional[str] = 'volc', resource_type: Optional[str] = 'vpc') -> Tuple[bool, str]:
        """
        同步到DB
        :param cloud_name:
        :param resource_type:
        :return:
        """
        vpcs: Union[List[Dict[str, Any]], List] = self.get_all_vpcs()

        if not vpcs:  return False, "VPC列表为空"
        # 同步资源
        ret_state, ret_msg = vpc_task(account_id=self._account_id, cloud_name=cloud_name, rows=vpcs)

        # 标记过期
        # mark_expired(resource_type=resource_type, account_id=self._account_id)
        instance_ids = [vpc['instance_id'] for vpc in vpcs]
        mark_expired_by_sync(cloud_name=cloud_name, account_id=self._account_id, resource_type=resource_type,
                             instance_ids=instance_ids, region=self._region)

        return ret_state, ret_msg




if __name__ == '__main__':
    pass
