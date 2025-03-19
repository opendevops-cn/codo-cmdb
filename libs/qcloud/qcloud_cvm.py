#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date   :  2023/1/27 11:02
Desc   : 腾讯云CVM主机自动发现
"""
import json
import logging
from typing import *
from tencentcloud.common import credential
from tencentcloud.cvm.v20170312 import cvm_client, models
from models.models_utils import server_task, mark_expired


def get_run_type(val):
    run_map = {
        "PENDING": "创建中",
        "LAUNCH_FAILED": "创建失败",
        "RUNNING": "运行中",
        "STOPPED": "关机",
        "STARTING": "开机中",
        "STOPPING": "关机中",
        "REBOOTING": "重启中",
        "SHUTDOWN": "停止待销毁",
        "TERMINATING": "销毁中",
    }
    return run_map.get(val, '未知')


def get_pay_type(val):
    pay_map = {
        "PREPAID": "包年包月",
        "POSTPAID_BY_HOUR": "按量付费"
    }
    return pay_map.get(val, '未知')


class QCloudCVM:
    def __init__(self, access_id: str, access_key: str, region: str, account_id: str):
        self.cloud_name = 'qcloud'
        self._offset = 0  # 偏移量,这里拼接的时候必须是字符串
        self._limit = 100  # 官方默认是20，大于100 需要设置偏移量再次请求：offset=100,offset={机器总数}
        self._region = region
        self._account_id = account_id
        self.__cred = credential.Credential(access_id, access_key)
        self.client = cvm_client.CvmClient(self.__cred, self._region)
        # self.q_network_obj = QCloudNetwork(region=self._region, access_id=access_id, access_key=access_key,
        #                                    account_id=self._account_id)

    def get_all_cvm(self):

        cvm_list = []
        limit = self._limit
        offset = self._offset
        req = models.DescribeInstancesRequest()
        try:
            while True:
                params = {
                    "Offset": offset,
                    "Limit": limit
                }
                req.from_json_string(json.dumps(params))
                resp = self.client.DescribeInstances(req)
                if not resp.InstanceSet:
                    break
                cvm_list.extend(map(self.format_data, resp.InstanceSet))
                offset += self._limit
                if resp.TotalCount < self._limit:
                    break
            return cvm_list
        except Exception as err:
            logging.error(f"腾讯云CVM  get all cvm {self._account_id} {err}")
            return []

    @staticmethod
    def get_os_type(os_name):
        if not os_name:
            return ''
        return 'Windows' if 'windows' in os_name.lower() else 'Linux'

    def format_data(self, data) -> Dict[str, str]:
        """
        处理数据
        :param data:
        :return:
        """
        # 定义返回
        res: Dict[str, str] = dict()

        try:
            vpc_id = '' if not getattr(data.VirtualPrivateCloud, 'VpcId', None) else data.VirtualPrivateCloud.VpcId
            network_type = '经典网络' if not vpc_id else 'vpc'

            res['instance_id'] = data.InstanceId
            res['vpc_id'] = vpc_id
            res['state'] = get_run_type(data.InstanceState)
            res['instance_type'] = data.InstanceType
            res['cpu'] = data.CPU
            res['memory'] = data.Memory
            res['name'] = data.InstanceName
            res['network_type'] = network_type
            res['charge_type'] = get_pay_type(data.InstanceChargeType)

            # 内外网IP,可能有多个
            outer_ip = data.PublicIpAddresses[0] if data.PublicIpAddresses else ''
            inner_ip = data.PrivateIpAddresses[0]
            res['inner_ip'] = inner_ip
            res['outer_ip'] = outer_ip

            res['os_type'] = self.get_os_type(data.OsName)
            res['os_name'] = data.OsName
            res['instance_create_time'] = data.CreatedTime
            res['instance_expired_time'] = data.ExpiredTime
            res['region'] = self._region
            res['zone'] = data.Placement.Zone
            res['security_group_ids'] = data.SecurityGroupIds
        except Exception as err:
            logging.error(f"腾讯云CVM  data format err {self._account_id} {err}")

        # 系统盘和数据盘
        try:
            # system_disk = data.SystemDisk
            # print('系统盘', system_disk, type(system_disk))
            res['system_disk'] = data.SystemDisk.DiskSize  # 系统盘只有一块
        except (IndexError, KeyError, TypeError):
            res['system_disk'] = ""

        try:
            # print('数据盘', data.DataDisks, type(data.DataDisks))
            res['data_disk'] = data.DataDisks[0].DiskSize
        except (IndexError, KeyError, TypeError):
            res['data_disk'] = ""

        return res

    def rename(self, instance_id, instance_name) -> dict:
        """实例改名"""
        result = dict()
        params = {
            "InstanceIds": [instance_id],
            "InstanceName": instance_name
        }
        req = models.ModifyInstancesAttributeRequest()
        req.from_json_string(json.dumps(params))
        try:
            resp = self.client.ModifyInstancesAttribute(req)
            result = {'msg': resp.to_json_string(), 'code': 0}
        except Exception as e:
            result = {'msg': '%s' % e, 'code': -1}
        finally:
            return result

    def get_single_cvm(self, instance_id):
        try:
            params = {
                "InstanceIds": [instance_id]
            }
            req = models.DescribeInstancesRequest()
            req.from_json_string(json.dumps(params))
            resp = self.client.DescribeInstances(req)
            return self.format_data(resp.InstanceSet[0])
        except Exception as err:
            return None

    def sync_server_single(self, instance_id, cloud_name):
        if not instance_id: raise Exception('实例ID不可为空')
        res_data = self.get_single_cvm(instance_id)
        if not res_data: raise Exception(f'未查询到实例{instance_id}')

        network_inface_data = self.q_network_obj.get_single_interface(instance_id)
        res_data.network_attachment = network_inface_data[0] if network_inface_data else None

        server_task(account_id=self._account_id, cloud_name=cloud_name, rows=[res_data])

    def sync_cmdb(self, cloud_name: Optional[str] = 'qcloud', resource_type: Optional[str] = 'server') -> Tuple[
        bool, str]:
        """
        资产信息更新到DB
        :return:
        """
        all_cvm_list: List[dict] = self.get_all_cvm()
        if not all_cvm_list: return False, "CVM列表为空"
        # 更新资源
        ret_state, ret_msg = server_task(account_id=self._account_id, cloud_name=cloud_name, rows=all_cvm_list)
        # 标记过期
        mark_expired(resource_type=resource_type, account_id=self._account_id)

        return ret_state, ret_msg


if __name__ == '__main__':
    pass
