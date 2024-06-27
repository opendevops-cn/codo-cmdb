# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/4/25
# @Description: Description

from datetime import datetime
import logging

import requests
from httpsig import requests_auth
from websdk2.consts import const

from settings import settings as app_settings


class JumpServerBaseAPI:

    def __init__(self, timeout=30):
        self.jms_dict = app_settings[const.JMS_CONFIG_ITEM]
        if not self.jms_dict:
            raise ValueError('JMS配置为空')
        self.base_url = self.jms_dict[const.DEFAULT_JMS_KEY][const.JMS_API_BASE_URL]
        self.key_id = self.jms_dict[const.DEFAULT_JMS_KEY][const.JMS_API_KEY_ID]
        self.secret = self.jms_dict[const.DEFAULT_JMS_KEY][const.JMS_API_KEY_SECRET]
        self.timeout = timeout
        self.org_id = '00000000-0000-0000-0000-000000000002'  # Default组织ID

    @property
    def auth(self):
        signature_headers = ['(request-target)', 'accept', 'date']
        auth = requests_auth.HTTPSignatureAuth(key_id=self.key_id, secret=self.secret, algorithm='hmac-sha256',
                                               headers=signature_headers)
        return auth

    @property
    def headers(self):
        headers = {
            'Accept': 'application/json',
            'X-JMS-ORG': self.org_id,
            'Date': datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT'),
        }
        return headers

    def send_request(self, method, url, params=None, data=None, headers=None,
                     auth=None):
        if headers is None:
            headers = self.headers
        if auth is None:
            auth = self.auth
        try:
            response = getattr(requests, method.lower())(url=url, params=params, headers=headers, auth=auth, json=data,
                                                         timeout=self.timeout)
            response.raise_for_status()
            if response.status_code == 204:  # delete 操作
                return response.ok
            return response.json()
        except requests.RequestException as e:
            logging.error(
                f"请求JumpSever发生异常: {e}, url: {url}, params:{params}, data:{data}, method: {method},"
                f" response: {response.text}")
            return