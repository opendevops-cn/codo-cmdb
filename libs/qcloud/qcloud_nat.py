#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# @File    :   qcloud_nat.py
# @Time    :   2024/10/12 14:21:44
# @Author  :   DongdongLiu
# @Version :   1.0
# @Desc    :   腾讯云NAT网关实例

import json
import logging
from typing import *

from tencentcloud.common import credential
from tencentcloud.vpc.v20170312 import vpc_client, models as vpc_models

from models.models_utils import nat_task, mark_expired, mark_expired_by_sync

def get_run_type(val):
    run_map = {
        "PENDING": "生产中",
        "DELETING": "删除中/子实例关闭中",
        "AVAILABLE": "运行中",
        "UPDATING": "升级中",
        "PENDFAILURE": "创建失败",
        "DELETEFAILURE": "删除失败",
        "DENIED": "子实例关闭中"
    }
    return run_map.get(val, '未知')

def get_spec_type(val):
    return {
        1: "传统型",
        2: "标准型"
    }.get(val, '未知')


class QCloudNAT:
    def __init__(self, access_id: str, access_key: str, region: str, account_id: str):
        self.cloud_name = 'qcloud'
        self._offset = 0  # 偏移量,这里拼接的时候必须是字符串
        self._limit = 5  # 官方默认是20，大于100 需要设置偏移量再次请求：offset=100,offset={机器总数}
        self._region = region
        self._account_id = account_id
        self.__cred = credential.Credential(access_id, access_key)
        self.client = vpc_client.VpcClient(self.__cred, self._region)
        
    
    def describe_nat_gateways(self, offset: int = 0) -> List:
        """腾讯云NAT网关实例列表
        """
        req = vpc_models.DescribeNatGatewaysRequest()
        req.Offset = offset
        req.Limit = self._limit
        resp = self.client.DescribeNatGateways(req)
        return resp.NatGatewaySet
    
    def get_all_nat_gateways(self) -> List:
        all_nat_gateways = []
        offset = self._offset
        while True:
            nat_gateways = self.describe_nat_gateways(offset=offset)
            if not nat_gateways:
                break
            all_nat_gateways.extend([self.process_nat_gateway(data) for data in nat_gateways])
            offset += self._limit
        return all_nat_gateways
    
    def process_nat_gateway(self, data: Dict):
        """处理单个NAT网关实例
        """
        res: Dict[str, Any] = dict()
        try:
            # network_interface_id = data.network_interface_id
            res['instance_id'] = data.NatGatewayId
            res['vpc_id'] = data.VpcId
            res['state'] = get_run_type(data.State)
            res['name'] = data.NatGatewayName
            # res['network_interface_id'] = network_interface_id
            # res['charge_type'] = get_pay_type(data.billing_type)
            # res['project_name'] = data.project_name
            # res['spec'] = get_spec_type(data.NatProductVersion)
            # 内外网IP,可能有多个
            res["charge_type"] = "按量计费-按使用量计费"
            eip_addresses = data.PublicIpAddressSet
            if isinstance(eip_addresses, list):
                outer_ip = [eip.PublicIpAddress for eip in eip_addresses]
            if eip_addresses:
                res['network_type'] = '公网'
            res['outer_ip'] = outer_ip
            res['create_time'] = data.CreatedTime
            # res['expired_time'] = data.expired_time
            res['region'] = self._region
            res['zone'] = data.Zone
            # res['description'] = data.description
            res['subnet_id'] = data.SubnetId

        except Exception as err:
            logging.error(f"腾讯云 process_nat_gateway err. account_id: {self._account_id},  err:{err}")

        return res
    
    def sync_cmdb(self, cloud_name: Optional[str] = 'qcloud',
                resource_type: Optional[str] = 'nat') -> Tuple[
        bool, str]:
        """
        资产信息更新到DB
        :return:
        """
        all_nat_gateway_list: List[dict] = self.get_all_nat_gateways()
        if not all_nat_gateway_list:
            return False, "Nat列表为空"
        # 更新资源
        ret_state, ret_msg = nat_task(account_id=self._account_id, 
                                        cloud_name=cloud_name,
                                        rows=all_nat_gateway_list)
        # 标记过期
        # mark_expired(resource_type=resource_type, account_id=self._account_id)
        instance_ids = [nat['instance_id'] for nat in all_nat_gateway_list]
        mark_expired_by_sync(cloud_name=cloud_name, account_id=self._account_id, resource_type=resource_type,
                             instance_ids=instance_ids, region=self._region)

        return ret_state, ret_msg
    
    
    
if __name__ == '__main__':
    pass