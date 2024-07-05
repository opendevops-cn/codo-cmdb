# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/7/4
# @Description: Description
from typing import *

from libs.api_gateway.jumpserver.base import JumpServerBaseAPI


class JumpServerOrgAPI(JumpServerBaseAPI):
    """组织API"""

    def get(self, name: str = None, offset=0, limit=100) -> List[dict]:
        """
        查询组织
        :return:
        """
        params = {}
        if name is not None:
            params['name'] = name
        params.update(offset=offset, limit=limit)
        return self.send_request(url=f"{self.base_url}/api/v1/orgs/orgs/",
                                 method="GET", params=params)

    def get_by_id(self, org_id: str) -> dict:
        """
        根据组织id查询组织
        :param org_id:
        :return:
        """
        return self.send_request(url=f"{self.base_url}/api/v1/orgs/orgs/{org_id}/",
                                 method="GET")

    def create(self, **kwargs) -> List[dict]:
        """
        创建组织
        :return:
        """
        name = kwargs.get('name')
        assert name, f"参数校验异常，请检查参数: name: {name}"
        data = {'name': name}
        return self.send_request(method='post', data=data,
                                 url=f'{self.base_url}/api/v1/orgs/orgs/')


jms_org_api = JumpServerOrgAPI()

if __name__ == '__main__':
    pass






