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
from libs.mycrypt import mc

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


def update_cloud_settings(data: dict) -> dict:
    access_key = data.get('access_key', None).strip()
    if data.get('cloud_name').strip().lower() == 'gcp':
        account_file = data.get('account_file')
        if not account_file:
            return dict(code=-1, msg='谷歌云必须输入密钥文件')
        with DBContext('r', None, None) as session:
            cloud_conf_obj = session.query(CloudSettingModels).filter(
                CloudSettingModels.id == data.get('id')).first()
            if cloud_conf_obj.account_file.strip() == account_file.strip():
                data['account_file'] = account_file
            else:
                # 如果密钥文件和已有秘钥文件不一致，则认为是新的密钥文件
                data['account_file'] = mc.my_encrypt(account_file)
        data['access_id'] = 'not_need'
        data['access_key'] = 'not_need'
        data['region'] = 'not_need'
    else:
        data['project_id'] = ''
        data['account_file'] = ''
        if len(access_key) < 110:
            data['access_key'] = mc.my_encrypt(access_key)  # 密钥如果太短，则认为当前密钥为原始密钥
    with DBContext('w', None, True) as session:
        session.query(CloudSettingModels).filter(CloudSettingModels.id == data.get('id')).update(data)
    return dict(msg='更新成功', code=0)