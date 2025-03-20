# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/4/9
# @Description: 谷歌云mysql
from typing import List, Dict, Any, Optional, Tuple
import logging
from dataclasses import dataclass

from googleapiclient import discovery
from google.oauth2 import service_account
from google.cloud import compute_v1

from models.models_utils import mark_expired, mysql_task

# https://cloud.google.com/sql/docs/mysql/admin-api/rest/v1beta4/instances#SqlInstanceType
InstanceMapping = {
    "SQL_INSTANCE_TYPE_UNSPECIFIED": "Unknown",
    "CLOUD_SQL_INSTANCE": "单节点",
    "ON_PREMISES_INSTANCE": "非云实例",
    "READ_REPLICA_INSTANCE": "只读节点",
}

StateMapping = {
    "SQL_INSTANCE_STATE_UNSPECIFIED": "Unknown",
    "RUNNABLE": "运行中",
    "SUSPENDED": "不可用",
    "PENDING_DELETE": "删除中",
    "PENDING_CREATE": "创建中",
    "MAINTENANCE": "维护中",
    "FAILED": "错误"
}

@dataclass
class DBAddress:
    """数据库地址配置"""
    type: str
    ip: str
    domain: str = ""
    port: str = "3306"


class GCPCDB:
    def __init__(self, project_id: str, account_path: str, region: str,
                 account_id: str):
        self.cloud_name = 'gcp'
        self.page_size = 100  # 分页查询时设置的每页行数
        self._region = region
        self.project_id = project_id
        self._account_id = account_id
        self.__credentials = service_account.Credentials.from_service_account_file(
            account_path)
        self.client = self.client = discovery.build('sqladmin', 'v1',
                                                    credentials=self.__credentials)

    def list_instances(self, page_token):
        """
        查询mysql实例信息
        E.g: https://cloud.google.com/sql/docs/mysql/admin-api/rest/v1/instances/list
        :return:
        """
        req = self.client.instances().list(project=self.project_id,
                                           maxResults=self.page_size,
                                           pageToken=page_token)
        resp = req.execute()
        return resp

    def get_vpc_by_network(self, network: str):
        """
        获取vpc
        """
        client = compute_v1.NetworksClient(
            credentials=self.__credentials)
        request = compute_v1.GetNetworkRequest(network=network, project=self.project_id)
        response = client.get(request=request)
        return response

    def get_vpc_id(self, data: Dict[str, Any]) -> str:
        """
        查询vpc_id
        """
        try:
            private_network = data.get('settings', {}).get('ipConfiguration', {}).get('privateNetwork')
            if not private_network:
                return ""
            if "/" not in private_network:
                return ""
            network_name = private_network.split('/')[-1]
            vpc = self.get_vpc_by_network(network_name)
            return str(vpc.id)
        except Exception as e:
            logging.error(f'GCP CDB 获取vpc失败 set_vpc_id: {self._account_id} -- {e}')
            return ""


    def handle_data(self, data) -> Dict[str, Any]:
        """
        处理数据
        :param data:
        :return:
        """
        res: Dict[str, Any] = dict()
        try:
            res["instance_id"] = data['name']
            res["name"] = data['name']
            res["create_time"] = data['createTime']
            res['region'] = data.get('region', '')
            res['db_class'] = ""
            res['db_engine'] = "MySQL"
            res["db_version"] = '.'.join(
                data.get('databaseVersion', '').split('_')[1::])
            res['state'] = StateMapping.get(data.get('state', 'unknown'), '未知')
            res["vpc_id"] = self.get_vpc_id(data)
            res['zone'] = data.get('gceZone', '')
            res['network_type'] = "专有网络"
            db_address = self.__format_db_address(data.get('ipAddresses'))
            res['db_address'] = dict(items=db_address)
            res['ext_info'] = {"connection_name": data.get('connectionName', ''),
                               "data_disk_size_gb": data.get('settings', {}).get('dataDiskSizeGb', 0)
                               }

        except Exception as e:
            logging.error(
                f'谷歌云cdb handle data err: {self._account_id} -- {e}')

        return res

    @staticmethod
    def __format_db_address(ip_addresses: List[Dict[str, Any]]) ->  List[Dict[str, str]]:
        """格式化数据库地址

        Args:
            ip_addresses: IP地址列表
                [
                    {"type": "PRIMARY", "ipAddress": "1.1.1.1"},
                    {"type": "PRIVATE", "ipAddress": "10.0.0.1"}
                ]

        Returns:
            List[Dict[str, str]]: 格式化后的地址列表
        """
        # 地址类型映射
        if not ip_addresses:
            return []
        address_type_map = {
            "PRIMARY": "public",
            "PRIVATE": "private"
        }
        return [
            DBAddress(
                type=address_type_map.get(addr.get("type", ""), "unknown"),
                ip=addr.get("ipAddress", "")
            ).__dict__
            for addr in ip_addresses
            if addr.get("type") in address_type_map
        ]

    def get_all_instances(self):
        cdbs = list()
        try:
            page_token = ''
            while True:
                resp = self.list_instances(page_token=page_token)
                next_page_token = resp.get('nextPageToken')
                items = resp.get('items')
                if not items:
                    break
                cdbs.extend([self.handle_data(item) for item in items])
                if not next_page_token:
                    break
                page_token = next_page_token
        except Exception as e:
            logging.error(
                f'谷歌云cdb调用失败 get_all_instances err: {self._account_id} -- {e}')
        return cdbs

    def sync_cmdb(self, cloud_name: Optional[str] = 'gcp',
                  resource_type: Optional[str] = 'mysql') -> Tuple[
        bool, str]:
        """
        同步到DB
        :param cloud_name:
        :param resource_type:
        :return:
        """
        cdbs: List[dict] = self.get_all_instances()
        if not cdbs: return False, "CDB列表为空"
        # 更新资源
        ret_state, ret_msg = mysql_task(account_id=self._account_id,
                                        cloud_name=cloud_name, rows=cdbs)
        # 标记过期
        mark_expired(resource_type=resource_type, account_id=self._account_id)

        return ret_state, ret_msg


if __name__ == '__main__':
    pass
