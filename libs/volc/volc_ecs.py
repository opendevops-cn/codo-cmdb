#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date   :  2023/11/22 11:02
Desc   :  火山云ECS主机自动发现
"""
import json
import logging
from typing import *
from models.models_utils import server_task, mark_expired
import volcenginesdkcore
import volcenginesdkecs
from volcenginesdkcore.rest import ApiException


def get_run_type(val):
    run_map = {
        "PENDING": "创建中",
        "LAUNCH_FAILED": "创建失败",
        "RUNNING": "运行中",
        "STOPPED": "关机",
        "STARTING": "开机中",
        "STOPPING": "关机中",
        "REBOOTING": "重启中",
        "SHUTDOWN": "停止待销毁",
        "TERMINATING": "销毁中",
    }
    return run_map.get(val, '未知')


def get_pay_type(val):
    pay_map = {
        "PREPAID": "包年包月",
        "POSTPAID_BY_HOUR": "按量付费"
    }
    return pay_map.get(val, '未知')


class VolCECS:
    def __init__(self, access_id: str, access_key: str, region: str, account_id: str):
        self.cloud_name = 'volc'
        self.page_number = 1  # 实例状态列表的页码。起始值：1 默认值：1
        self.page_size = 100  # 分页查询时设置的每页行数。最大值：100 默认值：10
        self._region = region
        self._account_id = account_id
        configuration = volcenginesdkcore.Configuration()
        configuration.ak = access_id
        configuration.sk = access_key
        configuration.region = self._region
        # set default configuration
        volcenginesdkcore.Configuration.set_default(configuration)
        self.api_instance = volcenginesdkecs.ECSApi()

    def get_describe_info(self, next_token):

        try:
            instances_request = volcenginesdkecs.DescribeInstancesRequest(
                next_token=next_token)
            resp = self.api_instance.describe_instances(instances_request)
            return resp
        except ApiException as e:
            logging.error("Exception when calling api: %s\n" % e)
        return []

    def get_all_ecs(self):
        """
        循环分页获取所有的ECS信息，返回迭代器
        """
        ecs_list = []
        next_token = None
        try:
            while True:
                data = self.get_describe_info(next_token)
                next_token = data.next_token
                if not data or not data.instances or not next_token:
                    break

                logging.warning(f"33333333{data.instances}")
                ecs_list.extend(map(self.format_data, data.instances))
            return ecs_list
        except Exception as err:
            logging.error(f"火山云ECS  get all ecs{self._account_id} {err}")
            return ecs_list
            # yield map(self.format_data, list(data.instances))

    def format_data(self, data) -> Dict[str, str]:
        """
        处理数据
        :param data:
        :return:
        """
        logging.error(f" format_data >>>>>>{type(data)} {data.eip_address}")
        # 定义返回
        res: Dict[str, str] = dict()
        try:
            logging.error(f" format_data {data}")
            network_interface = data.network_interfaces[0]
            vpc_id = data.vpc_id
            network_type = '经典网络' if not vpc_id else 'vpc'

            res['instance_id'] = data.instance_id
            res['vpc_id'] = vpc_id
            res['state'] = get_run_type(data.status)
            res['instance_type'] = data.instance_type_id
            res['cpu'] = data.cpus
            res['memory'] = data.memory_size / 1024
            res['name'] = data.instance_name
            res['network_type'] = network_type
            # res['charge_type'] = get_pay_type(data.InstanceChargeType)

            # 内外网IP,可能有多个
            # outer_ip = data.eip_address
            inner_ip = network_interface.primary_ip_address
            res['inner_ip'] = inner_ip
            # res['outer_ip'] = outer_ip

            res['os_name'] = data.os_name
            res['os_type'] = data.os_type
            res['instance_create_time'] = data.created_at
            res['instance_expired_time'] = data.expired_at
            res['region'] = self._region
            res['zone'] = data.zone_id
            res['description'] = data.description
            # res['security_group_ids'] = data.SecurityGroupIds

        except Exception as err:
            logging.error(f"火山云ECS   data format err {self._account_id} {err}")

        # 系统盘和数据盘
        # try:
        #     # system_disk = data.SystemDisk
        #     # print('系统盘', system_disk, type(system_disk))
        #     res['system_disk'] = data.SystemDisk.DiskSize  # 系统盘只有一块
        # except (IndexError, KeyError, TypeError):
        #     res['system_disk'] = ""
        #
        # try:
        #     # print('数据盘', data.DataDisks, type(data.DataDisks))
        #     res['data_disk'] = data.DataDisks[0].DiskSize
        # except (IndexError, KeyError, TypeError):
        #     res['data_disk'] = ""

        return res

    def sync_cmdb(self, cloud_name: Optional[str] = 'volc', resource_type: Optional[str] = 'server') -> Tuple[
        bool, str]:
        """
        资产信息更新到DB
        :return:
        """
        all_ecs_list: List[dict] = self.get_all_ecs()
        logging.info(all_ecs_list)
        if not all_ecs_list: 
            return False, "ECS列表为空"
        # 更新资源
        ret_state, ret_msg = server_task(account_id=self._account_id, cloud_name=cloud_name, rows=all_ecs_list)
        # 标记过期
        mark_expired(resource_type=resource_type, account_id=self._account_id)

        return ret_state, ret_msg


if __name__ == '__main__':
    pass
