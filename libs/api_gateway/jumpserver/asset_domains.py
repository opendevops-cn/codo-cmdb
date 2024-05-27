# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/5/20
# @Description: 网域列表

import logging
from typing import *

from libs.api_gateway.jumpserver.base import JumpServerBaseAPI


class AssetsDomainsAPI(JumpServerBaseAPI):

    def get(self, name: str = None) -> List[Dict]:
        """
        根据网域名称搜素
        """
        params = {}
        if name is not None:
            params.update(name=name)
        return self.send_request(method='get', url=f'{self.base_url}/api/v1/assets/domains/', params=params)


if __name__ == '__main__':
    pass




