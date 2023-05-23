#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023年4月7日
Desc    : 阿里云Events主动运维事件（ECS、PolarDB、Redis）
"""

import json
import datetime
from settings import settings
from typing import *
from models.asset import AssetServerModels, AssetMySQLModels, AssetRedisModels
# from models.event import AliyunEventsModels
from websdk2.db_context import DBContext
from models.models_utils import cloud_event_task
from aliyunsdkcore.client import AcsClient
from aliyunsdkecs.request.v20140526.DescribeInstanceHistoryEventsRequest import DescribeInstanceHistoryEventsRequest
from aliyunsdkpolardb.request.v20170801.DescribePendingMaintenanceActionRequest import \
    DescribePendingMaintenanceActionRequest
from aliyunsdkr_kvstore.request.v20150101.DescribeActiveOperationTaskRequest import DescribeActiveOperationTaskRequest


def ecs_event_status(val):
    mapping = {
        "Scheduled": "待处理",
        "Executing": "执行中",
        "Executed": "已完成",
    }
    return mapping.get(val, val)


def db_event_status(val):
    mapping = {
        2: "等待指定时间",
        3: "待处理",
        4: "处理中",
        5: "成功",
        6: "失败",
        7: "已取消"
    }
    return mapping.get(val, '未知')


def ecs_event_type(val):
    mapping = {
        "SystemMaintenance.Reboot": "因系统维护实例重启",
        "SystemFailure.Reboot": "因系统错误实例重启",
        "SystemFailure.Redeploy": "因系统错误实例重新部署",
        "SystemFailure.Delete": "因实例创建失败实例释放",
        "InstanceFailure.Reboot": "因实例错误实例重启",
        "InstanceExpiration.Stop": "因包年包月期限到期，实例停止",
        "InstanceExpiration.Delete": "因包年包月期限到期，实例释放",
        "AccountUnbalanced.Stop": "因账号欠费，按量付费实例停止",
        "AccountUnbalanced.Delete": "因账号欠费，按量付费实例释放"
    }
    return mapping.get(val, val)


def polardb_event_type(val):
    mapping = {
        "DatabaseSoftwareUpgrading": "数据库软件升级",
        "DatabaseHardwareMaintenance": "硬件维护与升级",
        "DatabaseStorageUpgrading": "数据库存储升级",
        "DatabaseProxyUpgrading": "代理小版本升级"
    }
    return mapping.get(val, val)


def redis_event_type(val):
    mapping = {
        "rds_apsaradb_ha": "主从节点切换",
        "rds_apsaradb_transfer": "实例迁移",
        "rds_apsaradb_upgrade": "小版本升级"
    }
    return mapping.get(val, val)


class AliyunEventClient:
    def __init__(self, access_id: Optional[str], access_key: Optional[str], region: Optional[str],
                 account_id: Optional[str]):
        self._access_id = access_id
        self._access_key = access_key
        self._region = region
        self._account_id = account_id
        self.__client = AcsClient(self._access_id, self._access_key, self._region)

    def get_ecs_events(self) -> List[Dict[str, Any]]:
        """
        调用DescribeInstanceHistoryEvents查询实例的系统事件信息
        :return:
        """
        request = DescribeInstanceHistoryEventsRequest()
        request.set_accept_format('json')
        request.set_InstanceEventCycleStatuss(["Scheduled", "Executed"])
        response = self.__client.do_action_with_exception(request)
        response = json.loads(str(response, encoding="utf8"))
        res_list = response.get('InstanceSystemEventSet').get('InstanceSystemEventType')
        if not res_list: return []
        return list(map(self._ecs_format, res_list))

    def get_polardb_events(self) -> List[Dict[str, Any]]:
        """
        调用DescribePendingMaintenanceAction接口查询待处理事件的详情。
        :return:
        """
        request = DescribePendingMaintenanceActionRequest()
        request.set_accept_format('json')
        request.set_Region("all")
        request.set_TaskType("all")
        response = self.__client.do_action_with_exception(request)
        response = json.loads(str(response, encoding="utf8"))
        res_list = response.get('Items')
        if not res_list: return []
        return list(map(self._polardb_format, res_list))

    def get_redis_events(self) -> List[Dict[str, Any]]:
        """
        调用DescribeActiveOperationTask查询Redis实例的运维任务详情。
        :return:
        """
        request = DescribeActiveOperationTaskRequest()
        request.set_accept_format('json')
        request.set_TaskType("all")
        request.set_Region("all")
        response = self.__client.do_action_with_exception(request)
        response = json.loads(str(response, encoding="utf8"))
        res_list = response.get('Items')
        if not res_list: return []
        return list(map(self._redis_format, res_list))

    @staticmethod
    def _get_instance_name(service: Optional[str], intanceid: Optional[str]) -> Union[str]:
        """
        通过本地资源库获取主机InstanceName
        :return:
        """
        if service not in ['ecs', 'polardb', 'redis']: return ''
        with DBContext('r', None, None, **settings) as db_session:
            if service == 'ecs':
                instance_name = db_session.query(AssetServerModels.name).filter(
                    AssetServerModels.instance_id == intanceid
                ).first()
            elif service == 'polardb':
                instance_name = db_session.query(AssetMySQLModels.dbname).filter(
                    AssetMySQLModels.instance_id == intanceid
                ).first()
            elif service == 'redis':
                instance_name = db_session.query(AssetRedisModels.instance_name).filter(
                    AssetRedisModels.instance_id == intanceid
                ).first()
        instance_name = instance_name[0] if instance_name else ''
        return instance_name

    def _ecs_format(self, data: Optional[Dict]) -> Dict[str, Any]:
        res: Dict[str, Any] = dict()

        _default_service = 'ecs'
        res["account_name"] = self._account_id
        res["event_service"] = _default_service
        res["event_id"] = data.get('EventId')
        res["event_type"] = ecs_event_type(data.get('EventType').get('Name'))
        res['event_status'] = ecs_event_status(data.get('EventCycleStatus').get('Name'))
        instance_id = data.get('InstanceId')
        res['event_instance_id'] = instance_id
        res['event_instance_name'] = self._get_instance_name(_default_service, instance_id)
        res['region'] = data.get('Region')
        res['event_start_time'] = self._parse_utctime(data.get('EventPublishTime'))
        res['event_end_time'] = self._parse_utctime(data.get('NotBefore'))
        res['event_detail'] = data.get('Reason')
        return res

    def _polardb_format(self, data: Optional[Dict]) -> Dict[str, Any]:
        _default_service = 'polardb'
        res: Dict[str, Any] = dict()

        res["account_name"] = self._account_id
        res["event_service"] = _default_service
        res["event_id"] = str(data.get('Id'))
        res["event_type"] = polardb_event_type(data.get('TaskType'))
        res['event_status'] = db_event_status(data.get('Status'))
        instance_id = data.get('DBClusterId')
        res['event_instance_id'] = instance_id
        res['event_instance_name'] = self._get_instance_name(_default_service, instance_id)
        res['region'] = data.get('Region')
        res['event_start_time'] = self._parse_utctime(data.get('StartTime'))
        res['event_end_time'] = self._parse_utctime(data.get('Deadline'))
        res['event_detail'] = 'SwitchTime at {}'.format(self._parse_utctime(data.get('SwitchTime')))
        return res

    def _redis_format(self, data: Optional[Dict]) -> Dict[str, Any]:
        _default_service = 'redis'
        res: Dict[str, Any] = dict()

        res["account_name"] = self._account_id
        res["event_service"] = _default_service
        res["event_id"] = str(data.get('Id'))
        res["event_type"] = redis_event_type(data.get('TaskType'))
        res['event_status'] = db_event_status(data.get('Status'))
        instance_id = data.get('InsName')
        res['event_instance_id'] = instance_id
        res['event_instance_name'] = self._get_instance_name(_default_service, instance_id)
        res['region'] = data.get('Region')
        res['event_start_time'] = self._parse_utctime(data.get('StartTime'))
        res['event_end_time'] = self._parse_utctime(data.get('Deadline'))
        res['event_detail'] = 'SwitchTime at {}'.format(self._parse_utctime(data.get('SwitchTime')))
        return res

    @staticmethod
    def _parse_utctime(utctime):
        """
        转换UTC时间为本地时间
        :return:
        """
        utc_format = "%Y-%m-%dT%H:%M:%SZ"
        utcTime = datetime.datetime.strptime(utctime, utc_format)
        localtime = utcTime + datetime.timedelta(hours=8)
        return localtime

    def sync_cmdb(self, cloud_name: Optional[str] = 'aliyun', resource_type: Optional[str] = 'events') -> Tuple[
        bool, str]:
        """
        Events 写入数据库
        :return:
        """

        ecs_res, polardb_res, redis_res = self.get_ecs_events(), self.get_polardb_events(), self.get_redis_events()
        all_events: List[Dict] = []
        if ecs_res: all_events.extend(ecs_res)
        if polardb_res: all_events.extend(polardb_res)
        if redis_res: all_events.extend(redis_res)

        if not all_events: return True, 'No events'

        ret_state, ret_msg = cloud_event_task(account_id=self._account_id, cloud_name=cloud_name, rows=all_events)
        return ret_state, ret_msg
        # with DBContext('w', None, True, **settings) as db_session:
        #     for _event in all_events:
        #         exist_event = db_session.query(AliyunEventsModels).filter(
        #             AliyunEventsModels.event_instance_id == _event.get('event_instance_id'),
        #             AliyunEventsModels.event_start_time == _event.get('event_start_time')
        #         ).first()
        #         # 先改为正常
        #         db_session.query(AliyunEventsModels).update({
        #             AliyunEventsModels.event_status: '已完成'
        #         })
        #         if not exist_event:
        #             db_session.add(AliyunEventsModels(
        #                 event_account=_event.get('account_name'),
        #                 event_service=_event.get('event_service'),
        #                 event_type=_event.get('event_type'),
        #                 event_status=_event.get('event_status'),
        #                 event_instance_id=_event.get('event_instance_id'),
        #                 event_instance_name=_event.get('event_instance_name'),
        #                 event_start_time=_event.get('event_start_time'),
        #                 event_end_time=_event.get('event_end_time'),
        #                 event_detail=_event.get('event_detail')
        #             ))
        #         else:
        #             db_session.query(AliyunEventsModels).filter(
        #                 AliyunEventsModels.event_instnace_id == _event.get('event_instance_id'),
        #                 AliyunEventsModels.event_start_time == _event.get('event_start_time')
        #             ).update(
        #                 dict(
        #                     event_account=_event.get('account_name'),
        #                     event_service=_event.get('event_service'),
        #                     event_type=_event.get('event_type'),
        #                     event_status=_event.get('event_status'),
        #                     event_instance_id=_event.get('event_instance_id'),
        #                     event_instance_name=_event.get('event_instance_name'),
        #                     event_start_time=_event.get('event_start_time'),
        #                     event_end_time=_event.get('event_end_time'),
        #                     event_detail=_event.get('event_detail')
        #                 )
        #             )
        #     db_session.commit()
        # return True, 'sync success'


if __name__ == '__main__':
    pass
