#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date   :  2023/12/15 11:02
Desc   :  谷歌云ECS主机自动发现
"""
import logging
from typing import *

from google.oauth2 import service_account
from google.cloud import compute_v1

from models.models_utils import server_task, mark_expired


def get_run_type(val):
    run_map = {
        "PROVISIONING": "创建中",
        "STAGING": "正在启动",
        "STOPPING": "关机中",
        "STOPPED": "关机",
        "SUSPENDING": "正在挂起",
        "SUSPENDED": "已挂起",
        "RUNNING": "运行中",
        "REBOOTING": "重启中",
        "TERMINATED": "销毁中",
    }
    return run_map.get(val, '未知')


def get_pay_type(val):
    pay_map = {
        "PREPAID": "包年包月",
        "POSTPAID_BY_HOUR": "按量付费"
    }
    return pay_map.get(val, '未知')


class GCPECS:
    def __init__(self, project_id: str, account_path: str, region: str, account_id: str):
        self.cloud_name = 'gcp'
        self.page_size = 100  # 分页查询时设置的每页行数。最大值：100 默认值：10
        self._region = region
        self.project_id = project_id
        self._account_id = account_id
        self.__credentials = service_account.Credentials.from_service_account_file(account_path)
        self.machine_type_client = compute_v1.MachineTypesClient(credentials=self.__credentials)

    def list_all_instances(self) -> List[dict]:
        """
        Returns a dictionary of all instances present in a project, grouped by their zone.

        Args:
        project_id: project ID or project number of the Cloud project you want to use.
        Returns:
            A dictionary with zone names as keys (in form of "zones/{zone_name}") and
            iterable collections of Instance objects as values.
        """
        instance_client = compute_v1.InstancesClient(credentials=self.__credentials)
        request = compute_v1.AggregatedListInstancesRequest()
        request.project = self.project_id
        # Use the `max_results` parameter to limit the number of results that the API returns per response page.
        request.max_results = self.page_size

        agg_list = instance_client.aggregated_list(request=request)

        ecs_list = []
        for zone, response in agg_list:
            if response.instances:
                ecs_list.extend(map(self.format_data, response.instances))

        return ecs_list

    def get_vpc_by_network(self, network: str):
        """
        获取vpc
        """
        client = compute_v1.NetworksClient(
            credentials=self.__credentials)
        request = compute_v1.GetNetworkRequest(network=network, project=self.project_id)
        response = client.get(request=request)
        return response

    @staticmethod
    def get_region_by_zone(zone: str):
        """
        获取region
        """
        return "-".join(zone.split("-")[:-1])

    @staticmethod
    def get_os_type(data):
        """
        获取操作系统类型
        """
        try:
            os_type = data.disks[0].licenses[0].split('/')[-1]
            return "Windows" if "windows" in os_type.lower() else "Linux"
        except Exception as e:
            logging.error(f"获取操作系统类型失败 {e}")
            os_type = ''
        return os_type


    def format_data(self, data) -> Dict[str, str]:
        """
        处理数据
        :param data:
        :return:
        """
        # 定义返回
        res: Dict[str, str] = dict()
        try:
            network_interface = data.network_interfaces[0]
            network = network_interface.network.split('/')[-1]

            try:
                vpc_instance = self.get_vpc_by_network(network=network)
                vpc_id = str(vpc_instance.id)
            except Exception as e:
                logging.error(f'调用谷歌云ECS获取vpc异常. get_vpc_by_network: {self._account_id} -- {e}')
                vpc_id = ''

            # vpc_id = network_interface.network.split('/')[-1]
            network_type = 'vpc'

            # 从机器类型中获取CPU和内存
            machine_type = data.machine_type.split('/')[-1]
            machine_type_request = compute_v1.GetMachineTypeRequest()
            machine_type_request.project = self.project_id
            machine_type_request.zone = data.zone.split('/')[-1]
            machine_type_request.machine_type = machine_type

            # 获取machine_type的详细信息
            machine_type_info = self.machine_type_client.get(request=machine_type_request)

            res['instance_id'] = str(data.id)
            res['vpc_id'] = vpc_id
            res['state'] = get_run_type(data.status)
            res['instance_type'] = machine_type
            res['cpu'] = str(machine_type_info.guest_cpus)  # CPU核心数
            res['memory'] = str(float(machine_type_info.memory_mb / 1024))  # 内存大小
            res['name'] = data.name
            res['network_type'] = network_type
            # res['charge_type'] = get_pay_type(data.InstanceChargeType)

            # 内外网IP,可能有多个
            inner_ip = network_interface.network_i_p
            res['inner_ip'] = inner_ip
            try:
                res['outer_ip'] = network_interface.access_configs[0].nat_i_p
            except Exception as e:
                logging.error(f"{network_interface.access_configs}  {e}")

            res['os_name'] = ""
            res['os_type'] = self.get_os_type(data)
            res['instance_create_time'] = data.creation_timestamp
            # res['instance_expired_time'] = data.expired_at
            zone = data.zone.split('/')[-1]
            res['region'] = self.get_region_by_zone(zone)
            res['zone'] = zone
            res['description'] = data.description
            # res['security_group_ids'] = data.SecurityGroupIds

            # 系统盘和数据盘
            try:
                # 系统盘和数据盘信息
                disks_info = []
                for disk in data.disks:
                    disk_info = {
                        'type': 'system' if disk.boot else 'data',
                        'size_gb': disk.disk_size_gb,
                        'device_name': disk.device_name,
                        'source': disk.source.split('/')[-1]
                    }
                    disks_info.append(disk_info)

                    # 如果是系统盘，单独记录
                    if disk.boot:
                        res['system_disk'] = str(disk.disk_size_gb)

                    if not disk.boot:
                        res['data_disk'] = str(disk.disk_size_gb)
                # 如果需要，可以将所有磁盘信息添加到结果中
                # res['disks'] = disks_info
            except (IndexError, KeyError, TypeError):
                res['system_disk'] = ""
            #
            # try:
            #     # print('数据盘', data.DataDisks, type(data.DataDisks))
            #     res['data_disk'] = data.DataDisks[0].DiskSize
            # except (IndexError, KeyError, TypeError):
            #     res['data_disk'] = ""

        except Exception as err:
            logging.error(f"谷歌云 ECS   data format err {self._account_id} {err}")
        return res

    def sync_cmdb(self, cloud_name: Optional[str] = 'gcp', resource_type: Optional[str] = 'server') -> Tuple[
        bool, str]:
        """
        资产信息更新到DB
        :return:
        """
        all_ecs_list: List[dict] = self.list_all_instances()
        if not all_ecs_list:
            return False, "ECS列表为空"
        # 更新资源
        ret_state, ret_msg = server_task(account_id=self._account_id, cloud_name=cloud_name, rows=all_ecs_list)
        # 标记过期
        mark_expired(resource_type=resource_type, account_id=self._account_id)

        return ret_state, ret_msg


if __name__ == '__main__':
    pass
