#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2021/1/19
Desc    : 加密方法
"""

from cryptography.fernet import Fernet


class MyCrypt:
    """
    usage: mc = MyCrypt()               实例化
        mc.my_encrypt('ceshi')          对字符串ceshi进行加密
        mc.my_decrypt('')               对密文进行解密
    """

    def __init__(self, key: bytes = b'tu6aXq3w7rFRJoUMgvMN45H7qwHIxOO9Vq11s3dzLRs='):
        # 这里密钥key 长度必须为16（AES-128）、24（AES-192）、或32（AES-256）Bytes 长度
        self.key = key
        self.f = Fernet(self.key)

    @property
    def create_key(self):
        return Fernet.generate_key()

    def my_encrypt(self, text: str):
        if isinstance(text, str): text = text.encode('utf-8')
        return self.f.encrypt(text).decode('utf-8')

    def my_decrypt(self, text: str):
        if isinstance(text, str): text = text.encode('utf-8')
        return self.f.decrypt(text).decode('utf-8')
    

mc = MyCrypt()


if __name__ == '__main__':
    # mc = MyCrypt()
    # print(mc.create_key)
    # print(mc.my_encrypt('ceshi'))
    # print(mc.my_decrypt("gAAAAABjjuJ3vzSd35-RhSG5Tcjg2VeHtBrwHbgXKcRHt4JvOe_4qKxwFCwjy-oMHKRVen4nHHDkR81OKxr3Bi0wB_EmMxeSmQ=="))
    pass
