#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/6/14 14:27
# @Author  : Fred Yangxiaofei
# @File    : huawei_api.py
# @Role    : 说明脚本功能




#encoding=utf-8
import json
from openstack import connection
region= "cn-east-2"    # example: region = "cn-north-1"  cn-east-2
projectId = "1d33e8b23fb94278beaeedf2853501ad"
cloud = "myhuaweicloud.com"   # cdn use: cloud = "myhwclouds.com"

AK = ""
SK = ""

conn = connection.Connection(
              project_id=projectId,
              cloud=cloud,
              region=region,
              ak = AK,
              sk = SK)

def test_compute():
    # i = 1
    # while True:
    #     servers = conn.compute.servers(limit=i)
    #     for server in servers:
    #         print(server)
    #         asset_data = dict()
    #         if not server: break
    #
    #         i += 1
    #         if server.addresses:
    #             asset_data['hostname'] = server.name
    #             #
    #             ip_info = server.addresses
    #             for k, v in ip_info.items():
    #                 for i in v:
    #                     # 这是弹性IP
    #                     if 'floating' in i.values():
    #                         public_ip = i.get('addr')
    #                     else:
    #                         private_ip = i.get('addr')
    #
    #             if public_ip:
    #                 asset_data['public_ip'] = public_ip
    #             else:
    #                 asset_data['public_ip'] = private_ip
    #             asset_data['instance_type'] = server.flavor.get('id')
    #             asset_data['instance_id'] = server.id
    #             asset_data['instance_status'] = server.status
    #             asset_data['region'] = server.availability_zone
    #             print(asset_data)
    #             yield asset_data
    #         else:
    #             break
    servers = conn.compute.servers(limit = 10)
    for server in servers:
        asset_data = dict()
        #主机名
        asset_data['hostname'] = server.name
        #IP地址
        #
        ip_info = server.addresses
        for k, v in ip_info.items():
            for i in v:
                if 'floating' in i.values():
                    public_ip = i.get('addr')
                else:
                    private_ip = i.get('addr')

        if public_ip:
            asset_data['public_ip'] = public_ip
        else:
            asset_data['public_ip'] = private_ip
        asset_data['instance_type'] = server.flavor.get('id')
        asset_data['instance_id'] = server.id
        asset_data['instance_status'] = server.status
        asset_data['region'] = server.availability_zone
        print(asset_data)

if __name__ == "__main__":
    test_compute()