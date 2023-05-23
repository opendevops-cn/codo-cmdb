#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date   : 2023/1/27 11:02
Desc   : 阿里云 PolarDB
"""

import json
import logging
from typing import *
from models.models_utils import mysql_task, mark_expired
from aliyunsdkcore.client import AcsClient
from aliyunsdkpolardb.request.v20170801.DescribeDBClustersRequest import DescribeDBClustersRequest
from aliyunsdkpolardb.request.v20170801.DescribeDBClusterEndpointsRequest import DescribeDBClusterEndpointsRequest


def get_run_type(val):
    run_map = {
        "Creating": "创建中",
        "Running": "运行中",
        "Deleted": "已释放",
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


# 转换type
def get_type(val):
    type_map = {
        "Public": "public",
        "Private": "private",
        "Inner": "private",
    }
    return type_map.get(val, val)


class AliyunPolarDBClient:
    def __init__(self, access_id: Optional[str], access_key: Optional[str], region: Optional[str],
                 account_id: Optional[str]):
        self.page_number = 1  # 实例状态列表的页码。起始值：1 默认值：1
        self.page_size = 100  # 分页查询时设置的每页行数。最大值：100 默认值：10
        self._access_id = access_id
        self._access_key = access_key
        self._region = region
        self._accountID = account_id
        self.__client = self._create_client()

    def _create_client(self) -> AcsClient:
        client = AcsClient(self._access_id, self._access_key, self._region)
        return client

    def get_polardb_response(self) -> Tuple[bool, dict]:
        """
        获取PolarDB集群Response
        :return:
        """
        try:
            request = DescribeDBClustersRequest()
            request.set_accept_format('json')
            request.set_PageSize(self.page_size)
            request.set_PageNumber(self.page_number)
            response = self.__client.do_action_with_exception(request)
            response = json.loads(str(response, encoding="utf8"))
        except Exception as err:
            logging.error(f'get polardb response error: {err}')
            return False, {}
        return True, response

    def get_all_polardb(self) -> List[dict]:
        """
        获取所有的PolarDB集群信息
        :return:
        """
        self.page_number = 1

        all_polardb_instance: List[Dict] = []
        while True:
            is_success, response = self.get_polardb_response()
            if not is_success or not response: break
            if 'Items' not in response: break
            self.page_number += 1
            total_polardb = response['TotalRecordCount']
            logging.info(f'aliyun  {self._region} polardb total is: {total_polardb}')
            rows = response['Items']['DBCluster']
            if not rows: break
            for data in rows:
                polardb_data = self._format_data(data)
                all_polardb_instance.append(polardb_data)

        return all_polardb_instance

    def get_polardb_endpoints(self, instance_id) -> Dict[str, List[Dict]]:
        """
        调用DescribeDBClusterEndpoints接口查询PolarDB集群的地址信息。
        :return:
        """
        request = DescribeDBClusterEndpointsRequest()
        request.set_accept_format('json')
        request.set_DBClusterId(instance_id)
        response = self.__client.do_action_with_exception(request)
        response = json.loads(str(response, encoding="utf8"))
        endpoints = response['Items']

        # 映射关系
        mapping = {
            "port": "Port",
            "ip": "IPAddress",
            "domain": "ConnectionString",
            "type": "NetType"
        }
        # 定义address
        db_address: Dict[str, List[Dict]] = {"items": []}

        for _endpoint in endpoints:
            endpoint_type = _endpoint['EndpointType']
            db_address['items'].extend([
                {

                    **{"endpoint_type": endpoint_type},
                    **{
                        k: get_type(data[v])
                        for k, v in mapping.items()
                    }
                }
                for data in _endpoint['AddressItems']
            ])

        return db_address

    def _format_data(self, data: Optional[Dict]) -> Dict[str, Any]:
        res: Dict[str, Any] = {}
        res['instance_id'] = data.get('DBClusterId')
        res['create_time'] = data.get('CreateTime')
        res['charge_type'] = get_paymeny_type(data.get('PayType'))
        res['region'] = data.get('RegionId')
        res['zone'] = data.get('ZoneId')
        res['name'] = data.get('DBClusterDescription')
        res['db_class'] = data.get('DBNodeClass')
        res['db_engine'] = data.get('Engine')
        res['db_version'] = data.get('DBVersion')
        res['state'] = get_run_type(data.get('DBClusterStatus'))
        res['network_type'] = get_network_type(data.get('DBClusterNetworkType'))
        res['db_address'] = self.get_polardb_endpoints(data.get('DBClusterId'))
        # res['db_address'] = self.get_db_endpoints(data.get('DBInstanceId'))
        # logging.info(f'PolarDB Instance: {res}')
        return res

    def sync_cmdb(self, cloud_name: Optional[str] = 'aliyun', resource_type: Optional[str] = 'mysql') -> Tuple[
        bool, str]:

        # 所有PolarDB信息
        all_polardb_list: List[dict] = self.get_all_polardb()
        if not all_polardb_list: return False, "PolarDB列表为空"
        # 更新资源
        ret_state, ret_msg = mysql_task(account_id=self._accountID, cloud_name=cloud_name, rows=all_polardb_list)
        # 标记过期
        mark_expired(resource_type=resource_type, account_id=self._accountID)

        return ret_state, ret_msg


if __name__ == '__main__':
    pass
