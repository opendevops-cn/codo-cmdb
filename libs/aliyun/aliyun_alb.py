#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author: shenshuo
Date  : 2023/2/25
Desc  : 获取阿里云ALB资产信息
"""

import json
import logging
from typing import List, Tuple, Dict, Any, Optional
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.auth.credentials import AccessKeyCredential
from aliyunsdkalb.request.v20200616.ListLoadBalancersRequest import ListLoadBalancersRequest
from models.models_utils import lb_task, mark_expired, mark_expired_by_sync


def get_run_status(val):
    return {
        "Inactive": "已停止",
        "Active": "运行中",
        "Provisioning": "创建中",
        "Configuring": "变配中",
        "CreateFailed": "创建失败",
    }.get(val, "未知")


def get_endpoint_type(val):
    return {"Internet": "公网", "Intranet": "内网"}.get(val, "未知")


def get_internet_charge_type(val):
    return {"paybybandwidth": "带宽计费", "paybytraffic": "流量计费"}.get(val, "未知")


def get_pay_type(val):
    return {"PayOnDemand": "按量付费", "PrePay": "包年包月"}.get(val, "未知")


def get_business_status(val):
    return {"Abnormal": "异常", "Normal": "正常"}.get(val, "未知")


class AliyunALbClient:
    def __init__(self, access_id: str, access_key: str, region: str, account_id: str):
        self.NextToken = ""  # 分页查询参数 第一次取值无需填写，如果还有资源继续查询则取第一次查询NextToken的值
        self.MaxResults = 100
        self._access_id = access_id
        self._access_key = access_key
        self._region = region
        self._account_id = account_id
        self.__client = self._create_client()

    def _create_client(self) -> AcsClient:
        credentials = AccessKeyCredential(self._access_id, self._access_key)
        return AcsClient(region_id=self._region, credential=credentials)

    def get_alb_response(self) -> Tuple[bool, str, dict]:
        """
        获取应用型负载均衡
        :return:
        """
        ret_state, ret_msg, ret_date = True, "获取Response成功", {}
        try:
            request = ListLoadBalancersRequest()
            request.set_accept_format("json")
            request.set_MaxResults(self.MaxResults)
            request.set_NextToken(self.NextToken)
            response = self.__client.do_action_with_exception(request)
            ret_date = json.loads(str(response, encoding="utf8"))
        except Exception as error:
            ret_state, ret_msg, ret_date = True, error, {}
        return ret_state, ret_msg, ret_date

    def get_all_alb(self) -> List[Dict[str, Any]]:
        """
        获取所有的应用负载均衡 ALB
        :return:
        """
        all_alb_list: List = []
        while True:
            is_success, msg, response = self.get_alb_response()
            if not is_success or not response:
                logging.error(msg)
                break
            if "LoadBalancers" not in response:
                logging.error(msg)
                break
            rows = response["LoadBalancers"]
            if not rows:
                break
            for row in rows:
                data = self.format_alb_data(row)
                all_alb_list.append(data)
            # 继续下一次查询
            if "NextToken" not in response:
                break
            self.NextToken = response["NextToken"]
        return all_alb_list

    def format_alb_data(self, row: dict, type: Optional[str] = "alb") -> Dict[str, Any]:
        """
        处理下需要入库的数据
        :param type:
        :param row:
        :return:
        """
        # 定义返回
        res: Dict[str, Any] = dict()
        # print(row)
        res["type"] = type  # slb or alb
        res["name"] = row.get("LoadBalancerName")
        res["instance_id"] = row.get("LoadBalancerId")
        res["create_time"] = row.get("CreateTime")
        res["region"] = self._region
        res["zone"] = ""
        res["status"] = get_run_status(row.get("LoadBalancerStatus"))
        res["dns_name"] = row.get("DNSName")
        res["endpoint_type"] = get_endpoint_type(row.get("AddressType"))
        res["ext_info"] = {
            "vpc_id": row.get("VpcId"),
            "business_status": get_business_status(row.get("LoadBalancerBussinessStatus")),
        }
        return res

    def sync_cmdb(self, cloud_name: Optional[str] = "aliyun", resource_type: Optional[str] = "lb") -> Tuple[bool, str]:
        """
        同步CMDB
        """
        all_alb_list: List[Dict[str, Any]] = self.get_all_alb()
        if not all_alb_list:
            return False, "ALB列表为空"
        # 同步资源
        ret_state, ret_msg = lb_task(account_id=self._account_id, cloud_name=cloud_name, rows=all_alb_list)

        # 标记过期
        # mark_expired(resource_type=resource_type, account_id=self._account_id)
        instance_ids = [row["instance_id"] for row in all_alb_list]
        mark_expired_by_sync(cloud_name=cloud_name, account_id=self._account_id, resource_type=resource_type,
                             instance_ids=instance_ids, region=self._region)

        return ret_state, ret_msg


if __name__ == "__main__":
    pass
