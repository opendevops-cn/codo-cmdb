#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/1/27 11:02
Desc    : AWS health Events
"""

import boto3
import logging
from settings import settings
from typing import *
from models.asset import AssetServerModels
from models.event import AwsHealthEventModels
from websdk2.db_context import DBContext

"""
需要添加AWSHealthFullAccess权限
"""


def get_event_status(val):
    mapping = {
        "Upcoming": "未处理",
        "Closed": "已关闭"
    }
    return mapping.get(val, val)


class AwsHealthClient:
    def __init__(self, access_id: Optional[str], access_key: Optional[str], account_id: Optional[str],
                 region: Optional[str]):
        self._access_id = access_id
        self._access_key = access_key
        self._accountID = account_id
        self._region = region
        self.__client = self.create_client()

    def create_client(self):
        """
        aws health 仅在指定地区有endpoints,us-east-1表示global全球
        https://docs.aws.amazon.com/health/latest/ug/health-api.html
        :return:
        """
        try:
            client = boto3.client('health', region_name='us-east-1', aws_access_key_id=self._access_id,
                                  aws_secret_access_key=self._access_key)
        except Exception as err:
            logging.error(f'-{self._accountID}-{self._region}aws health boto3 create client error:{err}')
            client = None
        return client

    def get_all_events(self) -> List[dict]:
        """
        docs:https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/health.html#Health.Client.describe_events
        :return:
        """
        try:
            # rsp : List[Dict[str, str]]
            response = self.__client.describe_events(maxResults=10, filter={
                "eventTypeCategories": ["scheduledChange"],  # 主动运维事件
                # 根据时间 （一个月）
                # 'lastUpdatedTimes': [
                #     {
                #         'from': datetime(2021, 5, 1),
                #         'to': datetime(2021, 6, 1)
                #     },
                # ],
            })
            events = response.get('events')
            if not events: return []
            # 基础信息,不包含instanceID
            basic_events = list(map(self._format_events, events))

            # 所有的arns
            arns = [e.get('arn') for e in events]
            # event detail信息, 获取InstanceID和AccountID
            event_details = self.get_event_details(arns)
            res_list: List[Dict] = []
            for _event in event_details:
                for _basic in basic_events:
                    if _event.get('event_arn') == _basic.get('event_arn'):
                        _event.update(_basic)
                        res_list.append(_event)
        except Exception as err:
            logging.error(f'get aws health events error, {err}')
            return []
        return res_list

    @staticmethod
    def _format_events(data: Optional[Dict]) -> Dict[str, str]:
        """
        :param data: events
        :return:
        """
        res: Dict[str, str] = {}
        res['event_arn'] = data.get('arn')
        res['event_service'] = data.get('service')
        res['event_type'] = data.get('eventTypeCode')
        res['event_region'] = data.get('region')
        res['event_start_time'] = data.get('startTime')
        res['event_end_time'] = data.get('endTime')
        res['event_status'] = get_event_status(data.get('statusCode'))
        return res
        # res['event_details'] = self.get_event_details(data.get('arn'))

    def get_event_details(self, event_arns: list) -> List[Dict[str, str]]:
        response = self.__client.describe_affected_entities(
            filter={
                "eventArns": event_arns
                # "eventArns": [
                #     'arn:aws:health:ap-northeast-1::event/EC2/AWS_EC2_INSTANCE_REBOOT_FLEXIBLE_MAINTENANCE_SCHEDULED/AWS_EC2_INSTANCE_REBOOT_FLEXIBLE_MAINTENANCE_SCHEDULED_4c741f55-fbc2-4791-871d-378eb307a20c',
                # ]
            }

        )
        event_details: List[Dict[str, str]] = []
        entities = response.get('entities')
        if entities:
            for data in entities:
                detail = {
                    "event_arn": data.get('eventArn'),  # arn 对应关系
                    "event_account_id": data.get('awsAccountId'),  # 账号ID
                    "event_instnace_id": data.get('entityValue'),  # 实例ID
                    "event_hostname": self.get_event_hostname(data.get('entityValue'))  # 实例名称
                }
                event_details.append(detail)
        return event_details

    @staticmethod
    def get_event_hostname(instance_id: Optional[str]) -> Union[str]:
        """
        通过Event InstanceID查询出来对应的Host
        :return:
        """
        with DBContext('r', None, None, **settings) as db_session:
            the_host_name = db_session.query(AssetServerModels.name).filter(
                AssetServerModels.instance_id == instance_id
            ).first()

            host_name = the_host_name[0] if the_host_name else ''

        return host_name

    @staticmethod
    def sync_task(all_events: List[dict]) -> Tuple[bool, str]:
        try:
            with DBContext('w', None, None, **settings) as db_session:
                for event in all_events:
                    event_arn = event.get('event_arn')
                    exist_arn = db_session.query(AwsHealthEventModels.id).filter(
                        AwsHealthEventModels.event_arn == event_arn
                    ).first()
                    if not exist_arn:
                        db_session.add(
                            AwsHealthEventModels(
                                event_arn=event_arn, event_service=event.get('event_service'),
                                event_account_id=event.get('event_account_id'), event_region=event.get('event_region'),
                                event_instnace_id=event.get('event_instnace_id'),
                                event_hostname=event.get('event_hostname'),
                                event_type=event.get('event_type'), event_status=event.get('event_status'),
                                event_start_time=event.get('event_start_time'),
                                event_end_time=event.get('event_end_time')
                            )
                        )

                    else:
                        db_session.query(AwsHealthEventModels).filter(
                            AwsHealthEventModels.event_arn == event_arn
                        ).update(dict(event_arn=event_arn, event_service=event.get('event_service'),
                                      event_account_id=event.get('event_account_id'),
                                      event_region=event.get('event_region'),
                                      event_instnace_id=event.get('event_instnace_id'),
                                      event_hostname=event.get('event_hostname'),
                                      event_type=event.get('event_type'),
                                      event_status=event.get('event_status'),
                                      event_start_time=event.get('event_start_time'),
                                      event_end_time=event.get('event_end_time')))
                db_session.commit()
        except Exception as err:
            return False, str(err)

        return True, "Sync success"

    def sync_cmdb(self) -> Tuple[bool, str]:
        all_events: List[dict] = self.get_all_events()
        if not all_events: return False, "AWS Events为空"
        return self.sync_task(all_events)


if __name__ == '__main__':
    pass
