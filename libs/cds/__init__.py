#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: shenshuo
Date  : 2023/2/25
Desc  : 首都在线 API
"""

from urllib.parse import quote, urlencode
from hashlib import sha1
import json
import requests
import time
import base64
import hmac
import uuid
import logging


class CDSApi(object):

    def __init__(self, access_id: str, access_key: str, region: str, account_id: str):
        self._access_id = access_id
        self._access_key = access_key
        self._region = region
        self._account_id = account_id

    @staticmethod
    def percent_encode(txt):
        """将特殊转义字符替换"""
        res = quote(txt, '')
        res = res.replace('+', '%20')
        res = res.replace('*', '%2A')
        res = res.replace('%7E', '~')
        return res

    def get_signature(self, action, ak, access_key_secret, method, url, param=None):
        """
        @params: action: 接口动作
        @params: ak: ak值
        @params: access_key_secret: ak秘钥
        @params: method: 接口调用方法(POST/GET)
        @params: param: 接口调用Query中参数(非POST方法Body中参数)
        @params: url: 接口调用路径
        @return: 请求的url可直接调用
        """
        if param is None:
            param = {}
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        D = {
            'Action': action,
            'AccessKeyId': ak,
            'SignatureMethod': 'HMAC-SHA1',
            'SignatureNonce': str(uuid.uuid1()),
            'SignatureVersion': "1.0",
            "Timestamp": timestamp,
            'Version': '2019-08-08',
        }
        if param:
            D.update(param)
        # sortedD = sorted(D.items(), key=lambda x: x[0])
        canstring = ''
        for k, v in sorted(D.items(), key=lambda x: x[0]):
            canstring += '&' + self.percent_encode(k) + '=' + self.percent_encode(v)
        string_to_sign = method + '&%2F&' + self.percent_encode(canstring[1:])

        h = hmac.new(bytes(access_key_secret, encoding="utf-8"), bytes(string_to_sign, encoding="utf-8"), sha1)
        signature = base64.encodebytes(h.digest()).strip()
        D['Signature'] = signature
        url = url + '/?' + urlencode(D)
        return url

    def make_requests(self, method, params):
        url = self.get_signature(params["action"], self._access_id, self._access_key, params["method"], params["url"])
        body = {
            "PageNumber": 1,
            "PageSize": 9999
        }
        res = None
        for i in range(3):
            try:
                if method == "POST":
                    res = requests.post(url, json=body)
                elif method == "GET":
                    res = requests.get(url)
                else:
                    raise Exception(f"method:{method} not foud!")
                break
            except requests.exceptions.ConnectionError:
                time.sleep(3)
            if i == 2:
                logging.error("CDS API requests fail")
                raise Exception(res)
        result = json.loads(res.content)
        if result.get("Code") != "Success":
            logging.error(f"CDSAPI get all vm error. result:{result}")
            raise Exception(result)
        return result