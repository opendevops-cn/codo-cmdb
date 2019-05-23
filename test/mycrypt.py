#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/3/25 13:41
# @Author  : Fred Yangxiaofei
# @File    : mycrypt.py
# @Role    : 加密解密，测试用的，现在这个模块写到了websdk，暂且不用libs/这个

import base64
from Crypto.Cipher import AES


class MyCrypt():

    def __init__(self, key='HOrUmuJ4bCVG6EYu2docoRNNYSdDpJJw'):
        """
        Usage:
            #实例化
            mc = MyCrypt()
            #加密方法
            mc.my_encrypt('password')
            #解密方法
            mc.my_decrypt('ZpZjEcsqnySTz6UsXD/+TA==')
        :param key:
        """
        self.key = key

    # str不是16的倍数那就补足为16的倍数
    def add_to_16(self, value):
        while len(value) % 16 != 0:
            value += '\0'
        return str.encode(value)  # 返回bytes

    def my_encrypt(self, text):
        """
        加密方法
        :param text: 密码
        :return:
        """
        aes = AES.new(self.add_to_16(self.key), AES.MODE_ECB)
        # 先进行aes加密

        encrypt_aes = aes.encrypt(self.add_to_16(text))
        # 用base64转成字符串形式
        encrypted_text = str(base64.encodebytes(encrypt_aes), encoding='utf-8').replace('\n', '')# 执行加密并转码返回bytes
        # print('[INFO]: 你的加密为：{}'.format(encrypted_text))
        return encrypted_text
    def my_decrypt(self, text):
        """
        解密方法
        :param text: 加密后的密文
        :return:
        """
        # 初始化加密器
        aes = AES.new(self.add_to_16(self.key), AES.MODE_ECB)
        # 优先逆向解密base64成bytes
        base64_decrypted = base64.decodebytes(text.encode(encoding='utf-8'))
        # 执行解密密并转码返回str
        decrypted_text = str(aes.decrypt(base64_decrypted), encoding='utf-8').replace('\0', '')
        # print('[INFO]: 你的解密为：{}'.format(decrypted_text))
        return decrypted_text


if __name__ == '__main__':
    pass
    mc = MyCrypt()
    # mc.my_encrypt('password')
    #mc.my_decrypt('ZpZjEcsqnySTz6UsXD/+TA==')
    mc.my_decrypt('ZpZjEcsqnySTz6UsXD/+TA==')