# -*- coding: utf-8 -*-
# @Author: Dongdong Liu
# @Date: 2024/9/19
# @Description: Sign module for CBB API Gateway
import hashlib
import random
import time
from typing import Dict, Any


class Signer:
    """
    签名类，用于生成签名字符串.
    """

    def __init__(self, secret: str, app_id: str) -> None:
        self.secret = secret
        self.app_id = app_id
        self._timestamp = self._get_current_timestamp()
        self._rnd = self._generate_randint()

    @property
    def rnd(self) -> int:
        """随机数."""
        return self._rnd

    @property
    def timestamp(self) -> int:
        """时间戳."""
        return self._timestamp

    @staticmethod
    def _get_current_timestamp() -> int:
        """当前时间戳."""
        return int(time.time())

    @staticmethod
    def _generate_randint() -> int:
        """生成随机数."""
        return random.randint(0, 999)

    def sign(self, body: str, tag: str = "") -> str:
        """
        生成签名字符串.
        :param body: json请求体.
        :param tag: 签名协议标签.
        :return: 签名后的字符串.
        """
        sign_str = f"{tag}{body}{self.timestamp}{self.rnd}{self.secret}"
        md5_sign_str = hashlib.md5(sign_str.encode()).hexdigest()
        return md5_sign_str

    def gen_sign_header(self, body: str, tag: str = "", version: str = "v1") -> Dict[str, Any]:
        """
        生成签名header.
        :param body: json请求体.
        :param tag: 签名协议标签.
        :param version: 保留字段，签名使用的协议版本，方便之后兼容.
        :return: 签名后的header.
        """
        sign_str = self.sign(body, tag)
        return {"cbb-sign-appid": self.app_id,
                "cbb-sign-time": str(self.timestamp),
                "cbb-sign-rnd": str(self.rnd),
                "cbb-sign": sign_str.replace("-", "").upper(),
                "cbb-sign-version": version}


if __name__ == '__main__':
    pass
