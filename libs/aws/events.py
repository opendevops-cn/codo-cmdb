#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File  : events.py
# @Author: Fred Yangxiaofei
# @Date  : 2019/8/23
# @Role  : 获取AWS Events事件信息


import sys, os

Base_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# print(Base_DIR)
sys.path.append(Base_DIR)

import boto3
from libs.db_context import DBContext
from models.server import AssetConfigs, AwsEvents, model_to_dict
from opssdk.operate import MyCryptV2
from websdk.utils import SendMail
from websdk.consts import const
from websdk.tools import convert
from websdk.configs import configs
from libs.redis_conn import redis_conn
from libs.web_logs import ins_log
from settings import AWS_EVENT_TO_EMAIL
import fire


class EventApi():
    def __init__(self, account_name, access_id, access_key, region):
        self.account_name = account_name
        self.access_id = access_id
        self.access_key = access_key
        self.region = region
        self.client = boto3.client('ec2', region_name=self.region, aws_access_key_id=self.access_id,
                                   aws_secret_access_key=self.access_key)

    def get_instance_events(self):
        """
        获取所有实例状态
        docs: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html
        :return:
        """

        response = self.client.describe_instance_status()
        response_list = response['InstanceStatuses']
        events_list = filter(lambda x: "Events" in x.keys(), response_list)
        # print(list(events_list))

        if not events_list: return None
        messages = map(self.fotmat_messages, events_list)

        return messages

    def fotmat_messages(self, events):
        """
        将有问题机器发送邮件通知
        :return:
        """

        if not isinstance(events, dict):
            raise TypeError

        messages = {
            "account_name": self.account_name,
            "region": events.get('AvailabilityZone'),
            "instance_id": events.get('InstanceId'),
            "event_id": events.get('Events')[0]['InstanceEventId'],
            "event_status": events.get('Events')[0]['Code'],
            "event_desc": events.get('Events')[0]['Description'],
            "event_start_time": events.get('Events')[0]['NotBefore'],
        }
        return messages

    def send_mail(self, content):
        """
        发送Mail
        :return:
        content: 邮件内容
        """
        cache_config_info = redis_conn.hgetall(const.APP_SETTINGS)
        if cache_config_info:
            config_info = convert(cache_config_info)
        else:
            config_info = configs['email_info']
        sm = SendMail(mail_host=config_info.get(const.EMAIL_HOST), mail_port=config_info.get(const.EMAIL_PORT),
                      mail_user=config_info.get(const.EMAIL_HOST_USER),
                      mail_password=config_info.get(const.EMAIL_HOST_PASSWORD),
                      mail_ssl=True if config_info.get(const.EMAIL_USE_SSL) == '1' else False)
        sm.send_mail(AWS_EVENT_TO_EMAIL, 'AwsEvents告警', content)

    def send_alert(self):
        """
        Aws Event发送告警
        :return:
        """
        events_list = self.get_instance_events()
        if not events_list: return False
        for event in events_list:
            acount_name = event.get('account_name')
            region = event.get('region')
            event_id = event.get('event_id')
            event_status = event.get('event_status')
            event_desc = event.get('event_desc')
            instance_id = event.get('instance_id')
            event_start_time = event.get('event_start_time')
            html_content = '[AwsEvents告警]\n\n名称：{acount_name}\n区域：{region}\n实例ID：{instance_id}\n事件状态：{event_status}\n事件ID：{event_id}\n开始时间(UTC):{event_start_time}\n\n事件描述：\n{event_desc}'.format(
                acount_name=acount_name, region=region, instance_id=instance_id, event_start_time=event_start_time,
                event_id=event_id, event_status=event_status, event_desc=event_desc)
            print(html_content)
            if 'Completed' not in html_content:
                self.send_mail(html_content)

    def sync_cmdb(self):
        """
        将数据写入数据库
        :return:
        """

        events_list = self.get_instance_events()
        if not events_list:
            ins_log.read_log('info', 'Not Fount AWS Events Messages')
            return

        with DBContext('w') as session:
            for event in events_list:
                # print('事件信息：{event}'.format(event=event))
                # ins_log.read_log('info', '事件信息：{}'.format(event))
                acount_name = event.get('account_name')
                region = event.get('region')
                event_id = event.get('event_id')
                event_status = event.get('event_status')
                event_desc = event.get('event_desc')
                instance_id = event.get('instance_id')
                event_start_time = event.get('event_start_time')
                exist_event_id = session.query(AwsEvents).filter(AwsEvents.event_id == event_id).first()
                if exist_event_id:
                    session.query(AwsEvents).filter(AwsEvents.event_id == event_id).update(
                        {AwsEvents.name: acount_name, AwsEvents.region: region, AwsEvents.event_status: event_status,
                         AwsEvents.event_start_time: event_start_time,
                         AwsEvents.instance_id: instance_id, AwsEvents.event_desc: event_desc})

                else:
                    new_event = AwsEvents(name=acount_name, region=region, instance_id=instance_id, event_id=event_id,
                                          event_status=event_status, event_desc=event_desc, record_state='未处理',
                                          event_start_time=event_start_time)

                    session.add(new_event)
            session.commit()


def get_configs():
    """
    get id / key / region info
    :return:
    """

    aws_configs_list = []
    with DBContext('r') as session:
        aws_configs_info = session.query(AssetConfigs).filter(AssetConfigs.account == 'AWS').all()
        for data in aws_configs_info:
            data_dict = model_to_dict(data)
            data_dict['create_time'] = str(data_dict['create_time'])
            data_dict['update_time'] = str(data_dict['update_time'])
            aws_configs_list.append(data_dict)
    return aws_configs_list


def main():
    """
    从接口获取已经启用的配置
    :return:
    """

    mc = MyCryptV2()
    aws_configs_list = get_configs()
    if not aws_configs_list:
        ins_log.read_log('error', '没有获取到AWS资产配置信息，跳过')
        return False
    for config in aws_configs_list:
        access_id = config.get('access_id')
        access_key = mc.my_decrypt(config.get('access_key'))  # 解密后使用
        region = config.get('region')
        name = config.get('name')  # 名称
        obj = EventApi(account_name=name, access_id=access_id, access_key=access_key, region=region)
        obj.send_alert()
        obj.sync_cmdb()


if __name__ == '__main__':
    fire.Fire(main)
