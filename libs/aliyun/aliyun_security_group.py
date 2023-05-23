#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/1/27 11:02
Desc    : 阿里云安全组
"""

import json
import logging
from typing import *
from aliyunsdkcore.client import AcsClient
from aliyunsdkecs.request.v20140526.DescribeSecurityGroupsRequest import DescribeSecurityGroupsRequest
from aliyunsdkecs.request.v20140526.DescribeSecurityGroupAttributeRequest import DescribeSecurityGroupAttributeRequest
from aliyunsdkecs.request.v20140526.DescribeSecurityGroupReferencesRequest import DescribeSecurityGroupReferencesRequest
from models.models_utils import security_group_task, mark_expired


class AliyunSecurityGroup:
    def __init__(self, access_id: str, access_key: str, region: str, account_id: str):
        self.page_number = 1  # 实例状态列表的页码。起始值：1 默认值：1
        self.page_size = 100  # 分页查询时设置的每页行数。最大值：100 默认值：10
        self._region = region
        self._account_id = account_id
        self.__client = AcsClient(access_id, access_key, self._region)

    def get_security_group(self, page_number=1) -> Union[None, dict]:
        try:
            request = DescribeSecurityGroupsRequest()
            request.set_accept_format('json')
            request.set_PageNumber(page_number)
            request.set_PageSize(self.page_size)
            response = self.__client.do_action_with_exception(request)
            return json.loads(str(response, encoding="utf8"))['SecurityGroups']
        except Exception as err:
            logging.error(f'获取阿里云安全组失败:{err}')
            return None

    def get_all_security_group(self):
        page_num = 1
        try:
            while True:
                data = self.get_security_group(page_num)
                if not data or 'SecurityGroup' not in data: break
                if not data['SecurityGroup']: break
                page_num += 1
                row = data['SecurityGroup']
                if not row: break
                yield map(self.format_data, row)
        except Exception as err:
            logging.error(f'获取阿里云安全组失败:{err}')
            return []

    def get_security_group_policies(self, security_group_id) -> Union[None, dict]:
        try:
            request = DescribeSecurityGroupAttributeRequest()
            request.set_accept_format('json')
            request.set_SecurityGroupId(security_group_id)
            response = self.__client.do_action_with_exception(request)
            return json.loads(str(response, encoding="utf8"))['Permissions']['Permission']
        except Exception as err:
            logging.error(f'获取阿里云安全组详情失败:{err}')
            return None

    def get_security_group_refs(self, security_group_id) -> Union[None, dict]:
        try:
            request = DescribeSecurityGroupReferencesRequest()
            request.set_accept_format('json')
            request.set_SecurityGroupIds([security_group_id])
            response = self.__client.do_action_with_exception(request)
            # print(json.loads(str(response, encoding="utf8")))
            return json.loads(str(response, encoding="utf8"))['SecurityGroupReferences']['SecurityGroupReference']
        except Exception as err:
            logging.error(f'获取阿里云 安全组关联失败:{err}')
            return None

    def format_data(self, data: Optional[dict]) -> Dict[str, Any]:
        """
        处理数据
        :param data:
        :return:
        """
        # 定义返回
        res: Dict[str, Any] = dict()
        instance_id = data.get('SecurityGroupId')
        res['instance_id'] = instance_id
        res['security_group_name'] = data.get('SecurityGroupName')
        res['description'] = data.get('Description')
        res['region'] = self._region
        res['vpc_id'] = data.get('VpcId')
        res['security_group_type'] = data.get('SecurityGroupType')

        # 获取规则
        info_list = []
        try:
            for attribute in self.get_security_group_policies(instance_id):
                info_list.append(self.format_data_policies(attribute, instance_id))
        except Exception as err:
            logging.error(f"阿里云安全组获取规则 {self._account_id} {err}")

        # 获取关联
        ref_list = []
        try:
            security_group_references = self.get_security_group_refs(instance_id)
            if not security_group_references or not isinstance(security_group_references, list): ref_list = []

            for references in security_group_references:
                if references and references['ReferencingSecurityGroups']:
                    rg_list = references['ReferencingSecurityGroups']['ReferencingSecurityGroup']
                    ref_list = [i['SecurityGroupId'] for i in rg_list]

        except Exception as err:
            logging.error(f"阿里云安全组 获取关联 {self._account_id} {err}")

        res['ref_info'] = dict(items=ref_list)
        res['security_info'] = dict(items=info_list)
        return res

    def format_data_policies(self, data, security_group_id) -> Dict[str, Any]:
        res: Dict[str, Any] = dict()

        try:
            res['security_group_id'] = security_group_id
            res['dest_cidr_ip'] = data.get('DestCidrIp')
            res['dest_group_id'] = data.get('DestGroupId')
            res['dest_group_name'] = data.get('DestGroupName')
            res['dest_group_owner_account'] = data.get('DestGroupOwnerAccount')
            res['direction'] = data.get('Direction')
            res['ip_protocol'] = data.get('IpProtocol')
            res['ipv6_dest_cidr_ip'] = data.get('Ipv6DestCidrIp')
            res['ipv6_source_cidr_ip'] = data.get('Ipv6SourceCidrIp')
            res['nic_type'] = data.get('NicType')
            res['policy'] = data.get('Policy')
            res['port_range'] = data.get('PortRange')
            res['priority'] = data.get('Priority')
            res['source_cidr_ip'] = data.get('SourceCidrIp')
            res['source_group_id'] = data.get('SourceGroupId')
            res['source_group_name'] = data.get('SourceGroupName')
            res['source_port_range'] = data.get('SourcePortRange')
            res['source_group_owner_account'] = data.get('SourceGroupOwnerAccount')
            res['description'] = data.get('Description')
            res['creation_time'] = data.get('CreateTime')

        except Exception as err:
            logging.error(f"阿里云安全组 format_data_policies {self._account_id} {err}")
        return res

    def sync_cmdb(self, cloud_name: Optional[str] = 'aliyun', resource_type: Optional[str] = 'security_group') -> Tuple[
        bool, str]:
        """
        同步CMDB
        :return:
        """
        # 所有的ECS对象，是一个迭代器
        all_sg: Generator[map] = self.get_all_security_group()
        # 处理到一个List里面
        all_security_group: List[dict] = []
        for _server_map in all_sg:
            all_security_group.extend(list(_server_map))

        if not all_security_group: return False, "安全组列表为空"
        # 更新资源
        ret_state, ret_msg = security_group_task(account_id=self._account_id, cloud_name=cloud_name,
                                                 rows=all_security_group)
        # 标记过期
        mark_expired(resource_type=resource_type, account_id=self._account_id)

        return ret_state, ret_msg
