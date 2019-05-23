#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 7/17/2018 9:41 AM
# @Author  : Fred Yang
# @File    : qcloud_api.py
# @Role    : 腾讯云API操作接口

import hmac
import hashlib
import base64
from urllib import parse

class ApiOper(object):
    """
        说明：
            腾讯云API的签名要进行：构造参数字典->对dict排序->拼接sign->对sign编码->拼接完成最终url->完成调用

        使用：
            构建参数字典部分通过其余脚本传参进来（如下例子）
            def get_dict():
                keydict = {
                    'Action': 'GetCdbExportLogUrl',
                    'Timestamp': str(int(time.time())),
                    'Nonce': str(int(random.random() * 1000)),
                    'Region': 'ap-shanghai',
                    'SecretId': TX_INFO['SecretId'],
                    # 'SignatureMethod': SignatureMethod,
                    'cdbInstanceId': 'cdb-extlv472',
                    'type': 'coldbackup'
                }
                return keydict
    """

    @staticmethod
    def sort_dic(keydict):
        """
        对字典进行拼接
        :param keydict:
        :return: 返回排序后的列表
        """
        sortlist = sorted(zip(keydict.keys(), keydict.values()))
        return sortlist

    @staticmethod
    def get_str_sign(sortlist, api_url):
        """
        将排序后的列表进行字符串拼接
        :param sortlist:
        :return: 拼接后的字符串
        """
        sign_str_init = ''
        for value in sortlist:
            sign_str_init += value[0] + '=' + value[1] + '&'
        sign_str = 'GET' + api_url + sign_str_init[:-1]
        return sign_str, sign_str_init

    @staticmethod
    def get_signature(sign_str,secret_key):
        """
        生成签名
        :param sign_str:
        :param secretkey:
        :return:签名字符串
        """
        secretkey = secret_key
        signature = bytes(sign_str, encoding='utf-8')
        secretkey = bytes(secretkey, encoding='utf-8')
        my_sign = hmac.new(secretkey, signature, hashlib.sha1).digest()
        my_sign = base64.b64encode(my_sign)
        return my_sign

    @staticmethod
    def encode_signature( my_sign):
        """
        对签名编码
        :param my_sign:
        :return: 编码后的签名串
        """
        result_sign = parse.quote(my_sign)
        return result_sign

    @staticmethod
    def get_result_url(sign_str, result_sign,api_url):
        """
        完成最终url拼接
        :param result_sign:
        :return: 最终url
        """
        result_url = 'https://' + api_url + sign_str + 'Signature=' + result_sign
        return result_url

    @staticmethod
    def run(keydict, api_url,secret_key):
        # 获取请求参数dict(使用脚本传进来)
        # 对参数dict进行排序
        sortlist = ApiOper.sort_dic(keydict)
        # 获取拼接后的sign字符串
        sign_str, sign_str_int = ApiOper.get_str_sign(sortlist, api_url)
        # 获取签名
        my_sign = ApiOper.get_signature(sign_str,secret_key)
        # 对签名串进行编码
        result_sign = ApiOper.encode_signature(my_sign)
        # 获取最终请求url
        result_url = ApiOper.get_result_url(sign_str_int, result_sign,api_url)
        return result_url
