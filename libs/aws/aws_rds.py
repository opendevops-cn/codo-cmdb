#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date   :  2023/1/27 11:02
Desc   :  AWS RDS Aurora
"""

import logging
import boto3
from typing import *
from models.models_utils import mark_expired, mysql_task


class AwsRDSClient:
    def __init__(self, access_id: Optional[str], access_key: Optional[str], region: Optional[str],
                 account_id: Optional[str]):
        self._access_id = access_id
        self._access_key = access_key
        self._region = region
        self._accountID = account_id
        self.__client = self.create_client()

    def create_client(self) -> Union[None, boto3.client]:
        try:
            client = boto3.client('rds', region_name=self._region, aws_access_key_id=self._access_id,
                                  aws_secret_access_key=self._access_key)
        except Exception as err:
            logging.error(f'AWS boto3 rds create client error:{err}')
            client = None
        return client

    def get_db_clusters(self) -> List[Dict[str, Any]]:
        """
        https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/rds.html#RDS.Client.describe_db_clusters
        :return:
        """
        try:
            response = self.__client.describe_db_clusters(MaxRecords=100)
            clusters = response.get('DBClusters')
            if not clusters: return []
            rds_list = list(map(self._format_cluster_data, clusters))
        except Exception as err:
            logging.error(f'get aws rds error, {err}')
            return []
        return rds_list

    def _format_cluster_data(self, data: dict) -> Dict[str, Any]:
        res: Dict[str, Any] = {}
        res["instance_id"] = data.get("DBClusterIdentifier")
        res["region"] = self._region
        res["zone"] = ",".join(data.get("AvailabilityZones"))
        res["name"] = data.get("DBClusterIdentifier")
        res["state"] = "运行中" if data.get("Status") == "available" else data.get("Status")
        res["db_class"] = ""
        res["db_engine"] = data.get("Engine")
        res["db_version"] = data.get("EngineVersion")
        # 集群地址
        cluster_write_endpoint = data.get("Endpoint")
        cluster_read_endpoint = data.get("ReaderEndpoint")
        res["db_address"] = {"items": [
            {
                "type": "auto_dns",
                "port": data.get("Port"),
                "ip": "",
                "domain": cluster_read_endpoint,
                "endpoint_type": "read",
            },
            {
                "type": "auto_dns",
                "port": data.get("Port"),
                "ip": "",
                "domain": cluster_write_endpoint,
                "endpoint_type": "write",
            }
        ]}
        #  集群下的节点实例信息
        res["db_instance_info"] = self.get_instnace_info(res["name"])
        return res

    def get_instnace_info(self, dbname: str):
        """
        AWS Aurora 根据DBName获取组下面的节点详细信息
        :param dbname:
        :return:
        """
        try:
            response = self.__client.describe_db_instances(Filters=[{"Name": "db-cluster-id", "Values": [f"{dbname}"]}])
            instances = response.get("DBInstances")
            if not instances: return []
            res = list(map(self._format_instance_data, instances))
        except Exception as err:
            logging.error(f"get aws rds aurora instance info error: {err}")
            return []
        return res

    @staticmethod
    def _format_instance_data(data: dict) -> Dict[str, str]:
        res: Dict[str, str] = {}
        res["name"] = data.get("DBInstanceIdentifier")
        res["instance_class"] = data.get("DBInstanceClass")
        res["instance_engine"] = data.get("Engine")
        # res["instance_status"] = data.get("DBInstanceStatus")
        res["instance_status"] = "运行中" if data.get("DBInstanceStatus") == "available" else data.get(
            "DBInstanceStatus")
        res["instance_user"] = data.get("MasterUsername")
        res["instance_addr"] = data["Endpoint"]["Address"]
        res["instance_port"] = data["Endpoint"]["Port"]
        # res["instance_create_time"] = data.get("InstanceCreateTime")
        res["instance_security_groups"] = data.get("VpcSecurityGroups")
        res["instance_paramter_groups"] = data.get("DBParameterGroups")
        res["instance_multiAZ"] = data.get("MultiAZ")
        return res

    def sync_cmdb(self, cloud_name: Optional[str] = 'aws', resource_type: Optional[str] = 'mysql') -> Tuple[
        bool, str]:
        # 获取数据
        all_rds_list: List[dict] = self.get_db_clusters()
        if not all_rds_list: return False, "RDS列表为空"
        # 更新资源
        ret_state, ret_msg = mysql_task(account_id=self._accountID, cloud_name=cloud_name, rows=all_rds_list)
        # 标记过期
        mark_expired(resource_type=resource_type, account_id=self._accountID)

        return ret_state, ret_msg


if __name__ == '__main__':
    pass
