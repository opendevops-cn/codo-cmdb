#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023年4月7日
Desc    : 腾讯云Events主动运维事件（CVM）
"""

import json
import datetime
from typing import *
from tencentcloud.common import credential
from tencentcloud.cvm.v20170312 import cvm_client, models
from websdk2.db_context import DBContext
from models.asset import AssetServerModels
from models.models_utils import cloud_event_task


def cvm_event_status(val):
    mapping = {
        1: "待授权",
        2: "处理中",
        3: "已结束",
        4: "已预约",
        5: "已取消",
        6: "已避免"
    }
    return mapping.get(val, val)


class QCloudEventClient:
    def __init__(self, access_id: Optional[str], access_key: Optional[str], region: Optional[str],
                 account_id: Optional[str]):
        self._access_id = access_id
        self._access_key = access_key
        self._region = region
        self._account_id = account_id
        cred = credential.Credential(access_id, access_key)
        # 实例化一个http选项，可选的，没有特殊需求可以跳过
        self.__client = cvm_client.CvmClient(cred, "ap-guangzhou")  # 不区分region

    def get_cvm_events(self) -> List[Dict[str, Any]]:
        """
        调用DescribeTaskInfoRequest查询实例的系统事件信息
        :return:
        """
        req = models.DescribeTaskInfoRequest()
        start_date = datetime.date.today() - datetime.timedelta(days=15)
        end_date = datetime.date.today() + datetime.timedelta(days=2)
        params = {
            "Limit": 100,
            "Offset": 0,
            "StartDate": start_date.strftime('%Y-%m-%d %H:%M:%S'),
            "EndDate": end_date.strftime('%Y-%m-%d %H:%M:%S')
        }
        req.from_json_string(json.dumps(params))

        # 返回的resp是一个DescribeTaskInfoResponse的实例，与请求对象对应
        resp = self.__client.DescribeTaskInfo(req)
        # 输出json格式的字符串回包
        res_list = resp.RepairTaskInfoSet

        if not res_list: return []
        return list(map(self._cvm_format, res_list))

    def _cvm_format(self, data) -> Dict[str, Any]:
        res: Dict[str, Any] = dict()

        _default_service = 'server'
        instance_id = data.InstanceId
        res["event_id"] = data.TaskId
        res["event_service"] = _default_service
        res["event_type"] = data.TaskTypeName
        res['event_status'] = cvm_event_status(data.TaskStatus)
        res['event_instance_id'] = instance_id
        res['event_instance_name'] = self._get_instance_name(_default_service, instance_id)
        res['event_start_time'] = data.CreateTime
        res['event_end_time'] = data.EndTime
        res['event_detail'] = data.TaskDetail
        res['region'] = data.Region
        return res

    @staticmethod
    def _get_instance_name(service: Optional[str], intance_id: Optional[str]) -> Union[str]:
        """
        通过本地资源库获取主机InstanceName
        :return:
        """
        if service not in ['server', 'cdb', 'redis']: return ''
        with DBContext('r', None, None) as db_session:
            if service == 'server':
                instance_name = db_session.query(AssetServerModels.name).filter(
                    AssetServerModels.instance_id == intance_id
                ).first()
        instance_name = instance_name[0] if instance_name else ''
        return instance_name

    def sync_cmdb(self, cloud_name: Optional[str] = 'qcloud', resource_type: Optional[str] = 'events') -> Tuple[
        bool, str]:
        cvm_res = self.get_cvm_events()
        all_events = cvm_res
        if not all_events: return True, 'No events'

        # 更新
        ret_state, ret_msg = cloud_event_task(account_id=self._account_id, cloud_name=cloud_name, rows=all_events)

        return ret_state, ret_msg
