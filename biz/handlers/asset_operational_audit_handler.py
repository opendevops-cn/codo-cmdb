#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File  : asset_operational_audit_handler.py
# @Author: Fred Yangxiaofei
# @Date  : 2019/9/11
# @Role  : 资产操作记录


import json
from sqlalchemy import or_
from libs.base_handler import BaseHandler
from models.server import model_to_dict, AssetOperationalAudit
from websdk.db_context import DBContext
import tornado.web
import time, datetime
from dateutil.relativedelta import relativedelta


class AssetOperationalAuditHandler(tornado.web.RequestHandler):
    def get(self, *args, **kwargs):
        id = self.get_argument('id', default=None, strip=True)
        page_size = self.get_argument('page', default=1, strip=True)
        limit = self.get_argument('limit', default=10, strip=True)
        key = self.get_argument('key', default=None, strip=True)
        value = self.get_argument('value', default=None, strip=True)
        start_date = self.get_argument('start_date', default=None, strip=True)
        end_date = self.get_argument('end_date', default=None, strip=True)
        limit_start = (int(page_size) - 1) * int(limit)

        if not start_date:
            start_date = datetime.date.today() - relativedelta(months=+1)
        if not end_date:
            end_date = datetime.date.today() + datetime.timedelta(days=1)

        start_time_tuple = time.strptime(str(start_date), '%Y-%m-%d')
        end_time_tuple = time.strptime(str(end_date), '%Y-%m-%d')
        log_list = []

        with DBContext('r') as session:
            if id:
                count = session.query(AssetOperationalAudit).filter(AssetOperationalAudit.id == id).count()
                log_info = session.query(AssetOperationalAudit).filter(AssetOperationalAudit.id == id).all()
            elif key and value:
                count = session.query(AssetOperationalAudit).filter(AssetOperationalAudit.ctime > start_time_tuple,
                                                                    AssetOperationalAudit.ctime < end_time_tuple).filter_by(
                    **{key: value}).count()
                log_info = session.query(AssetOperationalAudit).filter(AssetOperationalAudit.ctime > start_time_tuple,
                                                                       AssetOperationalAudit.ctime < end_time_tuple).filter_by(
                    **{key: value}).order_by(-AssetOperationalAudit.ctime)
            else:
                count = session.query(AssetOperationalAudit).filter(AssetOperationalAudit.ctime > start_time_tuple,
                                                                    AssetOperationalAudit.ctime < end_time_tuple).count()
                log_info = session.query(AssetOperationalAudit).filter(AssetOperationalAudit.ctime > start_time_tuple,
                                                                       AssetOperationalAudit.ctime < end_time_tuple).order_by(
                    -AssetOperationalAudit.ctime).offset(limit_start).limit(int(limit))

        for msg in log_info:
            data_dict = model_to_dict(msg)
            data_dict['ctime'] = str(data_dict['ctime'])
            log_list.append(data_dict)

        return self.write(dict(code=0, msg='获取日志成功', count=count, data=log_list))


asset_audit_urls = [
    (r"/v1/cmdb/operational_audit/", AssetOperationalAuditHandler)
]
