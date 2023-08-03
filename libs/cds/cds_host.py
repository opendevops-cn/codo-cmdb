#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: shenshuo
Date  : 2023/2/25
Desc  : 首都在线主机
"""

from typing import *
from . import CDSApi
from models.models_utils import server_task, mark_expired


def get_run_type(val: str) -> str:
    run_map = {
        "CREATING": "创建中",
        "running": "运行中",
        "stop": "关机",
    }
    return run_map.get(val, '未知')


class CDSHostApi(CDSApi):
    def __init__(self, access_id: str, access_key: str, region: str, account_id: str):
        self._access_id = access_id
        self._access_key = access_key
        self._region = region
        self._account_id = account_id
        super(CDSHostApi, self).__init__(access_id, access_key, region, account_id)

    def format_data(self, data: Optional[dict]) -> Dict[str, Any]:
        """
        处理数据
        :param data:
        :return:
        """

        data_disks, public_ip_address = list(), list()
        if data['Disks']["DataDisks"]:
            data_disks = list(map(lambda x: x['Size'], data['Disks']["DataDisks"]))
        if data['PublicNetworkInterface']:
            public_ip_address = list(map(lambda x: x['IP'], data['PublicNetworkInterface']))

        if isinstance(public_ip_address, list) and len(public_ip_address) == 0: public_ip_address = ""
        ###
        private_ip_address = list(map(lambda x: x['IP'], data['PrivateNetworkInterface']))
        private_ip_address = "" if len(private_ip_address) == 0 else private_ip_address[0]
        # 定义返回
        res: Dict[str, Any] = dict()
        res['instance_id'] = data.get('InstanceId')
        res['account_id'] = self._account_id
        res['state'] = get_run_type(data['InstanceStatus'])
        res['instance_type'] = data.get('InstanceType')
        res['outer_ip'] = public_ip_address
        res['inner_ip'] = private_ip_address
        res['cpu'] = data.get('Cpu')
        res['memory'] = float(data['Ram'])
        res['name'] = data.get('InstanceName')
        res['region'] = data.get('RegionId')
        res['zone'] = ''
        res['os_name'] = data['ImageInfo']["ImageType"]
        return res

    def fetch_cds_instances(self):
        params = {
            "action": "DescribeInstances",
            "method": "POST",
            "url": "http://cdsapi.capitalonline.net/ccs"
        }

        res = self.make_requests(method="POST", params=params)
        row = res["Data"]["Instances"]
        return map(self.format_data, row)

    def sync_cmdb(self, cloud_name: Optional[str] = 'cds', resource_type: Optional[str] = 'server') -> Tuple[
        bool, str]:
        """
        同步CMDB
        :return:
        """
        # 机器比较少 根本用不上迭代器
        all_ecs = self.fetch_cds_instances()
        # 处理到一个List里面
        all_server_list: List[dict] = []
        for _server_map in all_ecs:
            all_server_list.append(_server_map)

        #     all_server_list.extend(list(_server_map))

        if not all_server_list: return False, "ECS列表为空"
        # # 更新资源
        ret_state, ret_msg = server_task(account_id=self._account_id, cloud_name=cloud_name, rows=all_server_list)
        # 标记过期
        mark_expired(resource_type=resource_type, account_id=self._account_id)
        #
        return ret_state, ret_msg