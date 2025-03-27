#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author  : shenshuo
Contact : 191715030@qq.com
Date    : 2023/2/25
Desc    : 首都在线LoadBalancer
"""

import logging
from typing import *
from . import CDSApi
from models.models_utils import lb_task, mark_expired, mark_expired_by_sync

def get_run_type(val: str) -> str:
    run_map = {
        "CREATING": "创建中",
        "RUNNING": "运行中",
        "stop": "关机",
    }
    return run_map.get(val, '未知')


class CDSLBApi(CDSApi):

    def __init__(self, access_id: str, access_key: str, region: str, account_id: str):
        self._access_id = access_id
        self._access_key = access_key
        self._region = region
        self._account_id = account_id
        super(CDSLBApi, self).__init__(access_id, access_key, region, account_id)

    def format_data(self, data: Optional[dict]) -> Dict[str, Any]:
        """
        处理数据
        :param data:
        :return:
        """
        logging.error(f"format_data__info {data}")
        res: Dict[str, Any] = dict()
        res['account_id'] = self._account_id
        res['type'] = data.get('SubProductKey')  # slb or alb
        res['name'] = data.get('InstanceName')
        res['instance_id'] = data.get('InstanceUuid')
        res['region'] = data.get('RegionId')
        res['zone'] = data.get('RegionId')
        res['status'] = get_run_type(data['Status'])
        vips = data.get('Vips')
        private_ip_list = []
        public_ip_list = []
        if isinstance(vips, list) and len(vips) > 0:
            for vip in vips:
                if vip.get('Type') == 'private': private_ip_list.append(vip.get('IP'))
                if vip.get('Type') == 'public': public_ip_list.append(vip.get('IP'))

        if private_ip_list:  res['dns_name'] = ','.join(private_ip_list)
        if public_ip_list:  res['dns_name'] = ','.join(public_ip_list)
        res['endpoint_type'] = "外网" if len(public_ip_list) > 0 else "内网"  ### 内网、外
        res['ext_info'] = {
            "vpc_id": data.get("VdcId"),
            "private_ip_list": private_ip_list,
            "public_ip_list": public_ip_list,
        }
        res['create_time'] = data.get('CreatedTime')
        return res

    def fetch_lb_instances(self):
        params = {
            "action": "DescribeLoadBalancers",
            "method": "GET",
            "url": "http://cdsapi.capitalonline.net/lb"
        }
        res = self.make_requests(method="GET", params=params)
        row = res["Data"]
        return map(self.format_data, row)

    def sync_cmdb(self, cloud_name: Optional[str] = 'cds', resource_type: Optional[str] = 'lb') -> Tuple[
        bool, str]:
        """
        同步CMDB
        :return:
        """
        # 机器比较少 根本用不上迭代器
        all_lb_list: List[dict] = []
        for _server_map in self.fetch_lb_instances():
            all_lb_list.append(_server_map)

        if not all_lb_list: return False, "LB 列表为空"
        # # 更新资源
        ret_state, ret_msg = lb_task(account_id=self._account_id, cloud_name=cloud_name, rows=all_lb_list)
        # 标记过期
        # mark_expired(resource_type=resource_type, account_id=self._account_id)
        instance_ids = [lb['instance_id'] for lb in all_lb_list]
        mark_expired_by_sync(cloud_name=cloud_name, account_id=self._account_id, resource_type=resource_type,
                             instance_ids=instance_ids, region=self._region)
        return ret_state, ret_msg
