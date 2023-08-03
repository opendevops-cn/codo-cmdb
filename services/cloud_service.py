#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2021/1/27 11:02
Desc    : 解释一下吧
"""
from typing import *
from websdk2.db_context import DBContextV2 as DBContext
from models.cloud import CloudSettingModels, SyncLogModels
from websdk2.utils.date_format import date_format_to8
from websdk2.model_utils import CommonOptView, queryset_to_list

opt_obj = CommonOptView(CloudSettingModels)


def get_cloud_settings() -> dict:
    with DBContext('r', None, None) as session:
        cloud_setting_info: List[CloudSettingModels] = session.query(CloudSettingModels).all()
        cloud_list: List[dict] = queryset_to_list(cloud_setting_info)
    return dict(msg='获取成功', code=0, data=cloud_list)


def get_cloud_sync_log(account_id) -> dict:
    if not account_id:
        return {"code": 1, "msg": "not account_id"}

    start_time_tuple, end_time_tuple = date_format_to8()
    with DBContext('r', None, None) as session:
        sync_log_info: List[SyncLogModels] = session.query(SyncLogModels).filter(
            SyncLogModels.sync_time.between(start_time_tuple, end_time_tuple)).filter(
            SyncLogModels.account_id == account_id).order_by(-SyncLogModels.id).limit(50)

        sync_log_list: List[dict] = queryset_to_list(sync_log_info)
    return dict(msg='获取成功', code=0, data=sync_log_list)
