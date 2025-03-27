# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/4/16
# @Description: 谷歌云防火墙
from typing import *
import logging

from google.oauth2 import service_account
from google.cloud import compute_v1

from models.models_utils import security_group_task, mark_expired, mark_expired_by_sync


class GCPSecurityGroup:
    def __init__(self, project_id: str, account_path: str, region: str,
                 account_id: str):
        self.cloud_name = 'gcp'
        self.page_size = 100  # 分页查询时设置的每页行数。最大值：100 默认值：10
        self._region = region
        self.project_id = project_id
        self._account_id = account_id
        self.account_path = account_path
        self.__credentials = service_account.Credentials.from_service_account_file(
            self.account_path)
        self.client = compute_v1.FirewallsClient(
            credentials=self.__credentials)

    def get_all_firewalls(self):
        """
        谷歌云防火墙策略
        """
        firewalls = list()
        try:
            request = compute_v1.ListFirewallsRequest()
            request.project = self.project_id
            request.max_results = self.page_size
            request.page_token = ''
            page_result = self.client.list(request=request)
            for response in page_result:
                firewalls.append(self.handle_data(response))
        except Exception as e:
            logging.error(
                f'谷歌云防火墙规则调用异常 get_all_firewalls: {self._account_id} -- {e}')
        return firewalls

    @staticmethod
    def handle_data(data) -> Dict[str, Any]:
        """
        处理数据
        """
        res: Dict[str, Any] = dict()
        res['instance_id'] = data.id
        res['network'] = data.network.split('/')[-1]
        res['security_group_name'] = data.name
        res['description'] = data.description
        res['region'] = ''
        res['create_time'] = data.creation_timestamp
        res['security_group_type'] = 'normal'
        res['ref_info'] = dict(items=[])
        direction = data.direction.lower()
        items = []
        if direction == 'ingress':
            # 入站规则
            for ip_address in data.source_ranges:
                item = dict(source_cidr_ip=ip_address)
                for allowed_item in data.allowed:
                    ip_protocol = allowed_item.I_p_protocol
                    item['ip_protocol'] = ip_protocol
                    item['security_group_id'] = data.id
                    item['source_group_name'] = ''
                    item['dest_group_name'] = ''
                    item['ipv6_source_cidr_ip'] = ''
                    item['dest_cidr_ip'] = ';'.join(data.target_tags)
                    item['ipv6_dest_cidr_ip'] = ''
                    item['policy'] = 'accept'
                    item[
                        'port_range'] = 'ALL' if ip_protocol == "all" else ";".join(
                        allowed_item.ports)
                    item['description'] = data.description
                    item['direction'] = direction
                    item['priority'] = data.priority
                    item['creation_time'] = data.creation_timestamp
                items.append(item)

        res['security_info'] = dict(items=items)
        return res

    def sync_cmdb(self, cloud_name: Optional[str] = 'gcp',
                  resource_type: Optional[str] = 'security_group') -> Tuple[
        bool, str]:
        """
        同步CMDB
        :param cloud_name:
        :param resource_type:
        :return:
        """
        firewalls = self.get_all_firewalls()

        if not firewalls:
            return False, "安全组列表为空"
        # 同步资源
        ret_state, ret_msg = security_group_task(account_id=self._account_id,
                                                 cloud_name=cloud_name,
                                                 rows=firewalls)

        # 标记过期
        # mark_expired(resource_type=resource_type, account_id=self._account_id)
        instance_ids = [firewall['instance_id'] for firewall in firewalls]
        mark_expired_by_sync(cloud_name=cloud_name, account_id=self._account_id, resource_type=resource_type,
                             instance_ids=instance_ids)

        return ret_state, ret_msg


if __name__ == '__main__':
    pass
