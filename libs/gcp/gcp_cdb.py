# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/4/9
# @Description: 谷歌云mysql
import json
from typing import *
import logging

from googleapiclient import discovery
from google.oauth2 import service_account

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
            res['region'] = data['region']
            res['db_class'] = ""
            res['db_engine'] = "MySQL"
            res["db_version"] = '.'.join(
                data['databaseVersion'].split('_')[1::])
            res['state'] = StateMapping.get(data['state'], '未知')
            res["vpc_id"] = data['settings']['ipConfiguration'][
                'privateNetwork']
            res['zone'] = data['gceZone']
            res['network_type'] = "专有网络"
            db_address = self.__format_db_address(data['ipAddresses'])
            res['db_address'] = dict(items=db_address)
            res['ext_info'] = {"connection_name": data['connectionName'],
                               "data_disk_size_gb": data['settings'][
                                   'dataDiskSizeGb']}
        except Exception as e:
            logging.error(
                f'谷歌云cdb handle data err: {self._account_id} -- {e}')

        return res

    def __format_db_address(self, ip_addresses: List[Dict[str, Any]]) -> List:
        """

        :param ip_addresses:
        :return:
        """
        items = []
        for ip_address in ip_addresses:
            if ip_address.get("type") == "PRIMARY":
                item = {
                    "type": "public",
                    "ip": ip_address.get('ipAddress'),
                    "domain": "",
                    "port": '3306'  # 默认为3306
                }
            elif ip_address.get("type") == "PRIVATE":
                item = {
                    "type": "private",
                    "ip": ip_address.get('ipAddress'),
                    "domain": "",
                    "port": '3306'
                }
            else:
                item = {}
            items.append(item)
        return items

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
