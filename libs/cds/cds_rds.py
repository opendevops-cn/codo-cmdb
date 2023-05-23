#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: shenshuo
Date  : 2023/2/25
Desc  : 首都在线MySQL
"""

from models.models_utils import mysql_task, mark_expired
from typing import *
from . import CDSApi


def get_run_type(val: str) -> str:
    run_map = {
        "CREATING": "创建中",
        "RUNNING": "运行中",
        "stop": "关机",
    }
    return run_map.get(val, '未知')


class CDSMysqlApi(CDSApi):
    def __init__(self, access_id: str, access_key: str, region: str, account_id: str):
        self._access_id = access_id
        self._access_key = access_key
        self._region = region
        self._account_id = account_id
        super(CDSMysqlApi, self).__init__(access_id, access_key, region, account_id)

    def format_data(self, data: Optional[dict]) -> Dict[str, Any]:
        """
        处理数据
        :param data:
        :return:
        """
        res: Dict[str, Any] = dict()
        res['instance_id'] = data.get('InstanceUuid')
        res['account_id'] = self._account_id
        res['state'] = get_run_type(data['Status'])
        res['charge_type'] = data.get('InstanceType')
        res['name'] = data.get('InstanceName')
        res['region'] = data.get('RegionId')
        res['zone'] = data.get('RegionId').split('_')[-1]
        res['db_engine'] = 'MySQL'
        res['db_version'] = data.get('Version')
        res['db_class'] = f"{data.get('Cpu')}C/{float(data['Ram']) / 1024}G/{data.get('Disks')}G"
        res['db_address'] = {
            "items": [
                {
                    "endpoint_type": "Primary",
                    "type": "private",
                    "port": data.get('Port'),
                    "ip": data.get('IP'),
                    "domain": "",
                },
                {
                    "endpoint_type": "Primary",
                    "type": "public",
                    "port": "",
                    "ip": "",
                    "domain": "",
                },
            ]
        }
        res['create_time'] = data.get('CreatedTime')
        # logging.error(f"format_data__info {res}")
        return res

    def fetch_mysql_instances(self):
        params = {
            "action": "DescribeDBInstances",
            "method": "GET",
            "url": "http://cdsapi.capitalonline.net/mysql"
        }
        res = self.make_requests(method="GET", params=params)

        row = res["Data"]
        return map(self.format_data, row)

    def sync_cmdb(self, cloud_name: Optional[str] = 'cds', resource_type: Optional[str] = 'mysql') -> Tuple[
        bool, str]:
        """
        同步CMDB
        :return:
        """
        # 机器比较少 根本用不上迭代器
        all_cdb_list: List[dict] = []
        for _server_map in self.fetch_mysql_instances():
            all_cdb_list.append(_server_map)

        #     all_server_list.extend(list(_server_map))

        if not all_cdb_list: return False, "MySQL列表为空"
        # # 更新资源
        ret_state, ret_msg = mysql_task(account_id=self._account_id, cloud_name=cloud_name, rows=all_cdb_list)
        # 标记过期
        mark_expired(resource_type=resource_type, account_id=self._account_id)
        #
        return ret_state, ret_msg
