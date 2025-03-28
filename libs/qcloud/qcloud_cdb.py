#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date   :  2023/1/27 11:02
Desc   :  腾讯云CDB自动发现
"""

import json
import logging
from typing import *
from tencentcloud.common import credential
from tencentcloud.cdb.v20170320 import cdb_client, models
from models.models_utils import mark_expired, mysql_task, mark_expired_by_sync


def get_run_type(val):
    """
    #取值来自腾讯云官方Docs:https://cloud.tencent.com/document/api/237/16191#DBInstance
    :param val:
    :return:
    """
    run_map = {
        0: "创建中",
        1: "运行中",
        5: "隔离中"
    }
    return run_map.get(val, '未知')


def get_pay_type(val):
    pay_map = {
        1: "包年包月",
        0: "按量付费"
    }
    return pay_map.get(val, '未知')


class QCloudCDB:
    def __init__(self, access_id: str, access_key: str, region: str, account_id: str):
        self.cloud_name = 'qcloud'
        self._offset = 0  # 偏移量,这里拼接的时候必须是字符串
        self._limit = 100  # 官方默认是20，大于100 需要设置偏移量再次请求：offset=100,offset={机器总数}
        self._region = region
        self._account_id = account_id
        self.__cred = credential.Credential(access_id, access_key)
        self.client = cdb_client.CdbClient(self.__cred, self._region)

    def get_all_cdb(self):

        cdb_list = []
        limit = self._limit
        offset = self._offset
        req = models.DescribeDBInstancesRequest()
        try:
            while True:
                params = {
                    "Offset": offset,
                    "Limit": limit
                }
                req.from_json_string(json.dumps(params))
                resp = self.client.DescribeDBInstances(req)
                if not resp.Items:
                    break
                cdb_list.extend(map(self.format_data, resp.Items))
                offset += self._limit
                if resp.TotalCount < self._limit:
                    break
            return cdb_list
        except Exception as err:
            logging.error(f"腾讯云CDB  get all cdb {self._account_id} {err}")
            return []

    @staticmethod
    def format_data(data) -> Dict[str, Any]:
        """
        处理数据
        :param data:
        :return:
        """
        # 定义返回
        res: Dict[str, Any] = dict()

        vpc_id = data.UniqVpcId
        network_type = '经典网络' if not vpc_id else '专有网络'
        res['instance_id'] = data.InstanceId
        res['vpc_id'] = vpc_id

        res['create_time'] = data.CreateTime
        res['network_type'] = network_type
        res['charge_type'] = get_pay_type(data.PayType)
        res['region'] = data.Region
        res['zone'] = data.Zone

        res['name'] = data.InstanceName
        res['state'] = get_run_type(data.Status)
        # 腾讯云CDB没有实例类型
        # res['db_class'] = '{cpu}C/{memory}G/{disk}G'.format(cpu=data.Cpu, memory=(int(data.Memory / 1000)),
        #                                                     disk=data.Volume)
        res['db_class'] = f"{data.Cpu}C/{(int(data.Memory / 1000))}G/{data.Volume}G"
        res['db_engine'] = 'MySQL'
        res['db_version'] = data.EngineVersion
        # 地址,存JSON主要是为了适配其他云格式一致
        res['db_address'] = {
            "items": [
                {
                    "endpoint_type": "Primary",
                    "type": "private",
                    "port": str(data.Vport),
                    "ip": data.Vip,
                    "domain": "",
                },
                {
                    "endpoint_type": "Primary",
                    "type": "public",
                    "port": str(data.WanPort),
                    "ip": "",
                    "domain": data.WanDomain,
                },
            ]
        }
        return res

    def sync_cmdb(self, cloud_name: Optional[str] = 'qcloud', resource_type: Optional[str] = 'mysql') -> Tuple[
        bool, str]:
        """
        资产信息更新到DB
        :return:
        """
        all_cdb_list: List[dict] = self.get_all_cdb()
        if not all_cdb_list: return False, "CDB列表为空"
        # 更新资源
        ret_state, ret_msg = mysql_task(account_id=self._account_id, cloud_name=cloud_name, rows=all_cdb_list)
        # 标记过期
        # mark_expired(resource_type=resource_type, account_id=self._account_id)
        instance_ids = [cdb['instance_id'] for cdb in all_cdb_list]
        mark_expired_by_sync(cloud_name=cloud_name, account_id=self._account_id, resource_type=resource_type,
                             instance_ids=instance_ids, region=self._region)

        return ret_state, ret_msg


# class QcloudCDBClient:
#     def __init__(self, access_id: str, access_key: str, region: str, account_id):
#         self._offset = '0'  # 偏移量,这里拼接的时候必须是字符串
#         self._limit = '100'  # 官方默认是20，大于100 需要设置偏移量再次请求：offset=100,offset={实例总数}
#         self._access_id = access_id
#         self._access_key = access_key
#         self._region = region
#         self._accountID = account_id
#
#     def get_cdb_url(self) -> Union[str]:
#         """
#         获取腾讯云机器的API拼接结果，get请求
#         :return:
#         """
#         api_url = 'cdb.tencentcloudapi.com/?'
#         keydict = {
#             # 公共参数部分
#             'Timestamp': str(int(time.time())),
#             'Nonce': str(int(random.random() * 1000)),
#             'Region': self._region,
#             'SecretId': self._access_id,
#             'Version': '2017-03-20',
#             # 'SignatureMethod': SignatureMethod,
#             # 接口参数部分
#             'Action': 'DescribeDBInstances',
#             'Offset': self._offset,  # 超过100 需要用到偏移量
#             'Limit': self._limit,
#         }
#         result_url = QcloudApiOper.run(keydict, api_url, self._access_key)
#         return result_url
#
#     def get_result_data(self) -> Tuple[bool, List[dict], int]:
#         """
#         获取返回的数据
#         :return:
#         """
#         result_url = self.get_cdb_url()
#         response = requests.get(result_url)
#         result_data = json.loads(response.text)
#         if result_data['Response'].get('Error'):
#             return False, result_data['Response'], 0
#         # 状态、数据List、ToTal
#         return True, result_data['Response']['Items'], result_data['Response']['TotalCount']
#
#     @staticmethod
#     def format_data(data) -> Dict[str, Any]:
#         """
#         处理数据
#         :param data:
#         :return:
#         """
#         if not isinstance(data, dict):
#             raise TypeError
#
#         # 定义返回
#         res: Dict[str, Any] = {}
#         res['instance_id'] = data.get('InstanceId')
#         res['create_time'] = data.get('CreateTime')
#         res['charge_type'] = get_paymeny_type(data.get('PayType'))
#         res['region'] = data.get('Region')
#         res['zone'] = data.get('Zone')
#
#         res['name'] = data.get('InstanceName')
#         res['state'] = get_run_type(data.get('Status'))
#         # 腾讯云CDB没有实例类型
#         res['db_class'] = '{cpu}C/{memory}G/{disk}G'.format(cpu=data.get('Cpu'),
#                                                             memory=(int(data.get('Memory') / 1000)),
#                                                             disk=data.get('Volume'))
#         res['db_engine'] = 'MySQL'
#         res['db_version'] = data.get('EngineVersion')
#         res['db_version'] = data.get('EngineVersion')
#         # 地址,存JSON主要是为了适配其他云格式一致
#         res['db_address'] = {
#             "items": [
#                 {
#                     "endpoint_type": "Primary",
#                     "type": "private",
#                     "port": data.get('Vport'),
#                     "ip": data.get('Vip'),
#                     "domain": "",
#                 },
#                 {
#                     "endpoint_type": "Primary",
#                     "type": "public",
#                     "port": data.get('WanPort'),
#                     "ip": "",
#                     "domain": data.get('WanDomain'),
#                 },
#             ]
#         }
#         return res
#
#     def get_all_cdb(self) -> List[dict]:
#         # 定义返回
#         all_cdb_list: List[dict] = []
#         is_success, result, host_total = self.get_result_data()
#         if not is_success:
#             logging.error(f'get cbd failed :{result}')
#             return []
#         logging.info(f'{self._region} cdb total is : {host_total}')
#         # 数量超过100需要分页
#         for c in range(0, host_total, 100):
#             self._offset = str(c)
#             if (c + 100) > host_total:
#                 self._limit = str(host_total)
#             else:
#                 self._limit = str(c + 100)
#             db_list = map(self.format_data, result)
#             all_cdb_list.extend(db_list)
#         return all_cdb_list
#
#     def sync_cmdb(self, cloud_name: Optional[str] = 'qcloud', resource_type: Optional[str] = 'mysql') -> Tuple[
#         bool, str]:
#         """
#         资产信息更新到DB
#         :return:
#         """
#         all_cdb_list: List[dict] = self.get_all_cdb()
#         if not all_cdb_list: return False, "CDB列表为空"
#         # 更新资源
#         ret_state, ret_msg = mysql_task(account_id=self._accountID, cloud_name=cloud_name, rows=all_cdb_list)
#         # 标记过期
#         mark_expired(resource_type=resource_type, account_id=self._accountID)
#
#         return ret_state, ret_msg


if __name__ == '__main__':
    pass
