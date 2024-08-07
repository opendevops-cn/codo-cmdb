# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/4/25
# @Description: 资产节点API
import logging
from typing import *

from libs.api_gateway.jumpserver.base import JumpServerBaseAPI


class AssetAPI(JumpServerBaseAPI):
    """资产节点API"""

    def get(self, name: str = None, is_fuzzy: bool = True, org_id: str = None) -> List[dict]:
        """
        查询节点
        :param name:
        :param is_fuzzy: 是否模糊查询
        :param org_id: 组织id
        :return:
        """
        params = {}
        if name is not None:
            params = {"search": name}

        result = self.send_request(method='get', url=f'{self.base_url}/api/v1/assets/nodes/', params=params,
                                   org_id=org_id)
        if not result:
            return []
        if is_fuzzy:
            return [item for item in result if item['full_value'] == name]
        return result

    def create(self, name: str = None, parent_id: str = None, org_id: str = None) -> List[dict]:
        """
        创建节点
        :param name: 节点名称
        :param parent_id: 父节点id
        :param org_id: 组织id
        :return:
        """
        assert name is not None, "节点名称不能为空"
        assert parent_id is not None, "父节点id不能为空"
        return self.send_request(method='post',
                                 url=f'{self.base_url}/api/v1/assets/nodes/{parent_id}/children/', org_id=org_id,
                                 data={"value": name})

    def delete(self, node_id: str = None, org_id: str = None) -> bool:
        """
        删除节点
        :param node_id: 节点id
        :org_id: 组织id
        :return:
        """
        assert node_id is not None, "节点id不能为空"
        return self.send_request(method='delete', org_id=org_id,
                                 url=f'{self.base_url}/api/v1/assets/nodes/{node_id}/')

    def update(self, node_id: str = None, org_id: str = None,  **kwargs) -> dict:
        """
        更新节点
        :param node_id: 节点id
        :org_id: 组织id
        """
        assert node_id is not None, "节点id不能为空"
        data = {}
        name = kwargs.get("name")
        value = kwargs.get("value")
        full_value = kwargs.get("full_value")
        if name:
            data["name"] = name
        if value:
            data['value'] = value
        if full_value:
            data['full_value'] = full_value

        return self.send_request(method='put', url=f'{self.base_url}/api/v1/assets/nodes/{node_id}/', data=data,
                                 org_id=org_id)


jms_asset_api = AssetAPI()

if __name__ == '__main__':
    pass
