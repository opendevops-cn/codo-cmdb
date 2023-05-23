#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2018/12/22 16:21
Desc    : Base Handler
"""

import json
import logging
from abc import ABC
from tornado.web import HTTPError
from websdk2.jwt_token import AuthToken, jwt
from websdk2.base_handler import BaseHandler as SDKBaseHandler


class BaseHandler(SDKBaseHandler, ABC):
    def __init__(self, *args, **kwargs):
        super(BaseHandler, self).__init__(*args, **kwargs)

    # 隐藏Key
    @staticmethod
    def hide_key(data) -> None:
        try:
            _body = json.loads(data["body"])
            if "access_key" in _body:
                _body["access_key"] = "***************"
            if "secret_key" in _body:
                _body["secret_key"] = "***************"
            if "ssh_key" in _body:
                _body["ssh_key"] = "***************"
            data["body"] = json.dumps(_body)
        except Exception as error:
            logging.error("hide_key error: {}".format(error))

    # def prepare(self):

    def prepare(self):
        self.check_xsrf_cookie()
        self.xsrf_token
        ### 验证客户端CSRF
        self.get_params_dict()
        # self.codo_csrf()

        ### 登陆验证
        self.codo_login()
        log_dict = {
            "host": self.request.host,
            "uri": self.request.uri,
            "method": self.request.method,
            "remote_ip": self.request.remote_ip,
            "User-Agent": self.request.headers.get("User-Agent", None),
            "params": {k: self.get_argument(k) for k in self.request.arguments},
            "body": self.request.body.decode("utf-8"),
        }
        # 判断是否存在body,如果body中存在access_key和secret_key的时候,换成***号
        if log_dict["body"]: self.hide_key(log_dict)
        # 非GET请求的日志都写数据库记录
        if self.request.method != "GET":
            logging.info(json.dumps(log_dict, indent=4, separators=(',', ':')))
            # 保存到数据库?
            pass

    # def get_current_nickname(self):
    #     return self.request.headers.get('Username', None)

    def codo_login(self):
        # 登陆验证
        auth_key = self.get_cookie('auth_key') if self.get_cookie("auth_key") else self.request.headers.get('auth-key')
        if not auth_key: auth_key = self.get_argument('auth_key', default=None, strip=True)

        # TODO 暂时不强制获取token
        if not auth_key: return

        if self.token_verify:
            auth_token = AuthToken()
            user_info = auth_token.decode_auth_token(auth_key)
        else:
            user_info = jwt.decode(auth_key, options={"verify_signature": False}).get('data')

        if not user_info: raise HTTPError(401, 'auth failed')

        self.user_id = user_info.get('user_id', None)
        self.username = user_info.get('username', None)
        self.nickname = user_info.get('nickname', None)
        self.email = user_info.get('email', None)
        self.is_super = user_info.get('is_superuser', False)

        if not self.user_id: raise HTTPError(401, 'auth failed')

        self.user_id = str(self.user_id)
        self.set_secure_cookie("user_id", self.user_id)
        self.set_secure_cookie("nickname", self.nickname)
        self.set_secure_cookie("username", self.username)
        self.set_secure_cookie("email", str(self.email))
        self.is_superuser = self.is_super
