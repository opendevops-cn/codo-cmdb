# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/3/26
# @Description: 火山云redis实例
from __future__ import print_function
import logging
from typing import *

import volcenginesdkcore
from volcenginesdkcore.rest import ApiException
from volcenginesdkredis import REDISApi, DescribeDBInstancesRequest, DescribeDBInstanceDetailRequest

from models.models_utils import redis_task, mark_expired


# 文档 https://www.volcengine.com/docs/6293/71563
RedisStatusMapping = {
    "AllowListMaintaining": "白名单维护中",
    "Scaling": "变更配置中",
    "ParameterModifying": "参数修改中",
    "Restarting": "重启中",
    "Creating": "创建中",
    "CreateFailed": "创建失败",
    "ProxyRestarting": "代理重启中",
    "Closing": "关停中",
    "Restoring": "恢复中",
    "AZChanging": "迁移可用区中",
    "TaskFailed": "任务执行失败",
    "Deleting": "删除中",
    "Upgrading": "升级版本中",
    "NetworkMaintaining": "网络维护中",
    "Maintaining": "维护中",
    "Released": "已关停",
    "Running": "运行中",
    "PrimaryChanging": "主备切换中"
}

# 计费类型
ChargeTypeMapping = {
    "PrePaid": "包年包月",
    "PostPaid": "按量计费"
}

# 实例类型
InstanceClassMapping = {
    "PrimarySecondary": "主备实例",
    "Standalone": "单节点实例"
}

# 分片集群
ShardedClusterMapping = {
    0: "不启用",
    1: "启用"
}

# 实例删除保护功能
DeletionProtectionMapping = {
    "enabled": "已开启",
    "disabled": "已关闭"
}

# 免密访问是否打开
VpcAuthModeMapping = {
    "open": "已开启",
    "close": "已关闭",
}

class VolCRedis:
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
        https://api.volcengine.com/api-sdk/view?serviceCode=Redis&version=2020-12-07&language=Python
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
        return REDISApi()

    def get_describe_db_instance(self):
        """
        接口查询Redis实例的基本信息
        Doc: https://api.volcengine.com/api-docs/view?serviceCode=Redis&version=2020-12-07&action=DescribeDBInstances
        :return:
        """
        try:
            instances_request = DescribeDBInstancesRequest(page_size=self.page_size, page_number=self.page_number,
                                                           region_id=self._region)
            resp = self.api_instance.describe_db_instances(instances_request)
            return resp
        except ApiException as e:
            logging.error("Exception when calling VolCRedis.get_describe_db_instance: %s", e)
            return None

    def get_describe_db_instance_detail(self, instance_id: str) -> dict:
        """
        接口查询redis实例的详细信息
        Doc: https://api.volcengine.com/api-docs/view?serviceCode=Redis&version=2020-12-07&action=DescribeDBInstanceDetail
        :param instance_id:
        :return:
        """
        try:
            instances_request = DescribeDBInstanceDetailRequest(instance_id=instance_id)
            resp = self.api_instance.describe_db_instance_detail(instances_request)
            return resp
        except ApiException as e:
            logging.error("Exception when calling VolCRedis.get_describe_db_instance_detail: %s", e)
            return None

    def get_all_redis(self):
        """
        :return:
        """
        redis_list = []
        self.page_number = 1
        while True:
            data = self.get_describe_db_instance()
            if data is None:
                break

            instances = data.instances
            if not instances:
                break
            redis_list.extend([self.handle_data(data) for data in instances])
            total_instances_num = data.total_instances_num
            if total_instances_num < self.page_size:
                break
            self.page_number += 1

        return redis_list

    def handle_data(self, data) -> Dict[str, str]:
        """
        处理数据
        :param data:
        :return:
        """
        # 定义返回
        res: Dict[str, Any] = dict()
        try:
            vpc_id = data.vpc_id
            instance_id = data.instance_id
            res['vpc_id'] = data.vpc_id
            res["network_type"] = '经典网络' if not vpc_id else '专有网络'
            res['qps'] = ''
            res['vswitch_id'] = ""
            res['instance_arch'] = ""
            res['instance_id'] = instance_id
            res['name'] = data.instance_name
            res['state'] = RedisStatusMapping.get(data.status, "Unknown")
            res['region'] = data.region_id
            res['charge_type'] = ChargeTypeMapping.get(data.charge_type, "Unknown")
            res['instance_type'] = 'Redis'
            res['instance_version'] = data.engine_version
            res['create_time'] = data.create_time
            res['zone'] = ";".join(data.zone_ids)
            res['instance_class'] = f'{data.capacity.total}MB'

            # 补充实例详情
            detail = self.get_describe_db_instance_detail(instance_id=instance_id)
            if detail is not None:
                items = []
                visit_addrs = detail.visit_addrs
                for addr in visit_addrs:
                    items.append(
                        {
                            "type": addr.addr_type.lower(),
                            "ip": "",
                            "domain": addr.address,
                            "port": addr.port
                        })
                res["instance_address"] = {"items": items}


        except Exception as err:
            logging.error(f"火山云Redis  data format err {self._account_id} {err}")

        return res

    def sync_cmdb(self, cloud_name: Optional[str] = 'volc', resource_type: Optional[str] = 'redis') -> Tuple[
        bool, str]:
        """
        同步到DB
        :param cloud_name:
        :param resource_type:
        :return:
        """
        all_redis_list: List[dict] = self.get_all_redis()
        if not all_redis_list:
            return False, "Redis列表为空"
        # 更新资源
        ret_state, ret_msg = redis_task(account_id=self._account_id, cloud_name=cloud_name, rows=all_redis_list)
        # 标记过期
        mark_expired(resource_type=resource_type, account_id=self._account_id)

        return ret_state, ret_msg


if __name__ == '__main__':
    pass