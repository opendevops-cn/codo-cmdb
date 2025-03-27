#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/1/27 11:02
Desc    : AWS EC2
Docs    : https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html?highlight=describe_instances#EC2.Client.describe_instances
"""

import logging
import boto3
from typing import *
from models.models_utils import server_task, mark_expired, mark_expired_by_sync, server_task_batch


def get_run_type(val):
    run_map = {
        "pending": "创建中",
        "running": "运行中",
        "stopping": "关机中",
        "stopped": "关机",
        "terminated": "终止",
    }
    return run_map.get(val, '未知')


class AwsEc2Client:
    def __init__(self, access_id: Optional[str], access_key: Optional[str], region: Optional[str],
                 account_id: Optional[str]):
        self._access_id = access_id
        self._access_key = access_key
        self._region = region
        self._accountID = account_id
        self.__client = boto3.client(
            'ec2', region_name=self._region,
            aws_access_key_id=self._access_id,
            aws_secret_access_key=self._access_key
        )

    def format_data(self, data: Optional[dict]):
        """
        处理数据
        :param data:
        :return:
        """
        if not isinstance(data, dict): raise TypeError
        # 定义返回
        res: Dict[str, str] = {}
        res['instance_id'] = data.get('InstanceId')
        # HostName 只要Tag里面Name的定义(标准)
        try:
            tag_list = data.get('Tags')
            tag_list = filter(lambda x: x["Key"] == "Name", tag_list)
            res['name'] = list(tag_list)[0].get('Value')
        except (KeyError, IndexError, TypeError):
            res['name'] = '未发现Name'

        res['instance_type'] = data.get('InstanceType')
        # res['cloudwatch_state'] = data.get('Monitoring').get('State')
        res['region'] = self._region
        res['zone'] = data.get('Placement').get('AvailabilityZone')
        res['inner_ip'] = data.get('PrivateIpAddress')
        res['outer_ip'] = data.get('PublicIpAddress')
        state = data['State']['Name']
        res['state'] = get_run_type(state)
        res['charge_type'] = '按量付费'
        res['network_type'] = '专有网络' if data.get('VpcId') else '经典网络'
        res['os_name'] = data.get('Platform')  # 可能是自定义的Image 没找到OSName
        # res['instance_create_time'] = ''
        # res['instance_expired_time'] = ''  # AWS按量没有过期时间

        return res

    def get_all_ec2(self) -> List[dict]:
        response = self.__client.describe_instances()
        reservations: List[dict] = response['Reservations']
        if not reservations:
            logging.error("获取EC2 Instances信息失败")
            return []
        # 所有EC2
        all_ec2_list: List[Dict[str, str]] = []
        for ret in reservations:
            for server_data in ret['Instances']:
                res = self.format_data(server_data)
                all_ec2_list.append(res)
        return all_ec2_list

    def sync_cmdb(self, cloud_name: Optional[str] = 'aws', resource_type: Optional[str] = 'server') -> Tuple[
        bool, str]:
        # 所有EC2数据
        all_ec2_list: List[dict] = self.get_all_ec2()
        if not all_ec2_list: return False, "EC2列表为空"
        # 更新资源
        ret_state, ret_msg = server_task_batch(account_id=self._accountID, cloud_name=cloud_name, rows=all_ec2_list)
        # 标记过期
        # mark_expired(resource_type=resource_type, account_id=self._accountID)
        instance_ids = [row['instance_id'] for row in all_ec2_list]
        mark_expired_by_sync(cloud_name=cloud_name, account_id=self._accountID, resource_type=resource_type,
                             instance_ids=instance_ids, region=self._region)

        return ret_state, ret_msg


if __name__ == '__main__':
    pass
