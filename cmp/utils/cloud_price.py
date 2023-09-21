#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Contact : 1084430062@qq.com
Author  : 娄文军
Date    : 2023/7/26 10:47
Desc    : 获取云实例计费
"""

from libs.qcloud.utils import QCloudAPI
from models import TENCENT_LIST


class CloudPrice:

    def __init__(self, account_id: str):
        self.account_id = account_id

    def get_tx_vm_price(self, data):
        """获取腾讯云CVM实例价格"""

        region = data["region"]
        params = {
            "InstanceChargeType": data["instance_charge_type"],
            "Placement": {
                "Zone": data["zone"]
            },
            "InstanceType": data["instance_type"],
            "ImageId": data["image_id"],
            "SystemDisk": {
                "DiskType": data["system_disk_type"],
                "DiskSize": data["system_disk_size"]
            },
            "InstanceCount": data["count"]
        }
        # 如果是包年包月类型, 必须添加以下参数
        if params["InstanceChargeType"] == "PREPAID":
            params["InstanceChargePrepaid"] = {
                "Period": 1,  # 单位：月
                "RenewFlag": "NOTIFY_AND_AUTO_RENEW"
            }
        disk_type, disk_size = data["data_disk"].get("type"), data["data_disk"].get("size")
        if disk_type and disk_size:
            params["DataDisks"] = [dict(DiskType=disk_type, DiskSize=disk_size)]

        tx_api = QCloudAPI(region=region, account_id=self.account_id)
        error, tx_data = tx_api.get_price_ins(params=params)
        if error:
            return dict(msg=f'查询价格失败:{error}', code=-1)
        err_msg = tx_data.get("Error", dict()).get("Message")
        if err_msg:
            return dict(msg=f'查询价格失败:{err_msg}', code=-1)
        res_data = dict(
            dis_count=tx_data["Price"]["InstancePrice"]["Discount"],
            dis_count_price=tx_data["Price"]["InstancePrice"]["DiscountPrice"],
            original_price=tx_data["Price"]["InstancePrice"]["OriginalPrice"],
            bandwidth_dis_count=tx_data["Price"]["BandwidthPrice"]["Discount"],
            bandwidth_dis_count_price=tx_data["Price"]["BandwidthPrice"]["DiscountPrice"],
            bandwidth_original_price=tx_data["Price"]["BandwidthPrice"]["OriginalPrice"],
        )
        return dict(msg='获取成功', code=0, data=res_data)

    def get_cds_vm_price(self, data):
        return dict(msg='获取成功', code=0)

    def get_preice(self, data) -> dict:
        vendor = data["vendor"]
        if vendor in TENCENT_LIST:
            return self.get_tx_vm_price(data)
        elif vendor == "cds":
            return self.get_cds_vm_price(data)
        return dict(msg=f'不支持该云厂商:{vendor}', code=-1)
