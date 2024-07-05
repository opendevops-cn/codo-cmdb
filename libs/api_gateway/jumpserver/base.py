# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/4/25
# @Description: Description

from datetime import datetime
import logging
import time
from functools import wraps
from typing import Type, Tuple

import requests
from httpsig import requests_auth
from websdk2.consts import const

from settings import settings as app_settings


def retry_on_exception(retries=3, delay=0.5, exceptions: Tuple[Type[Exception]] = (requests.RequestException,), ):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < retries:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    logging.error(f"请求异常：{e}, 重试中, {delay}s后重试...")
                    time.sleep(delay)
                    attempts += 1
            return False
        return wrapper
    return decorator


class JumpServerBaseAPI:

    DEFAULT_ORG_ID = '00000000-0000-0000-0000-000000000002'

    def __init__(self, timeout=30, org_id=None):
        self.jms_dict = app_settings[const.JMS_CONFIG_ITEM]
        if not self.jms_dict:
            raise ValueError('JMS配置为空')
        self.base_url = self.jms_dict[const.DEFAULT_JMS_KEY][const.JMS_API_BASE_URL]
        self.key_id = self.jms_dict[const.DEFAULT_JMS_KEY][const.JMS_API_KEY_ID]
        self.secret = self.jms_dict[const.DEFAULT_JMS_KEY][const.JMS_API_KEY_SECRET]
        self.timeout = timeout
        self.org_id = org_id or self.DEFAULT_ORG_ID

    @property
    def auth(self):
        signature_headers = ['(request-target)', 'accept', 'date']
        return requests_auth.HTTPSignatureAuth(key_id=self.key_id, secret=self.secret, algorithm='hmac-sha256',
                                               headers=signature_headers)

    @property
    def headers(self):
        return {
            'Accept': 'application/json',
            'X-JMS-ORG': self.org_id,
            'Date': datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT'),
        }

    @retry_on_exception()
    def send_request(self, method, url, params=None, data=None, headers=None, auth=None, org_id=None):
        """
        """
        if headers is None:
            headers = self.headers

        if auth is None:
            auth = self.auth

        if org_id is not None:
            headers['X-JMS-ORG'] = org_id

        try:
            response = getattr(requests, method.lower())(url=url, params=params, headers=headers, auth=auth, json=data,
                                                         timeout=self.timeout)
            response.raise_for_status()
            return response.json() if response.status_code != 204 else response.ok
        except requests.RequestException as e:
            logging.error(f"请求JumpSever发生异常: {e}, url: {url}, params:{params}, data:{data}, method: {method}")
            raise
