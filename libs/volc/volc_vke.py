# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2025/3/10
# @Description: 火山云集群

from __future__ import print_function

import logging
from typing import List, Dict, Union, Optional, Tuple

import volcenginesdkcore
from volcenginesdkcore.rest import ApiException
from volcenginesdkvke import VKEApi, ListClustersRequest

from models.models_utils import cluster_task, mark_expired, mark_expired_by_sync


def get_cluster_status(val):
    status_map = {
        "Creating": "创建中",
        'Running': '运行中',
        'Updating': '更新中',
        "Deleting": "删除中",
        'Stopped': '欠费关停',
        "Failed": "异常"
    }
    return status_map.get(val, '未知')


class VolcVKE:
    def __init__(self, access_id: str, access_key: str, region: str, account_id: str) -> None:
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
        https://api.volcengine.com/api-sdk/view?serviceCode=clb&version=2020-04-01&language=Python
        :param access_id:
        :param access_key:
        :param region:
        :return:
        """
        configuration = volcenginesdkcore.Configuration()
        configuration.ak = access_id
        configuration.sk = access_key
        configuration.region = region
        return VKEApi(volcenginesdkcore.ApiClient(configuration))

    def get_cluster(self):
        """
        获取集群
        """
        request = ListClustersRequest(page_number=self.page_number, page_size=self.page_size)
        try:
            response = self.api_instance.list_clusters(request)
            return response
        except ApiException as e:
            logging.error(f"火山云集群调用异常 get_cluster： {self._account_id} -- {e}")
            return None

    def process_cluster(self, data: Dict[str, str]) -> Dict[str, str]:
        """
        处理集群数据
        """
        tags = [{'key': tag.key, 'type': tag.type, 'value': tag.value} for tag in data.tags]
        return {
            "instance_id": data.id,
            "name": data.name,
            "state": get_cluster_status(data.status.phase),
            "version": data.kubernetes_version,
            "region": self._region,
            "vpc_id": data.cluster_config.vpc_id,
            "update_time": data.update_time,
            'tags': tags,
            'cidr_block_v4': data.services_config.service_cidrsv4,
            'inner_ip': data.cluster_config.api_server_endpoints.private_ip.ipv4,
            'outer_ip': data.cluster_config.api_server_endpoints.public_ip.ipv4,
            'total_node': data.node_statistics.total_count,
            'total_running_node': data.node_statistics.running_count,
            'description': data.description,
            'cluster_type': '标准集群',
        }

    def get_all_clusters(self) -> Union[List[Dict[str, str]], None]:
        """
        分页查询所有集群实例并处理数据
        """
        clusters_list = []
        while True:
            response = self.get_cluster()
            if response is None:
                break
            clusters_list.extend([self.process_cluster(data) for data in response.items])
            if response.total_count < self.page_size:
                break
            self.page_number += 1
        return clusters_list

    def sync_cmdb(self, cloud_name: Optional[str] = 'volc', resource_type: Optional[str] = 'cluster') -> Tuple[
        bool, str]:
        """
        资产信息更新到DB
        :return:
        """
        all_cluster_list: List[dict] = self.get_all_clusters()
        if not all_cluster_list:
            return False, "集群列表为空"
        # 更新资源
        ret_state, ret_msg = cluster_task(account_id=self._account_id,
                                          cloud_name=cloud_name,
                                          rows=all_cluster_list)
        # 标记过期
        # mark_expired(resource_type=resource_type, account_id=self._account_id)
        instance_ids = [cluster['instance_id'] for cluster in all_cluster_list]
        mark_expired_by_sync(cloud_name=cloud_name, account_id=self._account_id, resource_type=resource_type,
                             instance_ids=instance_ids, region=self._region)
        return ret_state, ret_msg


if __name__ == '__main__':
    pass
