#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2019/1/6 17:51
Desc    : 阿里云虚拟交换机
"""

import json
import logging
from typing import *
from aliyunsdkcore.client import AcsClient
from aliyunsdkvpc.request.v20160428.DescribeVSwitchesRequest import DescribeVSwitchesRequest
from models.models_utils import vswitch_task, mark_expired, mark_expired_by_sync


class AliyunVSwitch:
    def __init__(self, access_id: Optional[str], access_key: Optional[str], region: Optional[str],
                 account_id: Optional[str]):
        self.page_number = 1  # 实例状态列表的页码。起始值：1 默认值：1
        self.page_size = 20  # 分页查询时设置的每页行数。最大值：100 默认值：10
        self._region = region
        self._account_id = account_id
        self.request_vswitch = DescribeVSwitchesRequest()
        self.request_vswitch.set_accept_format('json')
        self.__client = AcsClient(access_id, access_key, self._region)

    def get_region_vswitch(self, vpc_id=None):
        try:
            self.request_vswitch.set_VpcId(vpc_id) if vpc_id else None
            self.request_vswitch.set_PageNumber(self.page_number)
            self.request_vswitch.set_PageSize(self.page_size)
            response = self.__client.do_action_with_exception(self.request_vswitch)
            return json.loads(str(response, encoding="utf8"))['VSwitches']
        except Exception as err:
            logging.error(f'Get vswitch response error: {err}')
            return False

    def get_all_vpc(self):
        vswitch__list = []
        while True:
            data = self.get_region_vswitch()
            if not data or 'VSwitch' not in data: break
            if not data['VSwitch']: break
            self.page_number += 1
            row = data['VSwitch']
            if not row: break
            vswitch__list.extend(map(self._format_data, row))
        return vswitch__list

    def _format_data(self, data: Optional[Dict]) -> Dict[str, Any]:
        res: Dict[str, Any] = dict()

        res['instance_id'] = data.get('VSwitchId')
        res['name'] = data.get('VSwitchName')
        res['vpc_id'] = data.get('VpcId')
        res['cidr_block_v4'] = data.get('CidrBlock')
        res['cidr_block_v6'] = data.get('Ipv6CidrBlock')
        res['region'] = self._region
        res['zone'] = data.get('ZoneId')
        res['route_id'] = data.get('RouteTableId')
        res['address_count'] = data.get('AvailableIpAddressCount')
        res['description'] = data.get('Description')
        res['is_default'] = data.get('IsDefault')
        # res['state'] = data.get('Status')
        # res['creation_time'] = data.get('CreationTime')

        return res

    def sync_cmdb(self, cloud_name: Optional[str] = 'aliyun', resource_type: Optional[str] = 'vswitch') -> Tuple[
        bool, str]:
        # 获取数据
        all_vpc_list: List[dict] = self.get_all_vpc()
        if not all_vpc_list: return False, "虚拟子网列表为空"
        # 更新资源
        ret_state, ret_msg = vswitch_task(account_id=self._account_id, cloud_name=cloud_name, rows=all_vpc_list)
        # 标记过期
        # mark_expired(resource_type=resource_type, account_id=self._account_id)
        instance_ids = [row['instance_id'] for row in all_vpc_list]
        mark_expired_by_sync(cloud_name=cloud_name, account_id=self._account_id, resource_type=resource_type,
                             instance_ids=instance_ids, region=self._region)

        return ret_state, ret_msg


if __name__ == '__main__':
    pass
