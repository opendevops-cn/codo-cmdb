# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2025/3/11
# @Description: 腾讯云k8s集群


from __future__ import print_function

import logging

from tencentcloud.common import credential
from tencentcloud.tke.v20180525 import tke_client, models

from models.models_utils import cluster_task, mark_expired


class QcloudTKE:
    """
    腾讯云k8s集群
    """

    def __init__(self, access_id: str, access_key: str, region: str, account_id: str) -> None:
        self._offset = 0  # 偏移量,这里拼接的时候必须是字符串
        self._limit = 100  # 官方默认是20，大于100 需要设置偏移量再次请求：offset=100,offset={机器总数}
        self._access_id = access_id
        self._access_key = access_key
        self._region = region
        self._account_id = account_id

        self.region = region
        self.__cred = credential.Credential(self._access_id, access_key)
        self.client = tke_client.TkeClient(self.__cred, self.region)
        self.req = models.DescribeEKSClustersRequest()

    def describe_tke_instance(self, offset: int):
        """获取tke实例
        Args:
            offset: 偏移量
        Return:
            models.DescribeDBInstancesResponse: tke实例响应
        """
        try:
            req = models.DescribeEKSClustersRequest()
            req.Limit = self._limit
            req.Offset = offset
            response = self.client.DescribeEKSClusters(req)
            return response
        except Exception as e:
            logging.error(f"获取腾讯云tke实例失败: {e}")
            return

    def describe_cluster_instance(self, offset: int):
        """获取标准集群实例
        Args:
            offset: 偏移量
        Return:
            models.DescribeDBInstancesResponse: tke实例响应
        """
        try:
            req = models.DescribeClustersRequest()
            req.Limit = self._limit
            req.Offset = offset
            response = self.client.DescribeClusters(req)
            return response
        except Exception as e:
            logging.error(f"获取腾讯云标准集群实例失败: {e}")
            return

    def get_all_cluster_instance(self):
        all_cluster_instance = []
        offset = self._offset
        try:
            while True:
                response = self.describe_cluster_instance(offset)
                if not response:
                    break
                all_cluster_instance.extend([self.process_cluster(data) for data in response.Clusters])
                if response.TotalCount <= self._limit:
                    break
                offset += self._limit
            return all_cluster_instance
        except Exception as e:
            logging.error(f"获取腾讯云标准集群实例失败: {e}")
            return []

    def describe_tke_nodes(self, cluster_id: str):
        """获取tke节点
        Args:
            cluster_id: 集群id
        Return:
            models.DescribeEKSClusterNodeResponse: tke节点响应
        """
        try:
            req = models.DescribeClusterStatusRequest()
            req.ClusterId = cluster_id
            response = self.client.DescribeClusterStatus(req)
            return response
        except Exception as e:
            logging.error(f"获取腾讯云tke节点失败: {e}")
            return

    def describe_tke_network_settings(self, cluster_id: str):
        """获取tke网络设置
        Args:
            cluster_id: 集群id
        Return:
            models.DescribeClusterEndpointVipResponse: tke网络设置响应
        """
        try:
            req = models.DescribeClustersRequest()
            req.ClusterId = cluster_id
            response = self.client.DescribeClusters(req)
            return response
        except Exception as e:
            logging.error(f"获取腾讯云tke网络设置失败: {e}")
            return

    def get_all_tke_instance(self):
        all_tke_instance = []
        offset = self._offset
        try:
            while True:
                response = self.describe_tke_instance(offset)
                if not response:
                    break
                all_tke_instance.extend([self.process_tke(data) for data in response.Clusters])
                if response.TotalCount <= self._limit:
                    break
                offset += self._limit
            return all_tke_instance
        except Exception as e:
            logging.error(f"获取腾讯云tke实例失败: {e}")
            return []

    @staticmethod
    def get_tke_status(val: str) -> str:
        """
        获取集群状态
        :return:
        """
        status_mapping = {
            "Running": "运行中",
            "Initializing ": "初始化中",
            "Failed": "异常",
            "Idling": "空闲中",
            "Activating": "激活中",
            "Terminating": "删除中",
        }
        return status_mapping.get(val, '未知')

    @staticmethod
    def get_cluster_status(val: str) -> str:
        """
        获取集群状态
        :return:
        """
        """获取集群状态描述
        Args:
            status: 状态代码
        Return:
            str: 状态描述
        """
        return {
            "Trading": "集群开通中",
            "Creating": "创建中",
            "Running": "运行中",
            "Deleting": "删除中",
            "Idling": "闲置中",
            "Recovering": "唤醒中",
            "Scaling": "规模调整中",
            "Upgrading": "升级中",
            "WaittingForConnect": "等待注册",
            "Isolated": "欠费隔离中",
            "Pause": "集群升级暂停",
            "NodeUpgrading": "节点升级中",
            "RuntimeUpgrading": "节点运行时升级中",
            "MasterScaling": "Master扩缩容中",
            "ClusterLevelUpgrading": "调整规格中",
            "ResourceIsolate": "隔离中",
            "ResourceIsolated": "已隔离",
            "ResourceReverse": "冲正中",
            "Abnormal": "异常"
        }.get(val, "未知")

    def process_cluster(self, data) -> dict:
        """
        处理标准集群实例
        Args:
            data: 标准集群实例数据
        Returns:
            dict: 处理后的数据
        """
        tags = self.process_tags(data)
        return {
            "instance_id": data.ClusterId,
            "name": data.ClusterName,
            "state": self.get_cluster_status(data.ClusterStatus),
            "version": data.ClusterVersion,
            "region": self._region,
            "vpc_id": data.ClusterNetworkSettings.VpcId,
            'cidr_block_v4': data.ClusterNetworkSettings.ServiceCIDR,
            'total_node': data.ClusterNodeNum,
            'total_running_node': 0,
            'tags': tags,
            'description': data.ClusterDescription,
            # 'zone': data.Zone
            'cluster_type': '标准集群',
        }

    @staticmethod
    def process_tags(data: dict) -> list:
        tags = []
        try:
            if hasattr(data, 'TagSpecification'):
                tags = [
                    {
                        "key": tag.Key,
                        "value": tag.Value
                    }
                    for spec in data.TagSpecification
                    for tag in spec.Tags
                ]
        except Exception as e:
            logging.error(f"获取标签失败: {e}")
        return tags

    def process_tke(self, data) -> dict:
        """
        处理tke实例
        Args:
            data: tke实例数据
        Returns:
            dict: 处理后的数据
        """

        tags = self.process_tags(data)
        return {
            "instance_id": data.ClusterId,
            "name": data.ClusterName,
            "state": self.get_tke_status(data.Status),
            "version": data.K8SVersion,
            "region": self._region,
            "vpc_id": data.VpcId,
            'tags': tags,
            'cidr_block_v4': '',
            'inner_ip': '',
            'outer_ip': '',
            'total_node': 0,
            'total_running_node': 0,
            'description': data.ClusterDesc,
            'cluster_type': 'Serverless集群',
        }

    def sync_cmdb(self, cloud_name: str = 'qcloud', resource_type: str = 'cluster'):
        """
        同步cmdb
        Args:
            cloud_name: 云商名称
            resource_type: 资源类型
        Returns:
            Tuple[bool, str]: 同步结果
        """
        try:
            tke_list = self.get_all_tke_instance()
            cluster_list = self.get_all_cluster_instance()
            tke_list.extend(cluster_list)
            if not tke_list:
                return False, '腾讯云tke集群为空'
            # 更新资源
            ret_state, ret_msg = cluster_task(account_id=self._account_id, cloud_name=cloud_name, rows=tke_list)
            # 标记过期
            mark_expired(resource_type=resource_type, account_id=self._account_id)
            return ret_state, ret_msg
        except Exception as e:
            logging.error(f"同步腾讯云tke集群失败: {e}")
            return False, '同步失败'


if __name__ == '__main__':
    pass
