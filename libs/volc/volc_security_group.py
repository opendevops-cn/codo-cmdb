# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/4/2
# @Description: 火山云安全组

from __future__ import print_function
import logging
from typing import *

from volcenginesdkcore.rest import ApiException
from volcenginesdkvpc import DescribeSecurityGroupsRequest, DescribeSecurityGroupAttributesRequest

from libs.volc.volc_vpc import VolCVPC
from models.models_utils import security_group_task, mark_expired, mark_expired_by_sync

SecurityGroupTypeMapping = {
    "default": "默认",
    "normal": "自定义",
    "VpnGW": "VPN网关",
    "NatGW": "Nat网关"
}

def get_port_range(port_start: str, port_end: str) -> str:
    """
    火山云安全组端口范围
    :param port_start:
    :param port_end:
    :return:
    """
    if port_start != port_end:
        return f"{port_start}-{port_end}"
    else:
        if port_start == port_end == -1:
            return "ALL"
        else:
            return port_start


class VolCSecurityGroup(VolCVPC):

    def get_describe_security_group(self):
        """
        查询安全组列表
        https://api.volcengine.com/api-docs/view?serviceCode=vpc&version=2020-04-01&action=DescribeSecurityGroups
        :param
        :return:
        """
        try:
            instances_request = DescribeSecurityGroupsRequest(page_number=self.page_number, page_size=self.page_size)
            resp = self.api_instance.describe_security_groups(instances_request)
            return resp
        except ApiException as e:
            logging.error(f"火山云安全组列表调用异常 get_describe_security_group: {self._account_id} -- {e}")

            return None

    def get_describe_security_group_detail(self, security_group_id: str):
        """
        查询安全组详细信息
        https://api.volcengine.com/api-docs/view?serviceCode=vpc&version=2020-04-01&action=DescribeSecurityGroupAttributes
        :return:
        """
        try:
            instances_request = DescribeSecurityGroupAttributesRequest(security_group_id=security_group_id)
            resp = self.api_instance.describe_security_group_attributes(instances_request)
            return resp
        except ApiException as e:
            logging.error(f"火山云安全组详情调用异常 get_describe_security_group_detail: {self._account_id} -- {e}")

            return None

    def handle_data(self, data) -> Dict[str, Any]:
        res: Dict[str, Any] = dict()
        instance_id = data.security_group_id
        res['instance_id'] = instance_id
        res['vpc_id'] = data.vpc_id
        res['security_group_name'] = data.security_group_name
        res['description'] = data.description
        res['region'] = self._region
        res['create_time'] = data.creation_time
        res['security_group_type'] = SecurityGroupTypeMapping.get(data.type, "Unknown")
        res['ref_info'] = dict(items=[])

        # 安全组权限
        detail = self.get_describe_security_group_detail(instance_id)
        items = []
        if detail is not None:
            permissions = detail.permissions
            if permissions:
                for permission in permissions:
                    item = dict()
                    item['security_group_id'] = detail.security_group_id
                    item['ip_protocol'] = permission.protocol
                    item['source_cidr_ip'] = permission.cidr_ip if permission.direction == "ingress" else ""  # 入方向规则设置源地址
                    item['source_group_name'] = ''
                    item['dest_group_name'] = ''
                    item['ipv6_source_cidr_ip'] = ''
                    item['dest_cidr_ip'] = permission.cidr_ip if permission.direction == "egress" else ""  # 出方向规则设置目标地址
                    item['ipv6_dest_cidr_ip'] = ''
                    item['policy'] = permission.policy
                    item['port_range'] = get_port_range(permission.port_start, permission.port_end)
                    item['port_start'] = permission.port_start
                    item['port_end'] = permission.port_end
                    item['description'] = permission.description
                    item['direction'] = permission.direction
                    item['priority'] = permission.priority
                    item['creation_time'] = permission.creation_time
                    items.append(item)

        res['security_info'] = dict(items=items)
        return res

    def get_all_security_group(self) -> List:
        security_groups = []
        try:
            while True:
                data = self.get_describe_security_group()
                if data is None:
                    break
                instances = data.security_groups
                if not instances:
                    break
                security_groups.extend([self.handle_data(data) for data in instances])
                if data.total_count < self.page_size:
                    break
                self.page_number += 1
        except Exception as e:
            logging.error(f"火山云安全组调用异常 get_all_security_group: {self._account_id} -- {e}")
        return security_groups

    def sync_cmdb(self, cloud_name: Optional[str] = 'volc', resource_type: Optional[str] = 'security_group') -> Tuple[
        bool, str]:
        """
        同步CMDB
        :param cloud_name:
        :param resource_type:
        :return:
        """
        all_security_group = self.get_all_security_group()

        if not all_security_group:
            return False, "安全组列表为空"
        # 同步资源
        ret_state, ret_msg = security_group_task(account_id=self._account_id, cloud_name=cloud_name,
                                                 rows=all_security_group)

        # 标记过期
        # mark_expired(resource_type=resource_type, account_id=self._account_id)
        instance_ids = [security_group['instance_id'] for security_group in all_security_group]
        mark_expired_by_sync(cloud_name=cloud_name, account_id=self._account_id, resource_type=resource_type,
                             instance_ids=instance_ids, region=self._region)
        return ret_state, ret_msg


if __name__ == '__main__':
    pass
