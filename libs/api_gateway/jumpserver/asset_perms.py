# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/4/25
# @Description: 资产授权
import logging
from typing import *

from libs.api_gateway.jumpserver.base import JumpServerBaseAPI


class AssetPermissionsAPI(JumpServerBaseAPI):
    """资产授权API"""

    def get(self, name: str = None) -> List[dict]:
        params = {}
        if name is not None:
            params['name'] = name

        return self.send_request(url=f"{self.base_url}/api/v1/perms/asset-permissions/",
                                 method="GET", params=params)

    def create(self, **kwargs) -> List[dict]:
        """
        创建资产授权
        accounts: "@ALL" ：所有账号
                        "@SPEC"：指定账号
                        "@INPUT"：手动账号
                        "@USER"：同名账号
        actions: 默认：all，可选值：[ all, connect, upload_file, download_file,
        updownload, clipboard_copy, clipboard_paste, clipboard_copy_paste ]

        :param kwargs:
        :return:
        """
        name = kwargs.get("name")
        user_groups = kwargs.get("user_groups", [])  # 用户组id String[]
        users = kwargs.get("users", [])  # 用户id String[]
        nodes = kwargs.get("nodes", [])  # 节点id String[]
        accounts = ['@ALL']
        actions = kwargs.get("actions", [])
        data = dict(name=name, user_groups=user_groups, nodes=nodes,
                    accounts=accounts, actions=actions, users=users)
        return self.send_request(method='post', data=data,
                                 url=f"{self.base_url}/api/v1/perms/asset-permissions/")

    def delete(self, assets_permissions_id: str = None) -> List[dict]:
        """
        删除资产授权
        :param assets_permissions_id: 资产授权id'
        :return:
        """
        assert assets_permissions_id is not None, "资产授权id不能为空"
        return self.send_request(method='delete',
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
        accounts = kwargs.get("accounts", ['@ALL'])
        actions = kwargs.get("actions", [])
        data = {}
        if user_groups:
            data["user_groups"] = user_groups
        if users:
            data["users"] = users
        if nodes:
            data["nodes"] = nodes
        if actions:
            data["actions"] = actions
        if accounts:
            data["accounts"] = accounts
        if name:
            data["name"] = name

        return self.send_request('put', data=data,
                                 url=f"{self.base_url}/api/v1/perms/asset-permissions/{assets_permissions_id}/")


if __name__ == '__main__':
    pass
