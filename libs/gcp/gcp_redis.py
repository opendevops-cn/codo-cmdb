# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/4/7
# @Description: 谷歌云redis自动发现

from typing import *
import logging

from google.oauth2 import service_account
from google.cloud import redis_v1, compute_v1

from models.models_utils import redis_task, mark_expired

StateMapping = {
    "CREATING": "创建中",
    "DELETING": "删除中",
    "FAILING_OVER": "故障转移中",
    "IMPORTING": "导入中",
    "MAINTENANCE": "维护中",
    "READY": "运行中",
    "REPAIRING": "删除中",
    "STATE_UNSPECIFIED": "未设置",
    "UPDATING": "更新中",
}

# https://cloud.google.com/memorystore/docs/redis/reference/rest/v1/projects.locations.instances?hl=zh-cn#Instance
TierMapping = {
    "TIER_UNSPECIFIED": "未设置",
    "BASIC": "基本版",
    "STANDARD_HA": "标准版"
}

class GCPRedis:

    def __init__(self, project_id: str, account_path: str, region: str,
                 account_id: str):
        self.cloud_name = 'gcp'
        self.page_size = 100  # 分页查询时设置的每页行数
        self._region = region
        self.project_id = project_id
        self._account_id = account_id
        self.account_path = account_path
        self.__credentials = service_account.Credentials.from_service_account_file(
            account_path)
        self.client = redis_v1.CloudRedisClient(credentials=self.__credentials)

    def list_instances(self) -> List[dict]:
        """
        查询redis实例信息
        Doc: https://cloud.google.com/memorystore/docs/redis/reference/rest/v1/projects.locations.instances/list?hl=zh-cn
        :return:
        """
        # Initialize request argument(s)
        request = redis_v1.ListInstancesRequest()
        request.parent = f'projects/{self.project_id}/locations/-'
        request.page_size = self.page_size
        # request.page_token = ''

        try:
            # Make the request
            page_result = self.client.list_instances(request=request)
            redis_list = list()
            # Handle the response
            for response in page_result:
                redis_list.append(self.handle_data(response))
            return redis_list
        except Exception as err:
            logging.error(
                f"谷歌云调用Redis异常 list_instances {self._account_id} {err}")
            return []

    def get_vpc_by_network(self, network: str):
        """
        获取vpc
        """
        client = compute_v1.NetworksClient(
            credentials=self.__credentials)
        request = compute_v1.GetNetworkRequest(network=network, project=self.project_id)
        response = client.get(request=request)
        return response

    def get_instance_details(self, name: str):
        request = redis_v1.GetInstanceRequest()
        request.name = name
        result = self.client.get_instance(request=request)
        return result

    def handle_data(self, data) -> Dict[str, Any]:
        res: Dict[str, Any] = dict()
        res['instance_id'] = data.display_name
        network = data.authorized_network.split('/')[-1]
        res['vswitch_id'] = ''
        res['create_time'] = data.create_time.strftime("%Y-%m-%d %H:%M:%S")
        res['charge_type'] = ''
        res['region'] = self._region
        res['zone'] = data.location_id
        res['qps'] = ''
        res['name'] = data.display_name
        res['instance_class'] = f'{data.memory_size_gb * 1024}MB'
        res['instance_arch'] = TierMapping.get(data.tier.name, "未知")
        res['instance_type'] = 'Redis'
        res['instance_version'] = '.'.join(data.redis_version.split('_')[1::])
        res['state'] = StateMapping.get(data.state.name, '未知')
        res['network_type'] = '专有网络'
        res['instance_address'] = {
            "items": [
                {
                    "type": "private",
                    "ip": data.host,
                    "domain": "",
                    "port": str(data.port)
                },
                {
                    "type": "public",
                    "ip": '',
                    "domain": "",
                    "port": ''
                }
            ]
        }
        try:
            vpc_instance = self.get_vpc_by_network(network=network)
            res['vpc_id'] = str(vpc_instance.id)
        except Exception as e:
            logging.error(
                f'调用谷歌云Redis获取vpc异常. get_vpc_by_network: {self._account_id} -- {e}')
        return res

    def sync_cmdb(self, cloud_name: Optional[str] = 'gcp',
                  resource_type: Optional[str] = 'redis') -> Tuple[
        bool, str]:
        """
        同步到DB
        :return:
        """
        redis_list: List[dict] = self.list_instances()
        if not redis_list:
            return False, "Redis列表为空"
        # 更新资源
        ret_state, ret_msg = redis_task(account_id=self._account_id,
                                        cloud_name=cloud_name,
                                        rows=redis_list)
        # 标记过期
        mark_expired(resource_type=resource_type, account_id=self._account_id)

        return ret_state, ret_msg


if __name__ == '__main__':
    pass