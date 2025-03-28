#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date   : 2023/1/27 11:02
Desc   : 阿里云 RDS
"""

import json
import logging
from typing import *
from models.models_utils import mark_expired, mysql_task, mark_expired_by_sync
from aliyunsdkcore.client import AcsClient
from aliyunsdkrds.request.v20140815.DescribeDBInstancesRequest import DescribeDBInstancesRequest
from aliyunsdkrds.request.v20140815.DescribeDBInstanceAttributeRequest import DescribeDBInstanceAttributeRequest
from aliyunsdkrds.request.v20140815.DescribeDBInstanceNetInfoRequest import DescribeDBInstanceNetInfoRequest


def get_run_type(val):
    run_map = {
        "Creating": "创建中",
        "Running": "运行中",
        "Released": "已释放",
    }
    return run_map.get(val, '未知')


def get_paymeny_type(val):
    pay_map = {
        "Prepaid": "包年包月",
        "Postpaid": "按量付费"
    }
    return pay_map.get(val, '未知')


def get_network_type(val):
    network_map = {
        "Classic": "经典网络",
        "VPC": "专有网络"
    }
    return network_map.get(val, '未知')


class AliyunRDSClient:
    def __init__(self, access_id: Optional[str], access_key: Optional[str], region: Optional[str],
                 account_id: Optional[str]):
        self.page_number = 1  # 实例状态列表的页码。起始值：1 默认值：1
        self.page_size = 100  # 分页查询时设置的每页行数。最大值：100 默认值：10
        self._access_id = access_id
        self._access_key = access_key
        self._region = region
        self._accountID = account_id
        self.__client = AcsClient(self._access_id, self._access_key, self._region)

    def get_db_response(self) -> Tuple[bool, dict]:
        """
        获取RDS详情
        :return:
        """
        try:
            request = DescribeDBInstancesRequest()
            request.set_PageNumber(self.page_number)
            request.set_PageSize(self.page_size)
            response = self.__client.do_action_with_exception(request)
            response = json.loads(str(response, encoding="utf8"))
        except Exception as err:
            logging.error(f'get rds instances error:{err}')
            return False, {}
        return True, response

    def get_rds_instance_id(self) -> List[str]:
        """
        获取所有RDS InstanceID
        :return:
        """

        self.page_number = 1
        all_instance_id_list: List[str] = []
        while True:
            is_success, response = self.get_db_response()
            if not is_success: break
            if 'Items' not in response: break
            self.page_number += 1
            rows = response['Items']['DBInstance']
            if not rows: break
            db_instances = [i.get('DBInstanceId') for i in rows]
            all_instance_id_list.extend(db_instances)
        return all_instance_id_list

    def get_db_endpoints(self, instance_id: Optional[str]) -> Dict[str, List[dict]]:
        """
        调用DescribeDBInstanceNetInfo接口查询实例的所有连接地址信息
        :param instance_id:
        :return:
        """
        request = DescribeDBInstanceNetInfoRequest()
        request.set_accept_format('json')
        request.set_DBInstanceId(instance_id)
        response = self.__client.do_action_with_exception(request)
        response = json.loads(str(response, encoding="utf8"))
        endpoints = response['DBInstanceNetInfos']['DBInstanceNetInfo']
        inner_address = {
            "endpoint_type": "Primary",
            "type": "private",
            "port": "",
            "ip": "",
            "domain": "",
        }
        outer_address = {
            "endpoint_type": "Primary",
            "type": "public",
            "port": "",
            "ip": "",
            "domain": "",
        }
        for _endpoint in endpoints:
            if _endpoint['IPType'] == 'Inner':
                inner_address['port'] = str(_endpoint.get('Port'))
                inner_address['ip'] = _endpoint.get('IPAddress')
                inner_address['domain'] = _endpoint.get('ConnectionString')
            else:
                outer_address['port'] = str(_endpoint.get('Port'))
                outer_address['ip'] = _endpoint.get('IPAddress')
                outer_address['domain'] = _endpoint.get('ConnectionString')
        db_address: Dict[str, List[Dict]] = {"items": []}
        db_address['items'].append(inner_address)
        db_address['items'].append(outer_address)

        return db_address

    def _format_data(self, data: Optional[Dict]) -> Dict[str, Any]:
        """
        只提取需要入库的数据
        :param data:
        :return:
        """
        res: Dict[str, Any] = dict()

        res['instance_id'] = data.get('DBInstanceId')
        res['create_time'] = data.get('CreationTime')
        res['charge_type'] = get_paymeny_type(data.get('PayType'))
        res['region'] = data.get('RegionId')
        res['zone'] = data.get('ZoneId')
        res['name'] = data.get('DBInstanceDescription')
        res['db_class'] = data.get('DBInstanceClass')
        res['db_engine'] = data.get('Engine')
        res['db_version'] = data.get('EngineVersion')
        res['state'] = get_run_type(data.get('DBInstanceStatus'))
        res['network_type'] = get_network_type(data.get('InstanceNetworkType'))
        res['db_address'] = self.get_db_endpoints(data.get('DBInstanceId'))
        return res

    def get_rds_attribute(self) -> List[Dict[str, Any]]:
        """
        获取RDS详细数据
        :return:
        """

        all_instances = self.get_rds_instance_id()
        if not all_instances: return []

        rds_data_list: List[Dict[str]] = []
        request = DescribeDBInstanceAttributeRequest()
        request.set_accept_format('json')

        for _instance_id in all_instances:
            request.set_DBInstanceId(_instance_id)
            response = self.__client.do_action_with_exception(request)
            response = json.loads(str(response, encoding="utf8"))
            rds_data = response['Items']['DBInstanceAttribute'][0]
            format_data = self._format_data(rds_data)
            rds_data_list.append(format_data)

        return rds_data_list

    def sync_cmdb(self, cloud_name: Optional[str] = 'aliyun', resource_type: Optional[str] = 'mysql') -> Tuple[
        bool, str]:
        # 获取数据
        all_rds_list: List[dict] = self.get_rds_attribute()
        if not all_rds_list: return False, "RDS列表为空"
        # 更新资源
        ret_state, ret_msg = mysql_task(account_id=self._accountID, cloud_name=cloud_name, rows=all_rds_list)
        # 标记过期
        # mark_expired(resource_type=resource_type, account_id=self._accountID)
        instance_ids = [row['instance_id'] for row in all_rds_list]
        mark_expired_by_sync(cloud_name=cloud_name, account_id=self._accountID, resource_type=resource_type,
                             instance_ids=instance_ids, region=self._region)

        return ret_state, ret_msg


if __name__ == '__main__':
    pass
