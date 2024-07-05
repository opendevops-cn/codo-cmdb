# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/4/25
# @Description: 同步codo用户到jumpserver

from typing import *

from libs.api_gateway.jumpserver.base import JumpServerBaseAPI


__all__ = ['jms_user_api']


class UserAPI(JumpServerBaseAPI):
    """用户API"""

    def get(self, name: str = None, username: str = None, email: str = None, org_id: str = None) -> List[dict]:
        """
        查询堡垒机用户
        :return:
        """
        params = {}
        if name is not None:
            params['name'] = name
        if username is not None:
            params['username'] = username
        if email is not None:
            params['email'] = email
        return self.send_request(method='get', params=params, url=f'{self.base_url}/api/v1/users/users/', org_id=org_id)

    def create(self, **kwargs) -> List[dict]:
        """
        创建堡垒机用户
        :return:
        """
        name = kwargs.get('name')
        username = kwargs.get('username')
        email = kwargs.get('email')
        assert all([name, username,
                    email]), (
            f"参数校验异常，请检查参数: name: {name}, username: {username}, "
            f"email:{email}")

        data = {'name': name, 'username': username, 'email': email,
                'source': 'ldap'}
        return self.send_request(method='post', data=data, org_id=kwargs.pop('org_id', None),
                                 url=f'{self.base_url}/api/v1/users/users/')


jms_user_api = UserAPI()

if __name__ == '__main__':
    pass