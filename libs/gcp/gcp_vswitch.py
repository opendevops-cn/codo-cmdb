# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/4/15
# @Description: 谷歌云虚拟子网

from __future__ import print_function
import logging
from datetime import datetime
from typing import *

from google.oauth2 import service_account
from google.cloud import compute_v1

from libs.gcp.gcp_vpc import GCPVpc
from models.models_utils import vswitch_task, mark_expired


class GCPSubnet:
    def __init__(self, project_id: str, account_path: str, region: str,
                 account_id: str):
        self.cloud_name = 'gcp'
        self.page_size = 100  # 分页查询时设置的每页行数。最大值：100 默认值：10
        self._region = region
        self.project_id = project_id
        self._account_id = account_id
        self.account_path = account_path
        self.__credentials = service_account.Credentials.from_service_account_file(
            self.account_path)
        self.client = compute_v1.SubnetworksClient(
            credentials=self.__credentials)

    def get_all_subnets(self):
        """
        获取所有的子网
        """
        subnets = []
        try:
            request = compute_v1.AggregatedListSubnetworksRequest()
            request.project = self.project_id
            request.max_results = self.page_size
            # request.page_token = ""
            page_result = self.client.aggregated_list(request=request)
            for region, response in page_result:
                subnetworks = response.subnetworks
                if not subnetworks:
                    continue
                subnets.extend([self.handle_data(data) for data in subnetworks])
        except Exception as e:
            logging.error(
                f"谷歌云虚拟子网调用异常 get_all_subnets： {self._account_id} -- {e}")
        return subnets

    def get_vpc_by_network(self, network: str):
        """
        获取vpc
        """
        vpc_client = GCPVpc(project_id=self.project_id, region=self._region,
                            account_path=self.account_path,
                            account_id=self._account_id)
        return vpc_client.get_vpc(project=self.project_id, network=network)

    def handle_data(self, data) -> Dict[str, Any]:
        """
        处理数据
        """
        res: Dict[str, Any] = dict()
        stack_type = data.stack_type
        network = data.network.split('/')[-1]
        res['instance_id'] = data.id
        res['name'] = data.name
        res['region'] = data.region.split('/')[-1]
        res['zone'] = ''
        res['address_count'] = ''
        res['route_id'] = ''
        res['create_time'] = datetime.strptime(data.creation_timestamp,
                                               "%Y-%m-%dT%H:%M:%S.%f%z").strftime(
            "%Y-%m-%d %H:%M:%S")
        # res['is_default'] = ''
        res['cidr_block_v4'] = data.ip_cidr_range
        res['cidr_block_v6'] = data.external_ipv6_prefix if (
                stack_type == 'IPV4_IPV6') else ''
        res['description'] = data.description
        try:
            vpc_instance = self.get_vpc_by_network(network=network)
            res['vpc_id'] = vpc_instance.id
            res['vpc_name'] = vpc_instance.name
        except Exception as e:
            logging.error(
                f'调用谷歌云虚拟子网获取vpc异常. get_vpc_by_network: {self._account_id} -- {e}')
        return res

    def sync_cmdb(self, cloud_name: Optional[str] = 'gcp',
                  resource_type: Optional[str] = 'vswitch') -> Tuple[
        bool, str]:
        """
        同步CMDB
        """
        subnets: List[dict] = self.get_all_subnets()

        if not subnets:
            return False, "虚拟子网列表为空"
        # 同步资源
        ret_state, ret_msg = vswitch_task(account_id=self._account_id,
                                          cloud_name=cloud_name, rows=subnets)

        # 标记过期
        mark_expired(resource_type=resource_type, account_id=self._account_id)

        return ret_state, ret_msg


if __name__ == '__main__':
    pass