# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/4/25
# @Description: 资产节点API
import logging
from typing import *

from libs.api_gateway.jumpserver.base import JumpServerBaseAPI


class AssetAPI(JumpServerBaseAPI):
    """资产节点API"""

    def get(self, name: str = None) -> List[dict]:
        """
        查询节点
        :param name:
        :return:
        """
        params = {}
        if name is not None:
            params = {"search": name}

        return self.send_request(method='get',
                                 url=f'{self.base_url}/api/v1/assets/nodes/',
                                 params=params)

    def create(self, name: str = None, parent_id: str = None) -> List[dict]:
        """
        创建节点
        :param name: 节点名称
        :param parent_id: 父节点id
        :return:
        """
        assert name is not None, "节点名称不能为空"
        assert parent_id is not None, "父节点id不能为空"
        return self.send_request(method='post',
                                 url=f'{self.base_url}/api/v1/assets/nodes/{parent_id}/children/',
                                 data={"value": name})

    def delete(self, node_id: str = None) -> bool:
        """
        删除节点
        :param node_id: 节点id
        :return:
        """
        assert node_id is not None, "节点id不能为空"
        return self.send_request(method='delete',
                                 url=f'{self.base_url}/api/v1/assets/nodes/{node_id}/')


if __name__ == '__main__':
    pass
