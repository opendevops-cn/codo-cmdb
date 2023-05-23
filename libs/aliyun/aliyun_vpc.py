#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2019/1/6 17:51
Desc    : 阿里云 VPC
"""

import json
import logging
from typing import *
from aliyunsdkcore.client import AcsClient
from aliyunsdkvpc.request.v20160428.DescribeVpcsRequest import DescribeVpcsRequest
from models.models_utils import vpc_task, mark_expired


class AliyunVPC:
    def __init__(self, access_id: Optional[str], access_key: Optional[str], region: Optional[str],
                 account_id: Optional[str]):
        self.page_number = 1  # 实例状态列表的页码。起始值：1 默认值：1
        self.page_size = 20  # 分页查询时设置的每页行数。最大值：100 默认值：10
        self._region = region
        self._account_id = account_id
        self.request_vpc = DescribeVpcsRequest()
        self.request_vpc.set_accept_format('json')
        self.__client = AcsClient(access_id, access_key, self._region)

    def get_region_vpc(self):
        try:
            self.request_vpc.set_PageNumber(self.page_number)
            self.request_vpc.set_PageSize(self.page_size)
            response = self.__client.do_action_with_exception(self.request_vpc)

            return json.loads(str(response, encoding="utf8"))['Vpcs']
        except Exception as err:
            logging.error(f'Get vpc response error: {err}')
            return False

    def get_all_vpc(self):
        vpc_list = []
        while True:
            data = self.get_region_vpc()
            if not data or 'Vpc' not in data: break
            if not data['Vpc']: break
            self.page_number += 1
            row = data['Vpc']
            if not row: break
            vpc_list.extend(map(self._format_data, row))
        return vpc_list

    def _format_data(self, data: Optional[Dict]) -> Dict[str, Any]:
        res: Dict[str, Any] = dict()

        try:
            vpc_switch = data.get('VSwitchIds').get('VSwitchId')
            vpc_switch = ','.join(vpc_switch)
        except (KeyError, TypeError):
            vpc_switch = ''

        res['instance_id'] = data.get('VpcId')
        res['vpc_name'] = data.get('VpcName')
        res['vpc_router'] = data.get('VRouterId')
        res['vpc_switch'] = vpc_switch
        res['cidr_block_v4'] = data.get('CidrBlock')
        res['cidr_block_v6'] = data.get('Ipv6CidrBlock')
        res['region'] = self._region
        res['is_default'] = False
        res['state'] = data.get('Status')
        res['creation_time'] = data.get('CreationTime')

        return res

    def sync_cmdb(self, cloud_name: Optional[str] = 'aliyun', resource_type: Optional[str] = 'vpc') -> Tuple[
        bool, str]:
        # 获取数据
        all_vpc_list: List[dict] = self.get_all_vpc()
        if not all_vpc_list: return False, "VPC列表为空"
        # 更新资源
        ret_state, ret_msg = vpc_task(account_id=self._account_id, cloud_name=cloud_name, rows=all_vpc_list)
        # 标记过期
        mark_expired(resource_type=resource_type, account_id=self._account_id)

        return ret_state, ret_msg


if __name__ == '__main__':
    pass
