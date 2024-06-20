# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/4/15
# @Description: 谷歌云虚拟网络

from __future__ import print_function
import logging
from datetime import datetime
from typing import *

from google.oauth2 import service_account
from google.cloud import compute_v1

from models.models_utils import vpc_task, mark_expired


class GCPVPC:
    def __init__(self, project_id: str, account_path: str, region: str,
                 account_id: str):
        self.cloud_name = 'gcp'
        self.page_size = 100  # 分页查询时设置的每页行数。最大值：100 默认值：10
        self._region = region
        self.project_id = project_id
        self._account_id = account_id
        self.__credentials = service_account.Credentials.from_service_account_file(
            account_path)
        self.client = compute_v1.NetworksClient(
            credentials=self.__credentials)

    def get_vpc(self, project: str, network: str):
        """
        获取单个vpc
        """
        request = compute_v1.GetNetworkRequest(network=network, project=project)
        response = self.client.get(request=request)
        return response

    def get_all_vpcs(self):
        """
        获取所有的vpc
        """
        vpcs = []
        try:
            request = compute_v1.ListNetworksRequest()
            request.project = self.project_id
            request.max_results = self.page_size
            # request.page_token = ""
            page_result = self.client.list(request=request)
            for response in page_result:
                vpcs.append(self.handle_data(response))
        except Exception as e:
            logging.error(
                f"谷歌云虚拟网络调用异常 get_all_vpcs： {self._account_id} -- {e}")
        return vpcs

    @staticmethod
    def handle_data(data) -> Dict[str, Any]:
        """
        处理数据
        """
        res: Dict[str, Any] = dict()
        res['instance_id'] = str(data.id)
        res['vpc_name'] = data.name
        res['region'] = ''
        res['create_time'] = datetime.strptime(data.creation_timestamp,
                                               "%Y-%m-%dT%H:%M:%S.%f%z").strftime(
            "%Y-%m-%d %H:%M:%S")
        # res['is_default'] = ''
        res['cidr_block_v4'] = data.I_pv4_range
        res['cidr_block_v6'] = data.internal_ipv6_range
        return res

    def sync_cmdb(self, cloud_name: Optional[str] = 'gcp',
                  resource_type: Optional[str] = 'vpc') -> Tuple[bool, str]:
        """
        同步到DB
        :param cloud_name:
        :param resource_type:
        :return:
        """
        vpcs: Union[List[Dict[str, Any]], List] = self.get_all_vpcs()

        if not vpcs:  return False, "VPC列表为空"
        # 同步资源
        ret_state, ret_msg = vpc_task(account_id=self._account_id,
                                      cloud_name=cloud_name, rows=vpcs)

        # 标记过期
        mark_expired(resource_type=resource_type, account_id=self._account_id)

        return ret_state, ret_msg


if __name__ == '__main__':
    pass
