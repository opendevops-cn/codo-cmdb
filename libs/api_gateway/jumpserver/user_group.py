# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/4/25
# @Description: 同步codo权限分组到jumpserver
import logging
from typing import *

from libs.api_gateway.jumpserver.base import JumpServerBaseAPI


class UserGroupAPI(JumpServerBaseAPI):
    """用户组API"""

    def get(self, name: str = None) -> List[dict]:
        """
        查询用户组
        :param name:
        :return:
        """
        params = {}
        if name is not None:
            params = {'name': name}
        return self.send_request(method='get',
                                 url=f'{self.base_url}/api/v1/users/groups/',
                                 params=params)

    def create(self, name: str = None) -> List[dict]:
        """
        创建用户组
        :param name: 用户组名
        :return:
        """
        assert name is not None, "用户组名称不能为空"
        return self.send_request(method='post',
                                 url=f'{self.base_url}/api/v1/users/groups/',
                                 data={'name': name})

    def update(self, name: str, users: List[str] = None) -> List[dict]:
        """
        用户组添加用户
        :param name:  用户组名
        :param users: 用户列表元素为用户id e.g ['d71639eb-716b-4340-846d-5a51c1ffa62f']
        :return:
        """
        user_groups = self.get(name=name)
        if not user_groups:
            logging.error(f'用户组不存在: {name}')
        user_group = user_groups[0]
        user_group_id = user_group['id']
        data = {
            "id": user_group_id,  # 用户组id
            "name": name,
            "comment": user_group["comment"],
            "users": users,
            "labels": user_group['labels']
        }
        return self.send_request(method='put',
                                 url=f'{self.base_url}/api/v1/users/groups/{user_group_id}/',
                                 data=data)

    def delete(self, user_group_id: str = None) -> bool:
        """
        删除用户组
        :param user_group_id: 用户组id
        :return:
        """
        assert user_group_id is not None, "用户组id不能为空"
        return self.send_request(method='delete',
                                 url=f'{self.base_url}/api/v1/user/groups/{user_group_id}/')


if __name__ == '__main__':
    pass
