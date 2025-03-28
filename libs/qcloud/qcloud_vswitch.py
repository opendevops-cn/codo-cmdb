#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2019/1/6 17:51
Desc    : 腾讯云 虚拟子网
"""

import json
import logging
from typing import *
from tencentcloud.common import credential
from tencentcloud.vpc.v20170312 import vpc_client, models
from models.models_utils import vswitch_task, mark_expired, mark_expired_by_sync


class QcloudVSwitch:
    def __init__(self, access_id: str, access_key: str, region: str, account_id):
        self._region = region
        self._offset = 0  # 偏移量,这里拼接的时候必须是字符串
        self._limit = 100  # 官方默认是20，大于100 需要设置偏移量再次请求
        self._account_id = account_id
        self.__cred = credential.Credential(access_id, access_key)
        self.client = vpc_client.VpcClient(self.__cred, self._region)
        self.req = models.DescribeSubnetsRequest()

    def get_all_subnet(self) -> list:
        subnet_list = []
        limit = self._limit
        offset = self._offset
        try:
            while True:
                params = {
                    "Offset": str(offset),
                    "Limit": str(limit)
                }
                self.req.from_json_string(json.dumps(params))
                resp = self.client.DescribeSubnets(self.req)
                if not resp.SubnetSet:
                    break

                subnet_list.extend(map(self.format_data, resp.SubnetSet))
                offset += limit
            return subnet_list
        except Exception as err:
            logging.error(err)
            return []

    def format_data(self, data) -> Dict[str, Any]:
        res: Dict[str, Any] = dict()

        res['instance_id'] = data.SubnetId
        res['name'] = data.SubnetName
        res['vpc_id'] = data.VpcId
        res['region'] = self._region
        res['zone'] = data.Zone
        res['address_count'] = data.AvailableIpAddressCount
        res['route_id'] = data.RouteTableId

        res['create_time'] = data.CreatedTime
        res['is_default'] = data.IsDefault
        res['cidr_block_v4'] = data.CidrBlock
        res['cidr_block_v6'] = data.Ipv6CidrBlock

        return res

    def sync_cmdb(self, cloud_name: Optional[str] = 'qcloud', resource_type: Optional[str] = 'vswitch') -> Tuple[
        bool, str]:
        """
        同步CMDB
        """
        all_subnet_list: List[list, Any, None] = self.get_all_subnet()

        if not all_subnet_list:
            return False, "虚拟子网列表为空"
        # 同步资源
        ret_state, ret_msg = vswitch_task(account_id=self._account_id, cloud_name=cloud_name, rows=all_subnet_list)

        # 标记过期
        # mark_expired(resource_type=resource_type, account_id=self._account_id)
        instance_ids = [subnet['instance_id'] for subnet in all_subnet_list]
        mark_expired_by_sync(cloud_name=cloud_name, account_id=self._account_id, resource_type=resource_type,
                             instance_ids=instance_ids, region=self._region)

        return ret_state, ret_msg
