#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 2023/7/26 10:47
# @Author  : 娄文军
# @Describe: 获取云实例带宽包

from libs.qcloud.utils import QCloudAPI
from models import TENCENT_LIST


class BandWidthPkg:

    def __init__(self, account_id: str):
        self.account_id = account_id

    def get_tx_vm_bandwh_pkg(self, data):
        """获取腾讯云CVM实例带宽包"""
        region = data["region"]
        tx_api = QCloudAPI(region=region, account_id=self.account_id)
        error, tx_data = tx_api.get_bandwidth_packages()
        if error:
            return dict(msg=f'查询失败:{error}', code=-1)
        err_msg = tx_data.get("Error", dict()).get("Message")
        if err_msg:
            return dict(msg=f'查询失败:{err_msg}', code=-1)
        res_data = [{"name": i["BandwidthPackageName"], "id": i["BandwidthPackageId"]} for i in
                    tx_data["BandwidthPackageSet"]]
        return dict(msg='获取成功', code=0, data=res_data)

    def get_cds_vm_bandwh_pkg(self, data):
        return dict(msg='获取成功', code=0)

    def get_bandwh_pkg(self, data):
        vendor = data["vendor"]
        if vendor in TENCENT_LIST:
            return self.get_tx_vm_bandwh_pkg(data)
        elif vendor == "cds":
            return self.get_cds_vm_bandwh_pkg(data)
        return dict(msg=f'不支持该云厂商:{vendor}', code=-1)
