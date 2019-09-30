#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File  : aws_events_handler.py
# @Author: Fred Yangxiaofei
# @Date  : 2019/8/23
# @Role  : AWS Events 事件路由

import json
from tornado.web import RequestHandler
from libs.base_handler import BaseHandler
from models.server import AwsEvents, model_to_dict
from websdk.db_context import DBContext


class AwsEventsHanlder(RequestHandler):
    def get(self, *args, **kwargs):
        key = self.get_argument('key', default=None, strip=True)
        value = self.get_argument('value', default=None, strip=True)
        aws_events_list = []
        with DBContext('r') as session:
            if key and value:
                aws_events_data = session.query(AwsEvents).filter_by(**{key: value}).all()
            else:
                aws_events_data = session.query(AwsEvents).all()

        for data in aws_events_data:
            data_dict = model_to_dict(data)
            data_dict['event_start_time'] = str(data_dict['event_start_time'])
            data_dict['record_create_time'] = str(data_dict['record_create_time'])

            aws_events_list.append(data_dict)

        return self.write(dict(code=0, msg='获取成功', data=aws_events_list))

    def patch(self, *args, **kwargs):

        data = json.loads(self.request.body.decode("utf-8"))
        id = data.get('id', None)
        record_state = data.get('record_state', None)

        if not id or not record_state:
            return self.write(dict(code=-2, msg='关键参数不能为空'))

        if record_state == '未处理':
            new_state = '已处理'

        elif record_state == '已处理':
            new_state = '未处理'

        with DBContext('w', None, True) as session:
            session.query(AwsEvents).filter(AwsEvents.id == id).update({AwsEvents.record_state: new_state})

        return self.write(dict(code=0, msg='状态变更成功'))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        id = data.get('id')
        if not id:
            return self.write(dict(code=-2, msg='关键参数不能为空'))

        with DBContext('w', None, True) as session:
            session.query(AwsEvents).filter(AwsEvents.id == id).delete(synchronize_session=False)

        self.write(dict(code=0, msg='删除成功'))


aws_events_urls = [
    (r"/v1/cmdb/aws_events/", AwsEventsHanlder),
]
