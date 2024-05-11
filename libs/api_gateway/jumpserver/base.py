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
        self.jmss_dict = app_settings[const.JMS_CONFIG_ITEM]
        self.base_url = self.jmss_dict[const.DEFAULT_JMS_KEY][const.JMS_API_BASE_URL]
        self.key_id = self.jmss_dict[const.DEFAULT_JMS_KEY][const.JMS_API_KEY_ID]
        self.secret = self.jmss_dict[const.DEFAULT_JMS_KEY][const.JMS_API_KEY_SECRET]
        self.timeout = timeout

    @property
    def auth(self):
        signature_headers = ['(request-target)', 'accept', 'date']
        auth = requests_auth.HTTPSignatureAuth(key_id=self.key_id,
                                               secret=self.secret,
                                               algorithm='hmac-sha256',
                                               headers=signature_headers)
        return auth

    @property
    def headers(self):
        headers = {
            'Accept': 'application/json',
            'X-JMS-ORG': '00000000-0000-0000-0000-000000000002',  # Default组织
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
            response = getattr(requests, method.lower())(url=url,
                                                         params=params,
                                                         headers=headers,
                                                         auth=auth,
                                                         json=data)
            response.raise_for_status()
            if response.status_code == 204:  # delete 操作
                return response.ok
            return response.json()
        except requests.RequestException as e:
            logging.error(
                f"请求JumpSever发生异常: {e}, url: {url}, method: {method}, response: {response.text}")
