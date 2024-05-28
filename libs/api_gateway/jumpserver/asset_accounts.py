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

    def post(self, **params) -> dict:
        """
        从模版添加创建账号
        """
        """
        """
        asset_id = params.get("asset_id")
        template = params.get("template_id")
        if not asset_id:
            raise ValueError("资产ID不能为空")
        if not template:
            raise ValueError("账号模版ID不能为空")
        data = {
            "asset": asset_id,
            "org_id": "00000000-0000-0000-0000-000000000002",
            "org_name": "Default",
            "template": template,
        }
        return self.send_request(method='post', url=f'{self.base_url}/api/v1/accounts/accounts/', data=data)


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

    def create(self, **params) -> dict:
        """
        创建账号推送
        """
        name = params.get("name")  # 推送名称
        accounts = params.get("accounts", [])  # 账号名称列表
        assets = params.get("assets", [])  # 资产ID列表
        secret_type = params.get("secret_type", "ssh_key")  # 密文类型
        secret_strategy = params.get("secret_strategy", "random")  # 密文策略
        ssh_key_change_strategy = params.get("ssh_key_change_strategy", "add")  # SSH 密钥更改方式
        if not all([accounts, assets, name]):
            raise ValueError(f"参数异常: accounts: {accounts}, assets: {assets}, name:{name}")
        data = dict(name=name, accounts=accounts, assets=assets, secret_type=secret_type,
                    secret_strategy=secret_strategy, ssh_key_change_strategy=ssh_key_change_strategy)
        return self.send_request(method='post', url=f'{self.base_url}/api/v1/accounts/push-account-automations/',
                                 data=data)


class AssetAccountTemplatesAPI(AssetAccountsAPI):
    """资产账户模版API"""
    def get(self, **params) -> List[str]:
        """
        查询账户模版列表
        """
        params.update(offset=0, limit=100)
        response = self.send_request(method='get', url=f'{self.base_url}/api/v1/accounts/account-templates/',
                                     params=params)

        return response['results']


class AssetAccountPush(AssetAccountsAPI):
    """账号推送手动执行"""
    def post(self, automation: str = None) -> dict:
        assert automation is not None, "账号推送ID不能为空"
        return self.send_request(method='post', url=f'{self.base_url}/api/v1/accounts/push-account-executions/',
                                 data={'automation': automation})


if __name__ == '__main__':
    pass