# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/4/2
# @Description: 火山云虚拟子网

from __future__ import print_function
import logging
from typing import *

import volcenginesdkcore
from volcenginesdkcore.rest import ApiException
from volcenginesdkvpc import VPCApi, DescribeSubnetsRequest

from libs.volc.volc_vpc import VolCVPC
from models.models_utils import vswitch_task, mark_expired, mark_expired_by_sync



class VolCSubnet(VolCVPC):
    def get_describe_subnets(self):
        """
        查询子网列表
        https://api.volcengine.com/api-docs/view?serviceCode=vpc&version=2020-04-01&action=DescribeSubnets
        :return:
        """
        try:
            instances_request = DescribeSubnetsRequest(page_number=self.page_number, page_size=self.page_size)
            resp = self.api_instance.describe_subnets(instances_request)
            return resp
        except ApiException as e:
            logging.error(f"火山云虚拟子网列表调用异常 get_describe_subnets: {self._account_id} -- {e}")

            return None

    def handle_data(self, data) -> Dict[str, Any]:
        """
        数据处理
        :param data:
        :return:
        """
        res: Dict[str, Any] = dict()
        res['instance_id'] = data.subnet_id
        res['name'] = data.subnet_name
        res['vpc_id'] = data.vpc_id
        res['region'] = self._region
        res['zone'] = data.zone_id
        res['address_count'] = data.available_ip_address_count
        res['route_id'] = data.route_table.route_table_id
        res['create_time'] = data.creation_time
        res['is_default'] = data.is_default
        res['cidr_block_v4'] = data.cidr_block
        res['cidr_block_v6'] = data.ipv6_cidr_block
        res['description'] = data.description

        return res

    def get_all_subnets(self) -> list:
        subnets = []
        try:
            while True:
                data = self.get_describe_subnets()
                instances = data.subnets
                if not instances:
                    break
                subnets.extend([self.handle_data(data) for data in instances])
                if data.total_count < self.page_size:
                    break
                self.page_number += 1
        except Exception as e:
            logging.error(f"火山云虚拟子网调用异常 get_all_subnets: {self._account_id} -- {e}")
        return subnets

    def sync_cmdb(self, cloud_name: Optional[str] = 'volc', resource_type: Optional[str] = 'vswitch') -> Tuple[
        bool, str]:
        """
        同步CMDB
        """
        subnets: List[dict] = self.get_all_subnets()

        if not subnets:
            return False, "虚拟子网列表为空"
        # 同步资源
        ret_state, ret_msg = vswitch_task(account_id=self._account_id, cloud_name=cloud_name, rows=subnets)

        # 标记过期
        # mark_expired(resource_type=resource_type, account_id=self._account_id)
        instance_ids = [vswitch['instance_id'] for vswitch in subnets]
        mark_expired_by_sync(cloud_name=cloud_name, account_id=self._account_id, resource_type=resource_type,
                             instance_ids=instance_ids)

        return ret_state, ret_msg


if __name__ == '__main__':
    pass