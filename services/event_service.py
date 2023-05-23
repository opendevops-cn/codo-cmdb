#!/usr/bin/env python
# -*- coding: utf-8 -*-
""""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023年2月5日
Desc    : Events 逻辑处理
"""

import logging
from sqlalchemy import or_
from typing import *
from websdk2.db_context import DBContextV2 as DBContext
from models.event import AwsHealthEventModels, CloudEventsModels
from websdk2.sqlalchemy_pagination import paginate


def _get_by_status(filter_status: str = None):
    """模糊查询"""
    if not filter_status:
        return True
    return or_(
        AwsHealthEventModels.event_status == filter_status
    )


def _get_by_val(val: str = None):
    """模糊查询"""
    if not val:
        return True
    return or_(
        AwsHealthEventModels.event_account_id.like(f'%{val}%'),
        AwsHealthEventModels.event_instnace_id.like(f'%{val}%'),
        AwsHealthEventModels.event_hostname.like(f'%{val}%'),
        AwsHealthEventModels.event_type.like(f'%{val}%'),
    )


def get_aws_event_list(**params) -> dict:
    value = params.get('searchValue') if "searchValue" in params else params.get('searchVal')
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'page_size' not in params: params['page_size'] = 300  # 默认获取到全部数据
    filter_status = params.get('filter_status')
    with DBContext('r') as session:
        page = paginate(session.query(AwsHealthEventModels).filter(_get_by_status(filter_status),
                                                                   _get_by_val(value)).filter_by(**filter_map),
                        **params)
    return dict(code=0, msg='获取成功', data=page.items, count=page.total)


def _get_by_al_status(filter_status: str = None):
    """模糊查询"""
    if not filter_status:
        return True
    if filter_status == '待处理' or filter_status == 'true':
        return or_(
            CloudEventsModels.event_status == "待处理"
        )
    else:
        return True


def _get_by_al_val(val: str = None):
    """模糊查询"""
    if not val:
        return True
    return or_(
        CloudEventsModels.account_id.like(f'%{val}%'),
        CloudEventsModels.event_instance_id.like(f'%{val}%'),
        CloudEventsModels.event_instance_name.like(f'%{val}%'),
        CloudEventsModels.event_type.like(f'%{val}%'),
        CloudEventsModels.event_detail.like(f'%{val}%'),
    )


def get_aliyun_event_list(**params) -> dict:
    value = params.get('searchValue') if "searchValue" in params else params.get('searchVal')
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'page_size' not in params: params['page_size'] = 300  # 默认获取到全部数据
    filter_status = params.get('filter_status')
    with DBContext('r') as session:
        page = paginate(session.query(CloudEventsModels).filter(CloudEventsModels.cloud_name == 'aliyun',
                                                                _get_by_al_status(filter_status),
                                                                _get_by_al_val(value)).filter_by(**filter_map),
                        **params)
    return dict(code=0, msg='获取成功', data=page.items, count=page.total)


def _get_by_qcloud_status(filter_status: str = None):
    """模糊查询"""
    if not filter_status:
        return True
    if filter_status == '待处理' or filter_status == 'true':
        return or_(
            CloudEventsModels.event_status == "待授权",
            CloudEventsModels.event_status == "处理中",
            CloudEventsModels.event_status == "已预约"
        )
    else:
        return True


def _get_by_qcloud_val(val: str = None):
    """模糊查询"""
    if not val:
        return True
    return or_(
        CloudEventsModels.account_id.like(f'%{val}%'),
        CloudEventsModels.event_instance_id.like(f'%{val}%'),
        CloudEventsModels.event_instance_name.like(f'%{val}%'),
        CloudEventsModels.event_detail.like(f'%{val}%'),
    )


def get_qcloud_event_list(**params) -> dict:
    value = params.get('searchValue') if "searchValue" in params else params.get('searchVal')
    filter_map = params.pop('filter_map') if "filter_map" in params else {}
    if 'page_size' not in params: params['page_size'] = 300  # 默认获取到全部数据
    filter_status = params.get('filter_status')
    with DBContext('r') as session:
        page = paginate(session.query(CloudEventsModels).filter(CloudEventsModels.cloud_name == 'qcloud',
                                                                _get_by_qcloud_status(filter_status),
                                                                _get_by_qcloud_val(value)).filter_by(**filter_map),
                        **params)
    return dict(code=0, msg='获取成功', data=page.items, count=page.total)
