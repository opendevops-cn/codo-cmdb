# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/4/25
# @Description: 资产授权
import logging
from typing import *

from libs.api_gateway.jumpserver.base import JumpServerBaseAPI


class AssetPermissionsAPI(JumpServerBaseAPI):
    """资产授权API"""

    def get(self, name: str = None,  org_id: str = None) -> List[dict]:
        params = {}
        if name is not None:
            params['name'] = name

        return self.send_request(url=f"{self.base_url}/api/v1/perms/asset-permissions/",
                                 method="GET", params=params, org_id=org_id)

    def create(self, **kwargs) -> List[dict]:
        """
        创建资产授权
        accounts: "@ALL" ：所有账号
                        "@SPEC"：指定账号
                        "@INPUT"：手动账号
                        "@USER"：同名账号
        actions: 默认：all，可选值：[ all, connect, upload_file, download_file,
        updownload, clipboard_copy, clipboard_paste, clipboard_copy_paste ]

        #执行账户模版
        # "accounts": [
        #     "@SPEC",
        #     "administrator",
        #     "%a765e187-a648-4b24-b354-0d7194ac519a"  % + 模版id
        # ],

        :param kwargs:
        :return:
        """
        name = kwargs.get("name")
        user_groups = kwargs.get("user_groups", [])  # 用户组id String[]
        users = kwargs.get("users", [])  # 用户id String[]
        nodes = kwargs.get("nodes", [])  # 节点id String[]
        assets = kwargs.get("assets", [])  # 资产id String []
        accounts = kwargs.get("accounts", [])
        org_id = kwargs.get("org_id",  None)
        date_start = kwargs.get("date_start", None)
        date_expired = kwargs.get("date_expired", None)
        assert accounts is not None, "账号模版ID不能为空"  # 选择模板添加时，会自动创建资产下不存在的账号并推送
        actions = kwargs.get("actions", ["connect", "copy", "paste"])
        data = dict(name=name, user_groups=user_groups, nodes=nodes, assets=assets,
                    accounts=accounts, actions=actions, users=users)
        if date_start:
            data.update(date_start=date_start)
        if date_expired:
            data.update(date_expired=date_expired)
        return self.send_request(method='post', data=data, org_id=org_id,
                                 url=f"{self.base_url}/api/v1/perms/asset-permissions/")

    def delete(self, assets_permissions_id: str = None, org_id: str = None) -> List[dict]:
        """
        删除资产授权
        :param assets_permissions_id: 资产授权id'
        :param org_id: 组织id
        :return:
        """
        assert assets_permissions_id is not None, "资产授权id不能为空"
        return self.send_request(method='delete', org_id=org_id,
                                 url=f"{self.base_url}/api/v1/perms/asset-permissions/{assets_permissions_id}/")

    def update(self, **kwargs) -> List[dict]:
        """
        更新资产授权
        :param kwargs:
        :return:
        """
        assets_permissions_id = kwargs.get("assets_permissions_id")
        assert assets_permissions_id is not None, "资产id不能为空"
        name = kwargs.get("name")
        user_groups = kwargs.get("user_groups", [])  # 用户组id String[]
        users = kwargs.get("users", [])  # 用户id String[]
        nodes = kwargs.get("nodes", [])  # 节点id String[]
        assets = kwargs.get("assets", [])  # 资产id String []
        accounts = kwargs.get("accounts", ['@ALL'])
        actions = kwargs.get("actions", [])
        org_id = kwargs.get("org_id", None)
        data = {}
        if user_groups:
            data["user_groups"] = user_groups
        if users:
            data["users"] = users
        if nodes:
            data["nodes"] = nodes
        if assets:
            data["assets"] = assets
        if actions:
            data["actions"] = actions
        if accounts:
            data["accounts"] = accounts
        if name:
            data["name"] = name

        return self.send_request('put', data=data, org_id=org_id,
                                 url=f"{self.base_url}/api/v1/perms/asset-permissions/{assets_permissions_id}/")


jms_asset_permission_api = AssetPermissionsAPI()

if __name__ == '__main__':
    pass
