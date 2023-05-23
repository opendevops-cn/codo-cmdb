#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/2/6 17:51
Desc    : 腾讯云 虚拟局域网
"""

import json
import logging
from typing import *
from tencentcloud.common import credential
from tencentcloud.vpc.v20170312 import vpc_client, models
from models.models_utils import vpc_task, mark_expired


class QCloudCVPC:
    def __init__(self, access_id: str, access_key: str, region: str, account_id):
        self._offset = 0  # 偏移量,这里拼接的时候必须是字符串
        self._limit = 100  # 官方默认是20，大于100 需要设置偏移量再次请求
        self._region = region
        self._account_id = account_id
        self.__cred = credential.Credential(access_id, access_key)
        self.client = vpc_client.VpcClient(self.__cred, self._region)
        self.req = models.DescribeVpcsRequest()

    def get_all_vpc(self):
        vpc_list = []
        limit = self._limit
        offset = self._offset
        try:
            while True:
                params = {
                    "Offset": str(offset),
                    "Limit": str(limit)
                }
                self.req.from_json_string(json.dumps(params))
                resp = self.client.DescribeVpcs(self.req)

                if not resp.VpcSet:
                    break
                vpc_list.extend(map(self.format_data, resp.VpcSet))
                offset += limit
            return vpc_list
        except Exception as err:
            logging.error(err)
            return []

    def format_data(self, data) -> Dict[str, Any]:
        res: Dict[str, Any] = dict()
        # print(data)
        res['instance_id'] = data.VpcId
        res['vpc_name'] = data.VpcName
        res['region'] = self._region
        res['create_time'] = data.CreatedTime
        res['is_default'] = data.IsDefault
        res['cidr_block_v4'] = data.CidrBlock
        res['cidr_block_v6'] = data.Ipv6CidrBlock

        return res

    def sync_cmdb(self, cloud_name: Optional[str] = 'qcloud', resource_type: Optional[str] = 'vpc') -> Tuple[bool, str]:
        """
        同步CMDB
        """
        all_vpc_list: List[list, Any, None] = self.get_all_vpc()

        if not all_vpc_list:  return False, "VPC列表为空"
        # 同步资源
        ret_state, ret_msg = vpc_task(account_id=self._account_id, cloud_name=cloud_name, rows=all_vpc_list)

        # 标记过期
        mark_expired(resource_type=resource_type, account_id=self._account_id)

        return ret_state, ret_msg


class QCloudNetwork:
    # 本接口（DescribeNetworkInterfaces）用于查询弹性网卡列表。
    def __init__(self, access_id: str, access_key: str, region: str, account_id):
        self._offset = 0  # 偏移量,这里拼接的时候必须是字符串
        self._limit = 100  # 官方默认是20，大于100 需要设置偏移量再次请求

        self._region = region
        self._account_id = account_id
        self.__cred = credential.Credential(access_id, access_key)
        self.client = vpc_client.VpcClient(self.__cred, self._region)
        self.req = models.DescribeNetworkInterfacesRequest()

    def get_all_network_interface(self):
        network_list = []
        limit = self._limit
        offset = self._offset
        try:
            while True:
                params = {
                    "Offset": offset,
                    "Limit": limit
                }
                self.req.from_json_string(json.dumps(params))
                resp = self.client.DescribeNetworkInterfaces(self.req)
                if not resp.NetworkInterfaceSet:
                    break
                # network_list.extend(map(self.format_data, resp.NetworkInterfaceSet))
                network_list.extend(resp.NetworkInterfaceSet)
                offset += limit
            return network_list
        except Exception as err:
            logging.error(err)
            return False

    # def sync_cmdb(self, cloud_name: Optional[str] = 'qcloud', resource_type: Optional[str] = 'clb') -> Tuple[
    #     bool, str]:
    #     """
    #     同步CMDB
    #     """
    #     all_alb_list: List[list, Any, None] = self.get_all_slb()
    #     if not all_alb_list:  return False, "CLB列表为空"
    #     # 同步资源
    #     ret_state, ret_msg = vpc_task(account_id=self._accountID, cloud_name=cloud_name, rows=all_alb_list)
    #
    #     # 标记过期
    #     mark_expired(resource_type=resource_type, account_id=self._accountID)
    #
    #     return ret_state, ret_msg

    def index(self):
        network_set = self.get_all_network_interface()
        if not network_set and not isinstance(network_set, list): return False

        for nw in network_set:
            print(nw)
        return True
