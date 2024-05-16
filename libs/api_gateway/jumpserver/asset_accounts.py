# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/5/16
# @Description: 资产账号API

import logging
from typing import *

from libs.api_gateway.jumpserver.base import JumpServerBaseAPI


class AssetAccountsAPI(JumpServerBaseAPI):
    """账号API"""

    def get(self, **params) -> List[str]:
        """
        账户列表
        """
        params.update(offset=0, limit=100)
        return self.send_request(method='get', url=f'{self.base_url}/api/v1/accounts/accounts/', params=params)


class AssetAccountPushAutomationsAPI(AssetAccountsAPI):
    """账号推送API"""

    def get(self, **params) -> List[str]:
        """
        账户列表
        """
        params.update(offset=0, limit=100)
        response = self.send_request(method='get', url=f'{self.base_url}/api/v1/accounts/push-account-automations/',
                                     params=params)
        result = set()
        for item in response['results']:
            accounts = item['accounts']
            for account in accounts:
                result.add(account)

        return list(result)


if __name__ == '__main__':
    pass