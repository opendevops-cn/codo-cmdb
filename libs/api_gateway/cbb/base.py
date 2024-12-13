# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/9/19
# @Description: Description

from typing import Tuple, Type
import logging
import time
import json
from functools import wraps

import requests

from libs.api_gateway.cbb.sign import Signer


def retry_on_exception(retries=2, delay=0.5, exceptions: Tuple[Type[Exception]] = (requests.RequestException,), ):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            e = None
            while attempts < retries:
                try:
                    return func(*args, **kwargs)
                except exceptions as ex:
                    logging.error(f"请求异常：{e}, 重试中, {delay}s后重试...")
                    time.sleep(delay)
                    attempts += 1
                    e = ex
            if e is not None:
                raise e
            else:
                raise Exception("请求异常")

        return wrapper

    return decorator


class CBBBaseAPI:
    """
    CBB API基类.
    """

    def __init__(self, signer: Signer, idip: str = None, game_appid: str = None):
        self.signer = signer
        self.headers = {"Content-Type": "application/json"}
        self.idip = idip or "http://cbb-common-preview.huanle.com"
        self.base_url = f"{self.idip}/idip/"
        self.game_appid = game_appid
        self.timeout = 5

    def sign_headers(self):
        return self.signer.gen_sign_header()

    @retry_on_exception(retries=2, delay=0.5, exceptions=(requests.RequestException,))
    def send_request(self, url: str, body: dict, method: str = "POST"):
        """
        封装请求.
        :param url: 请求地址.
        :param method: 请求方法，默认POST.
        :param body: 请求body.
        :return: {"head": {"errno": 0, "errmsg": "success"}, "body": {...}}  errno为0表示请求成功，否则表示请求失败.
        """
        json_body = json.dumps(body)
        self.headers.update(self.signer.gen_sign_header(body=json_body))
        response = requests.request(method, url, headers=self.headers, json=body, timeout=self.timeout)
        # HTTP 200 OK
        if response.status_code != 200:
            logging.error(f"CBB API请求失败, 请求地址：{url}, 请求方法：{method}, 请求body:{body}, 请求headers:{self.headers},"
                          f"响应状态码：{response.status_code}, 响应：{response.text}")
            raise requests.exceptions.RequestException(f"请求失败，CBB API返回状态码：{response.status_code}")

        resp = response.json()
        if resp.get("head", {}).get("errno") != 0:
            if resp.get("head", {}).get("errmsg") == "create collection first":
                logging.info("需要创建表结构，正在创建...")
                self.create_collection()
                # 抛出异常，重新请求一次
                raise requests.exceptions.RequestException("已创建表结构，重新请求")
            logging.error(f"CBB API请求失败, 请求地址：{url}, 请求方法：{method}, 请求body:{body}, 请求headers:{self.headers},返回值：{resp}")
            raise Exception(f"CBB API返回异常:{resp}")

        return resp

    def create_collection(self):
        """
        为区服列表相关的数据库创建索引
        这个接口在数据库表结构有变化时需要调用一次
        已有索引不会被删除
        如果数据表没建，upload相关接口会报create collection first，此时应该先调用这个接口
        """
        body = {
            "head": {"game_appid": self.game_appid, "cmd": 1009},
            "body": {}
        }
        url = f"{self.base_url}"
        return self.send_request(url, body)

