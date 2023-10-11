#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Contact : 1084430062@qq.com
Author  : 娄文军
Date    :  2023/7/26 15:53
Desc    : 申购订单
"""

import json
import ipaddress
from loguru import logger
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.model_utils import insert_or_update
from models.order_model import OrderInfoModel
from models import TENCENT_LIST
from libs.flow import FlowAPI
from websdk2.configs import configs


class CloudBuyUtils(FlowAPI):

    def __init__(self):
        # 此处可以引用SDK
        self.callback = f"{configs.get('cmdb_host')}/api/cmdb/api/v2/cmdb/order/callback/"
        super(CloudBuyUtils, self).__init__()

    @staticmethod
    def check_ip(ip_addr):
        try:
            ipaddress.ip_address(ip_addr)
            return True
        except ValueError:
            return False

    def exec_create_flow(self, data, tf_params):
        """这里统一对触发购买任务"""
        error, ret_data = None, list()
        server = tf_params["target"]
        instance_name = tf_params['data']['instance_name']
        count = tf_params['data']["count"]
        inner_ip = data.get("inner_ip")
        if inner_ip and self.check_ip(inner_ip) is False:
            error = "私有IP地址不合法"
            return error, ret_data

        # 选择模板修改后，最终进行购买
        for i in range(count):
            re_inner_ip = inner_ip
            if count > 1:
                # 购买多个实例，名称后缀自动有序递增
                re_name = f"{instance_name}-{i + 1}"
                if inner_ip:
                    # 私有IP，多个实例，自动有序递增
                    innerip_list = inner_ip.split(".")
                    d_ip_num = str(int(innerip_list[-1]) + i)
                    del innerip_list[-1]
                    innerip_list.append(d_ip_num)
                    re_inner_ip = ".".join(innerip_list)
            else:
                re_name = instance_name
            tf_params['data']['instance_name'] = re_name
            tf_params['data']['private_ip'] = re_inner_ip

            tf_params['data']['count'] = 1
            params = {"server": server, "action": "create", "requests_json": json.dumps(tf_params)}
            body = dict(
                flow_version_name="Terraform多云管理-运维项目",
                order_name=f'Terraform多云管理',
                global_params=json.dumps(params),
                creator="CMDB"
            )
            response = self.create_flow(data=json.dumps(body))
            status = "0"
            if response.get("code") != 0:
                status = "4"
                error = f'调用Flow任务失败:{response.get("msg")}'
            flow_id = response["flow_list_id"]
            order_data = dict(
                flow_id=flow_id,
                name=data['name'],
                instance_name=re_name,
                res_type=server,
                vendor=data["vendor"],
                status=status,
                data=data
            )
            ret_state, ret_msg = self.save_order(data=order_data)
            if not ret_state:
                error = ret_msg
            ret_data.append(flow_id)
        return error, ret_data

    def tx_buy_handler(self, data):
        # 购买虚拟机资源
        tf_params = {
            "csp": "tencent",
            "target": data["res_type"],
            "callback": self.callback,
            "account_id": data["account_id"],
            "cloud_region_id": data["cloud_region_id"],
            "data": {
                "region": data["region"],
                "instance_status": "running",
                "instance_name": data["instance_name"],
                "instance_charge_type": data["instance_charge_type"],
                "availability_zone": data["zone"],
                "system_disk_size": data["system_disk_size"],
                "tags": data["tags"],
                "instance_type": data["instance_type"],
                "image_id": data["image_id"],
                "system_disk_type": data["system_disk_type"],
                "security_groups": list(data["security_groups"].keys()),
                "vpc_id": data["vpc_id"],
                "private_ip": data["inner_ip"],
                "subnet_id": data["subnet_id"],
                "bandwidth_package_id": data["bandwidth_pkg_id"],
                "allocate_public_ip": True if data["is_eip"] == "1" else False,
                "internet_max_bandwidth_out": data["max_flow_out"],
                "internet_charge_type": data["internet_charge_type"],
                "image_passwd": data["image_passwd"],
                "data_disk": data["data_disk"],
                "count": data["count"]
            }
        }
        error, ret_data = self.exec_create_flow(data=data, tf_params=tf_params)
        if error:
            return dict(msg=f"下单失败:{error}", code=-1)
        return dict(msg="下单成功", data=ret_data, code=0)

    def cds_buy_handler(self, data) -> dict:
        return dict()

    @staticmethod
    def save_order(data) -> tuple:
        """保存订单数据"""
        ret_state, ret_msg = True, None
        try:
            with DBContext('w', None, True) as db_session:
                flow_id = data["flow_id"]
                name = data["name"]
                try:
                    db_session.add(insert_or_update(OrderInfoModel, f"flow_id='{flow_id}' and name='{name}'", **data))
                except Exception as err:
                    logger.error(err)
                    ret_state, ret_msg = False, f"写入订单数据库失败:{err}"
        except Exception as err:
            ret_state, ret_msg = False, f"写入订单数据库失败:{err}"
        return ret_state, ret_msg

    def buy(self, data) -> dict:
        vendor = data["vendor"]
        if vendor in TENCENT_LIST:
            return self.tx_buy_handler(data)
        elif vendor == "cds":
            return self.cds_buy_handler(data)
        else:
            return dict(msg=f'不支持该云厂商:{vendor}', code=-1)
