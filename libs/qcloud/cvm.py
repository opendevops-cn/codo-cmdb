#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/5/10 16:37
# @Author  : Fred Yangxiaofei
# @File    : cvm.py
# @Role    : 获取腾讯云主机信息


import time
import random
import requests
import json
import re
from libs.qcloud.qcloud_api import ApiOper
from libs.db_context import DBContext
from libs.web_logs import ins_log
from opssdk.operate import MyCryptV2
from models.server import Server, ServerDetail, AssetConfigs, model_to_dict
import fire


class CVMApi():
    def __init__(self, access_id, access_key, region, default_admin_user):
        self.offset = '0'  # 偏移量,这里拼接的时候必须是字符串
        self.limit = '100'  # 官方默认是20，大于100需要设置偏移量再次请求：offset=100,offset={机器总数}
        self.access_id = access_id
        self.access_key = access_key
        self.region = region
        self.default_admin_user = default_admin_user  # 默认管理用户
        self.account = '腾讯云'  # 标记机器为腾讯云
        self.state = 'auto'  # 标记自动获取状态

    def get_server_url(self):
        """
        获取腾讯云机器的API拼接结果，get请求
        :return:
        """
        api_url = 'cvm.tencentcloudapi.com/?'
        keydict = {
            # 公共参数部分
            'Timestamp': str(int(time.time())),
            'Nonce': str(int(random.random() * 1000)),
            'Region': self.region,
            'SecretId': self.access_id,
            'Version': '2017-03-12',
            # 'SignatureMethod': SignatureMethod,
            # 接口参数部分
            'Action': 'DescribeInstances',
            'Offset': self.offset,  # 机器数量超过100需要用到偏移量
            'Limit': self.limit,
        }
        result_url = ApiOper.run(keydict, api_url, self.access_key)
        return result_url

    def get_result_data(self):
        """
        获取返回的数据
        :return:
        """
        result_url = self.get_server_url()
        response = requests.get(result_url)
        result_data = json.loads(response.text)
        if result_data['Response'].get('Error'):
            ins_log.read_log('error', '{}'.format(result_data['Response']))
            return False
        else:
            ret = result_data['Response']

        return ret

    def get_server_count(self):
        """
        获取主机总数量。如果机器数量大于limit限制就要用到offset偏移查询
        :return:  int
        """

        ret = self.get_result_data()
        if not ret:
            return False

        server_count = ret['TotalCount']
        return server_count

    def get_server_info(self):
        """
        获取QCloud服务器信息
        :return:
        """

        ret = self.get_result_data()
        if not ret:
            return False

        server_list = []

        server_info = ret['InstanceSet']
        for i in server_info:
            asset_data = dict()
            instance_id = i.get('InstanceId')
            instance_state = i.get('InstanceState')
            instance_type = i.get('InstanceType')
            cpu = i.get('CPU')
            memory = i.get('Memory')
            hostname = i.get('InstanceName')
            disk = i['SystemDisk'].get('DiskSize')
            try:
                private_ip = i['PrivateIpAddresses'][0]
            except (KeyError, TypeError):
                private_ip = 'Null'
            try:
                public_ip = i['PublicIpAddresses'][0]
            except (KeyError, TypeError):
                public_ip = private_ip  # 不存在公网就给私网IP
            os_type = i.get('OsName')
            region = i['Placement'].get('Zone')
            asset_data['region'] = region
            asset_data['instance_id'] = instance_id
            asset_data['instance_state'] = instance_state
            asset_data['instance_type'] = instance_type
            asset_data['cpu_cores'] = '{}Core'.format(cpu)
            asset_data['memory'] = '{}G'.format(memory)
            asset_data['hostname'] = hostname
            asset_data['disk'] = '{}G'.format(disk)
            asset_data['private_ip'] = private_ip
            asset_data['public_ip'] = public_ip
            asset_data['os_type'] = os_type
            # print(asset_data)
            server_list.append(asset_data)
            ins_log.read_log('info', '资产信息:{}'.format(asset_data))
        return server_list

    def sync_cmdb(self):
        """
        返回结果写入CMDB
        :return:
        """
        server_list = self.get_server_info()

        if not server_list:
            print('Not Fount Server Info')
            return False

        with DBContext('w') as session:
            for server in server_list:
                ip = server.get('public_ip')
                private_ip = server.get('private_ip')
                instance_id = server.get('instance_id', 'Null')
                hostname = server.get('hostname', instance_id)
                if not hostname.strip():
                    hostname = instance_id
                if re.search('syncserver', hostname):
                    hostname = '{}_{}'.format(hostname, private_ip)

                region = server.get('region', 'Null')
                instance_type = server.get('instance_type', 'Null')
                instance_state = server.get('instance_state', 'Null')
                cpu = server.get('cpu', 'Null')
                cpu_cores = server.get('cpu_cores', 'Null')
                memory = server.get('memory', 'Null')
                disk = server.get('disk', 'Null')
                os_type = server.get('os_type', 'Null')
                os_kernel = server.get('os_kernel', 'Null')
                sn = server.get('sn', 'Null')

                exist_hostname = session.query(Server).filter(Server.hostname == hostname).first()
                exist_ip = session.query(Server).filter(Server.ip == ip).first()

                if not exist_hostname and not exist_ip:
                    new_serve = Server(ip=ip, public_ip=ip, private_ip=private_ip, hostname=hostname, port=22,
                                       idc=self.account, region=region,
                                       state=self.state,
                                       admin_user=self.default_admin_user)
                    new_serve_detail = ServerDetail(ip=ip, instance_id=instance_id, instance_type=instance_type,
                                                    instance_state=instance_state, cpu=cpu, cpu_cores=cpu_cores,
                                                    memory=memory,
                                                    disk=disk, os_type=os_type, os_kernel=os_kernel, sn=sn)
                    session.add(new_serve)
                    session.add(new_serve_detail)
                else:
                    session.query(Server).filter(Server.hostname == hostname).update(
                        {Server.ip: ip, Server.private_ip: private_ip, Server.public_ip: ip, Server.idc: self.account,
                         Server.region: region,
                         Server.admin_user: self.default_admin_user})
                    session.query(ServerDetail).filter(ServerDetail.ip == ip).update(
                        {ServerDetail.instance_id: instance_id, ServerDetail.instance_type: instance_type,
                         ServerDetail.instance_state: instance_state})

            session.commit()

    def test_auth(self):
        """
        测试下用户给的信息是否正确
        :return:
        """
        self.offset = '0'
        self.limit = '1'  # 测试的时候只请求一个机器就可以了，不然机器多了就卡好长时间
        result_url = self.get_server_url()
        response = requests.get(result_url)
        result_data = json.loads(response.text)
        return result_data

    def index(self):
        """
        腾讯云若机器超过100台需要进行通过offset+limit获取
        :return:
        """
        count = self.get_server_count()
        # print('Tocal：{}'.format(count))
        for c in range(0, count, 100):
            self.offset = str(c)
            if (c + 100) > count:
                self.limit = str(count)
            else:
                self.limit = str(c + 100)
            ins_log.read_log('info', '开始同步腾讯云的第{}--{}台机器'.format(self.offset, self.limit))
            self.sync_cmdb()


def get_configs():
    """
    get id / key / region info
    :return:
    """

    qcloud_configs_list = []
    with DBContext('r') as session:
        qcloud_configs_info = session.query(AssetConfigs).filter(AssetConfigs.account == '腾讯云',
                                                                 AssetConfigs.state == 'true').all()
        for data in qcloud_configs_info:
            data_dict = model_to_dict(data)
            data_dict['create_time'] = str(data_dict['create_time'])
            data_dict['update_time'] = str(data_dict['update_time'])
            qcloud_configs_list.append(data_dict)
    return qcloud_configs_list


def main():
    """
    从接口获取已经启用的配置
    :return:
    """

    mc = MyCryptV2()
    qcloud_configs_list = get_configs()
    if not qcloud_configs_list:
        ins_log.read_log('error', '没有获取到腾讯云资产配置信息，跳过')
        return False
    for config in qcloud_configs_list:
        access_id = config.get('access_id')
        access_key = mc.my_decrypt(config.get('access_key'))  # 解密后使用
        region = config.get('region')
        default_admin_user = config.get('default_admin_user')

        obj = CVMApi(access_id, access_key, region, default_admin_user)
        obj.index()


if __name__ == '__main__':
    fire.Fire(main)
