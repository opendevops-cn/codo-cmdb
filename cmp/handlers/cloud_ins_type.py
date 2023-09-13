#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Contact : 1084430062@qq.com
Author  : 娄文军
Date    : 2023/8/11 16:46
Desc    : 申购订单
"""

from libs.qcloud.utils import QCloudAPI
from models import TENCENT_LIST


class CloudInsTypeHandler(object):

    def __init__(self, account_id: str):
        self.account_id = account_id

    def get_tx_ins_type(self, data):
        region = data["region"]
        zone = data["zone"]
        instance_type = data["instance_type"]
        tx_api = QCloudAPI(region=region, account_id=self.account_id)
        error, tx_data = tx_api.get_cvm_ins_type(zone=zone, instance_type=instance_type)
        if error:
            return dict(msg=f'查询失败:{error}', code=-1)
        err_msg = tx_data.get("Error", dict()).get("Message")
        if err_msg:
            return dict(msg=f'查询失败:{err_msg}', code=-1)
        tx_config = tx_data["InstanceTypeConfigSet"][0]
        res_data = dict(
            cpu=tx_config["CPU"],
            memory=tx_config["Memory"],
            gpu=tx_config["GPU"]
        )
        return dict(msg='获取成功', code=0, data=res_data)

    def get_cds_ins_type(self, data):
        return dict(msg='获取成功', code=0)

    def get_ins_type(self, data):
        vendor = data["vendor"]
        if vendor in TENCENT_LIST:
            return self.get_tx_ins_type(data)
        elif vendor == "cds":
            return self.get_cds_ins_type(data)
        return dict(msg=f'不支持该云厂商:{vendor}', code=-1)
