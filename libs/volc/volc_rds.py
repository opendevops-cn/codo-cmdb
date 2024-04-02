# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/3/28
# @Description: Description
from __future__ import print_function
import logging
from typing import *

import volcenginesdkcore
from volcenginesdkcore.rest import ApiException
from volcenginesdkrdsmysqlv2 import RDSMYSQLV2Api, DescribeDBInstancesRequest

from models.models_utils import mark_expired, mysql_task

InstanceStatusMapping = {
    "Running": "运行中",
    "Creating": "创建中",
    "Deleting": "删除中",
    "Restarting": "重启中",
    "Restoring": "恢复中",
    "Updating": "变更中",
    "Upgrading": "升级中",
    "MasterChanging": "主备切换中",
    "Error": "错误"
}

ChargeStatusMapping = {
    "Normal": "正常",
    "Overdue": "欠费",
    "Unpaid": "等待支付"
}

ChargeTypeMapping = {
    "PostPaid": "按量付费",
    "PrePaid": "包年包月"
}


class VolCRDS:

    def __init__(self, access_id: str, access_key: str, region: str, account_id: str):
        self.cloud_name = 'volc'
        self.page_number = 1  # 实例状态列表的页码。起始值：1 默认值：1
        self.page_size = 100  # 分页查询时设置的每页行数。最大值：100 默认值：10
        self._region = region
        self._account_id = account_id
        self.api_instance = self.__initialize_api_instance(access_id, access_key, region)

    @staticmethod
    def __initialize_api_instance(access_id: str, access_key: str, region: str):
        """
        初始化api实例对象
        https://api.volcengine.com/api-sdk/view?serviceCode=rds_mysql&version=2022-01-01&language=Python
        :param access_id:
        :param access_key:
        :param region:
        :return:
        """
        configuration = volcenginesdkcore.Configuration()
        configuration.ak = access_id
        configuration.sk = access_key
        configuration.region = region
        # configuration.client_side_validation = False
        # set default configuration
        volcenginesdkcore.Configuration.set_default(configuration)
        return RDSMYSQLV2Api()

    def get_describe_db_instance(self):
        """
        接口查询RDSMysql实例的基本信息
        Doc: https://api.volcengine.com/api-docs/view?serviceCode=rds_mysql&version=2022-01-01&action=DescribeDBInstances
        :return:
        """
        try:
            instances_request = DescribeDBInstancesRequest()
            instances_request.page_number = self.page_number
            instances_request.page_size = self.page_size
            resp = self.api_instance.describe_db_instances(instances_request)
            return resp
        except ApiException as e:
            logging.error("Exception when calling VolcRDS.get_describe_db_instance: %s", e)

            return None

    def get_all_rds(self):
        rds_list = []
        try:
            while True:
               data = self.get_describe_db_instance()
               if data is None:
                   break
               instances = data.instances
               if not instances:
                   break
               rds_list.extend([self.handle_data(data) for data in instances])
               total = data.total
               if total < self.page_size:
                   break
               self.page_number += 1
        except Exception as err:
            logging.error(f"火山云RDS  get all rds {self._account_id} {err}")
        return rds_list

    def handle_data(self, data) -> Dict[str, Any]:
        """
        处理数据
        :param data:
        :return:
        """
        res: Dict[str, Any] = dict()
        res["instance_id"] = data.instance_id
        res["name"] = data.instance_name
        res["create_time"] = data.create_time
        res['region'] = data.region_id
        res['db_class'] = "双节点" if data.instance_type == "DoubleNode" else data.instance_type
        res['db_engine'] = "MySQL"
        res["db_version"] = data.db_engine_version
        res['state'] = InstanceStatusMapping.get(data.instance_status, "未知")
        res["vpc_id"] = data.vpc_id
        res['zone'] = data.zone_id
        res['network_type'] = "专有网络"
        res['charge_type'] = ChargeTypeMapping.get(data.charge_detail.charge_type, "未知")
        items = self.__format_db_address(data.address_object)
        res['db_address'] = dict(items=items)
        return res


    def __format_db_address(self, address_object):
        """
        组装db_address
        :param address:
        :return:
        """
        items = []
        for addr in address_object:
            if addr.network_type == "Public":
                item = {
                    "endpoint_type": "Primary",
                    "type": "public",
                    "port": addr.port,
                    "ip": addr.ip_address,
                    "domain": addr.domain
                }
            elif addr.network_type == "Private":
                item = {
                    "endpoint_type": "Primary",
                    "type": "private",
                    "port": addr.port,
                    "ip": addr.ip_address,
                    "domain": addr.domain
                }
            else:
                item = {}
            items.append(item)
        return items

    def sync_cmdb(self, cloud_name: Optional[str] = 'volc', resource_type: Optional[str] = 'mysql') -> Tuple[
        bool, str]:
        """
        同步到DB
        :param cloud_name:
        :param resource_type:
        :return:
        """
        all_rds_list: List[dict] = self.get_all_rds()
        if not all_rds_list: return False, "RDS列表为空"
        # 更新资源
        ret_state, ret_msg = mysql_task(account_id=self._account_id, cloud_name=cloud_name, rows=all_rds_list)
        # 标记过期
        mark_expired(resource_type=resource_type, account_id=self._account_id)

        return ret_state, ret_msg



if __name__ == '__main__':
    pass