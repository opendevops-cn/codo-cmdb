#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/5/30 16:14
# @Author  : Fred Yangxiaofei
# @File    : aliyun_api_test.py
# @Role    : 阿里云获取资产信息官方示例，如果测试不通过请自行排除问题



from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.acs_exception.exceptions import ClientException
from aliyunsdkcore.acs_exception.exceptions import ServerException
from aliyunsdkecs.request.v20140526.DescribeInstancesRequest import DescribeInstancesRequest

client = AcsClient('<accessKeyId>', '<accessSecret>', 'cn-hangzhou')

request = DescribeInstancesRequest()
request.set_accept_format('json')

response = client.do_action_with_exception(request)
# python2:  print(response)
print(str(response, encoding='utf-8'))