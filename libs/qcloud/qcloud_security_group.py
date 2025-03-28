#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2020/1/6 17:51
Desc    : 腾讯云安全组
"""

import json
import logging
from typing import *
from tencentcloud.common import credential
from tencentcloud.vpc.v20170312 import vpc_client, models
from models.models_utils import security_group_task, mark_expired, mark_expired_by_sync


class QCloudSecurityGroup:
    def __init__(self, access_id: str, access_key: str, region: str, account_id):
        self._region = region
        self._offset = 0  # 偏移量,这里拼接的时候必须是字符串
        self._limit = 100  # 官方默认是20，大于100 需要设置偏移量再次请求
        self._account_id = account_id
        self.__cred = credential.Credential(access_id, access_key)
        self.client = vpc_client.VpcClient(self.__cred, self._region)

    def get_all_security_group(self):
        security_group_list = []
        limit = self._limit
        offset = self._offset
        req = models.DescribeSecurityGroupsRequest()
        try:
            while True:
                params = {
                    "Offset": str(offset),
                    "Limit": str(limit)
                }
                req.from_json_string(json.dumps(params))
                resp = self.client.DescribeSecurityGroups(req)
                if not resp.SecurityGroupSet:
                    break
                security_group_list.extend(map(self.format_data, resp.SecurityGroupSet))
                offset += limit
            return security_group_list
        except Exception as err:
            logging.error(f"腾讯云安全组 {self._account_id} {err}")
            return []

    def format_data(self, data) -> Dict[str, Any]:
        res: Dict[str, Any] = dict()
        instance_id = data.SecurityGroupId
        res['instance_id'] = instance_id
        res['vpc_id'] = ''
        res['security_group_name'] = data.SecurityGroupName
        res['description'] = data.SecurityGroupDesc
        res['region'] = self._region
        res['create_time'] = data.CreatedTime

        # 获取规则
        info_list = []
        try:
            policies = self.get_security_group_policies(instance_id)
            for obj_egress in policies.Egress:
                obj_egress.Direction = 'Egress'
                info_list.append(self.format_data_policies(obj_egress, instance_id))
            for obj_ingress in policies.Ingress:
                obj_ingress.Direction = 'Ingress'
                info_list.append(self.format_data_policies(obj_ingress, instance_id))
        except Exception as err:
            logging.error(f"腾讯云安全组 获取规则 {self._account_id} {err}")

        # 获取关联
        ref_list = []
        try:
            security_group_references = self.get_security_group_refs(instance_id)
            if not security_group_references or not isinstance(security_group_references, list): ref_list = []

            for references in security_group_references:
                if references and references.ReferredSecurityGroupIds:
                    ref_list = references.ReferredSecurityGroupIds

        except Exception as err:
            logging.error(f"腾讯云安全组 获取关联 {self._account_id} {err}")

        res['ref_info'] = dict(items=ref_list)
        res['security_info'] = dict(items=info_list)
        return res

    def format_data_policies(self, data, security_group_id) -> Dict[str, Any]:
        res: Dict[str, Any] = dict()

        try:
            res['security_group_id'] = security_group_id
            res['ip_protocol'] = data.Protocol
            res['source_cidr_ip'] = data.CidrBlock if data.Direction == 'Ingress' else ''
            res['source_group_name'] = ''
            res['dest_group_name'] = ''
            res['ipv6_source_cidr_ip'] = data.Ipv6CidrBlock if data.Direction == 'Ingress' else ''
            res['dest_cidr_ip'] = data.CidrBlock if data.Direction == 'Egress' else ''
            res['ipv6_dest_cidr_ip'] = data.Ipv6CidrBlock if data.Direction == 'Egress' else ''
            res['policy'] = data.Action
            res['port_range'] = data.Port
            res['description'] = data.PolicyDescription
            res['direction'] = 'egress' if data.Direction == 'Egress' else 'ingress'
            res['priority'] = data.PolicyIndex
            res['creation_time'] = data.ModifyTime

        except Exception as err:
            logging.error(f"腾讯云安全组 format_data_policies {self._account_id} {err}")
        return res

    def get_security_group_policies(self, security_group_id):
        try:
            req = models.DescribeSecurityGroupPoliciesRequest()
            params = {
                "SecurityGroupId": security_group_id
            }
            req.from_json_string(json.dumps(params))
            resp = self.client.DescribeSecurityGroupPolicies(req)
            return resp.SecurityGroupPolicySet
        except Exception as err:
            logging.error(f"腾讯云安全组 policies {self._account_id} {err}")
            return {}

    def get_security_group_refs(self, security_group_id):
        try:
            req = models.DescribeSecurityGroupReferencesRequest()
            params = {
                "SecurityGroupIds": [security_group_id]
            }
            req.from_json_string(json.dumps(params))
            resp = self.client.DescribeSecurityGroupReferences(req)
            return resp.ReferredSecurityGroupSet
        except Exception as err:
            logging.error(f"腾讯云安全组 refs {self._account_id} {err}")
            return []

    def sync_cmdb(self, cloud_name: Optional[str] = 'qcloud', resource_type: Optional[str] = 'security_group') -> Tuple[
        bool, str]:
        """
        同步CMDB
        """

        all_security_group: List[list, Any, None] = self.get_all_security_group()

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
