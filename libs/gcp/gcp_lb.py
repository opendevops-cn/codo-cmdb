# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/4/11
# @Description: 谷歌云负载均衡
from typing import *
import logging

from google.oauth2 import service_account
from google.cloud import compute_v1

from models.models_utils import lb_task, mark_expired


class GCPLB:
    def __init__(self, project_id: str, account_path: str, region: str,
                 account_id: str):
        self.cloud_name = 'gcp'
        self.page_size = 100  # 分页查询时设置的每页行数。最大值：100 默认值：10
        self._region = region
        self.project_id = project_id
        self._account_id = account_id
        self.__credentials = service_account.Credentials.from_service_account_file(
            account_path)
        self.client = compute_v1.UrlMapsClient(
            credentials=self.__credentials)

    def list_url_maps(self):
        """
        路由映射
        """
        clbs = list()
        try:
            request = compute_v1.AggregatedListUrlMapsRequest()
            request.project = self.project_id
            request.max_results = self.page_size
            page_result = self.client.aggregated_list(request)
            for region, response in page_result:
                url_maps = response.url_maps
                if not url_maps:
                    continue
                clbs.extend([self.handle_data(data) for data in url_maps])
        except Exception as e:
            logging.error(
                f'调用谷歌云路由映射获取lb异常. list_url_maps: {self._account_id} -- {e}')

        return clbs

    def list_backend_service(self):
        """
        后端服务
        """
        clbs = list()
        client = compute_v1.BackendServicesClient(
            credentials=self.__credentials)
        request = compute_v1.AggregatedListBackendServicesRequest()
        request.project = self.project_id
        request.max_results = self.page_size
        page_result = client.aggregated_list(request)
        for region, response in page_result:
            backend_services = response.backend_services
            if not backend_services:
                continue
            clbs.extend([self.handle_data(data) for data in backend_services])
        return clbs

    @staticmethod
    def handle_data(data) -> Dict[str, Any]:
        """
        处理数据
        """
        res: Dict[str, Any] = dict()
        res['type'] = 'clb'
        res['name'] = data.name
        res['instance_id'] = data.name
        res['create_time'] = data.creation_timestamp
        res['lb_vip'] = ''
        res['region'] = data.region.split('/')[-1]
        res['zone'] = ''
        res['status'] = '运行中'
        res['dns_name'] = ''
        res['endpoint_type'] = ''
        res['ext_info'] = {
            "vpc_id": '',
            "lb_vips": '',
            "ip_version": '',
            "charge_type": ''
        }
        return res

    def sync_cmdb(self, cloud_name: Optional[str] = 'gcp',
                  resource_type: Optional[str] = 'lb') -> Tuple[
        bool, str]:
        """
        同步到DB
        :param cloud_name:
        :param resource_type:
        :return:
        """
        clbs: List[dict] = self.list_url_maps()
        if not clbs:
            return False, "clb列表为空"
        # 更新资源
        ret_state, ret_msg = lb_task(account_id=self._account_id,
                                     cloud_name=cloud_name, rows=clbs)
        # 标记过期
        mark_expired(resource_type=resource_type, account_id=self._account_id)

        return ret_state, ret_msg


if __name__ == '__main__':
    pass
