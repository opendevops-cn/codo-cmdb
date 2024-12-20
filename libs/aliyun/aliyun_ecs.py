#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date   : 2023/2/25 11:02
Desc   : 阿里云  ECS
"""

import json
import logging
from typing import *
from aliyunsdkcore.client import AcsClient
from aliyunsdkecs.request.v20140526.DescribeInstancesRequest import DescribeInstancesRequest
from models.models_utils import server_task, mark_expired


def get_run_type(val: str) -> str:
    run_map = {
        "Pending": "创建中",
        "Running": "运行中",
        "Stopped": "关机",
    }
    return run_map.get(val, '未知')


def get_paymeny_type(val: str) -> str:
    pay_map = {
        "PrePaid": "包年包月",
        "PostPaid": "按量付费"
    }
    return pay_map.get(val, '未知')


def get_network_type(val: str) -> str:
    network_map = {
        "classic": "经典网络",
        "vpc": "专有网络"
    }
    return network_map.get(val, '未知')


def get_inner_ip(inner_ip_list) -> str:
    try:
        inner_ip = ",".join(inner_ip_list) if len(inner_ip_list) > 1 else inner_ip_list[0]
    except IndexError:
        inner_ip = ""
    return inner_ip


def get_outer_ip(outer_ip_list) -> str:
    # print('outer_ip_list', outer_ip_list)
    if isinstance(outer_ip_list, str):
        outer_ip = outer_ip_list
    else:
        try:
            outer_ip = ",".join(outer_ip_list) if len(outer_ip_list) > 1 else outer_ip_list[0]
        except IndexError:
            outer_ip = ""
    return outer_ip


class AliyunEcsClient:
    def __init__(self, access_id: str, access_key: str, region: str, account_id: str):
        self.page_number = 1  # 实例状态列表的页码。起始值：1 默认值：1
        self.page_size = 100  # 分页查询时设置的每页行数。最大值：100 默认值：10
        self._access_id = access_id
        self._access_key = access_key
        self._region = region
        self._accountID = account_id
        self.__client = AcsClient(self._access_id, self._access_key, self._region)

    def get_describe_info(self) -> Union[None, dict]:
        """
        :return: bool, data, ToTal
        """
        try:
            request = DescribeInstancesRequest()
            # request.set_accept_format('json')
            request.set_PageNumber(self.page_number)
            request.set_PageSize(self.page_size)
            response = self.__client.do_action_with_exception(request)
            response_data = json.loads(str(response, encoding="utf8"))
        except Exception as err:
            logging.error(f'获取ECS信息失败:{err}')
            return None
        return response_data['Instances']

    def format_data(self, data: Optional[dict]) -> Dict[str, Any]:
        """
        处理数据
        :param data:
        :return:
        """
        # 定义返回
        res: Dict[str, Any] = {}
        vpc_id = data.get('VpcAttributes', {}).get('VpcId', '')
        res['vpc_id'] = vpc_id
        res['instance_id'] = data.get('InstanceId')
        res['state'] = get_run_type(data.get('Status'))
        res['instance_type'] = data.get('InstanceType')
        res['cpu'] = data.get('Cpu')
        res['memory'] = int(int(data.get('Memory')) / 1024)
        res['name'] = data.get('InstanceName')
        res['region'] = self._region
        res['zone'] = data['ZoneId']
        res['charge_type'] = get_paymeny_type(data.get('InstanceChargeType'))
        res['network_type'] = get_network_type(data.get('InstanceNetworkType'))

        # 内外网IP,可能有多个 (阿里云VPC和经典网络取值不同)
        if res['network_type'] == '专有网络':
            # vpc内网
            inner_ip_list = data['VpcAttributes']['PrivateIpAddress']['IpAddress']
            inner_ip = get_inner_ip(inner_ip_list)

            # vpc外网 (有公网取公网IP，没有则取EIP)
            public_ip_list = data['PublicIpAddress']['IpAddress']
            eip_list = data['EipAddress']['IpAddress']
            outer_ip_list = eip_list if len(public_ip_list) == 0 else public_ip_list
            outer_ip = get_outer_ip(outer_ip_list)

        else:
            # classic 内网
            inner_ip_list = data['InnerIpAddress']['IpAddress']
            inner_ip = get_inner_ip(inner_ip_list)

            # classic 公网
            public_ip_list = data['PublicIpAddress']['IpAddress']
            outer_ip = get_outer_ip(public_ip_list)

        res['inner_ip'] = inner_ip
        res['outer_ip'] = outer_ip
        try:
            res['security_group_ids'] = data['SecurityGroupIds']['SecurityGroupId']
        except Exception as err:
            res['security_group_ids'] = []

        res['os_name'] = data.get('OSName')
        res['instance_create_time'] = data.get('CreationTime')
        res['instance_expired_time'] = data.get('ExpiredTime')

        return res

    def get_all_ecs(self):
        """
        循环分页获取所有的ECS信息，返回迭代器
        """
        self.page_number = 1
        while True:
            data = self.get_describe_info()
            if not data or 'Instance' not in data: break
            if not data['Instance']: break
            self.page_number += 1
            row = data['Instance']
            if not row: break
            yield map(self.format_data, row)

    def sync_cmdb(self, cloud_name: Optional[str] = 'aliyun', resource_type: Optional[str] = 'server') -> Tuple[
        bool, str]:
        """
        同步CMDB
        :return:
        """
        # 所有的ECS对象，是一个迭代器
        all_ecs: Generator[map] = self.get_all_ecs()
        # 处理到一个List里面
        all_server_list: List[dict] = []
        for _server_map in all_ecs:
            all_server_list.extend(list(_server_map))

        if not all_server_list: return False, "ECS列表为空"
        # 更新资源
        ret_state, ret_msg = server_task(account_id=self._accountID, cloud_name=cloud_name, rows=all_server_list)
        # 标记过期
        mark_expired(resource_type=resource_type, account_id=self._accountID)

        return ret_state, ret_msg


if __name__ == '__main__':
    pass
