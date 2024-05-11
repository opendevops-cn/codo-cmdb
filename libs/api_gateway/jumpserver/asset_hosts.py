# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/4/25
# @Description: 主机资产

from typing import *

from libs.api_gateway.jumpserver.base import JumpServerBaseAPI


class AssetHostsAPI(JumpServerBaseAPI):
    """主机资产API"""

    def get(self, address: str = None, id: str = None, name: str = None) -> \
            List[dict]:
        """
        查询主机资产
        :param address: IP地址
        :param id:
        :param name:
        :return:
        """
        params = {}
        if id is not None:
            params['id'] = id
        if address is not None:
            params['address'] = address
        if name is not None:
            params['name'] = name
        return self.send_request(method='get',
                                 url=f'{self.base_url}/api/v1/assets/assets/',
                                 params=params)

    def create(self, **kwargs):
        """
        创建主机资产
        :param kwargs:
        :return:
        """
        name = kwargs.get('name')
        address = kwargs.get('address')
        platform = kwargs.get('platform', 1)  # '1'：Linux '5'：Windows

        nodes = kwargs.get('nodes')
        protocols = kwargs.get('protocols')
        if not all([name, address, platform, nodes]):
            raise ValueError(f'参数异常：{name}, {address}, {platform}, {nodes}')

        if not protocols:
            protocols = [
                {
                    "name": "ssh",
                    "port": 36001
                },
                {
                    "name": "sftp",
                    "port": 36001
                }
            ]
        data = dict(name=name, address=address, nodes=nodes,
                    protocols=protocols,
                    platform=platform)
        return self.send_request(method='post',
                                 url=f'{self.base_url}/api/v1/assets/hosts/',
                                 data=data)

    def delete(self, asset_id: str = None) -> List[dict]:
        """
        删除主机资产
        :param asset_id: 资产id
        :return:
        """
        assert asset_id is not None, '资产id不能为空'
        return self.send_request(method='delete',
                                 url=f'{self.base_url}/api/v1/assets/hosts/{asset_id}/')


if __name__ == '__main__':
    pass