#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/5/13 16:35
# @Author  : Fred Yangxiaofei
# @File    : ec2.py
# @Role    : 获取AWS Ec2信息推送到cmdb


import boto3
import re
from libs.db_context import DBContext
from models.server import Server, ServerDetail, AssetConfigs, model_to_dict
from opssdk.operate import MyCryptV2
from libs.web_logs import ins_log
import fire


class Ec2Api():
    def __init__(self, access_id, access_key, region, default_admin_user):
        self.access_id = access_id
        self.access_key = access_key
        self.region = region
        self.client = boto3.client('ec2', region_name=self.region, aws_access_key_id=self.access_id,
                                   aws_secret_access_key=self.access_key)
        self.default_admin_user = default_admin_user
        self.account = 'AWS'  # 标记AWS机器
        self.state = 'auto'  # auto状态：标记为自动获取的机器

    def get_response(self):
        """
        获取返回
        :return:
        """
        try:
            response = self.client.describe_instances()
            return response
        except Exception as e:
            ins_log.read_log('error', e)
            # print(e)
            return False

    def get_server_info(self):

        response = self.get_response()
        if not response:
            ins_log.read_log('error', 'Not fount response, please check your access_id and access_key...')
            # print('[Error]: Not fount response, please check your access_id and access_key...')
            return False

        ret = response['Reservations']
        server_list = []
        if ret:
            for r in ret:
                for i in r['Instances']:
                    asset_data = dict()
                    try:
                        # asset_data['hostname'] = i.get('Tags')[0].get('Value') #这是旧的
                        # AWS里面支持多个标签,我们只要Key为Name的
                        tag_list = i.get('Tags')
                        # tag_list = [i for i in tag_list if i["Key"] == "Name"]
                        tag_list = filter(lambda x: x["Key"] == "Name", tag_list)
                        asset_data['hostname'] = list(tag_list)[0].get('Value')

                    except (KeyError, TypeError, IndexError):
                        asset_data['hostname'] = i.get('InstanceId', 'Null')  # 拿不到hostnameg给instance_id

                    asset_data['region'] = i['Placement'].get('AvailabilityZone', 'Null')
                    asset_data['instance_id'] = i.get('InstanceId', 'Null')
                    asset_data['instance_type'] = i.get('InstanceType', 'Null')
                    asset_data['instance_state'] = i['State'].get('Name', '')
                    asset_data['private_ip'] = i.get('PrivateIpAddress', 'Null')
                    asset_data['public_ip'] = i.get('PublicIpAddress', asset_data['private_ip'])  # 没有公网就给私网IP
                    # print(asset_data)
                    server_list.append(asset_data)

        return server_list

    def sync_cmdb(self):
        """
        写入CMDB
        :return:
        """

        server_list = self.get_server_info()
        if not server_list:
            ins_log.read_log('info', 'Not fount server info...')
            # print('Not Fount Server Info')
            return False
        with DBContext('w') as session:
            for server in server_list:
                ins_log.read_log('info', '资产信息:{}'.format(server))
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
                # AWS=接口没看到CPU这类信息
                cpu = server.get('cpu', 'Null')  # CPU型号
                cpu_cores = server.get('cpu_cores', 'Null')
                memory = server.get('memory', 'Null')
                disk = server.get('disk', 'Null')
                os_type = server.get('os_type', 'Null')
                os_kernel = server.get('os_kernel', 'Null')
                sn = server.get('sn', 'Null')

                exist_hostname = session.query(Server).filter(Server.hostname == hostname).first()
                # exist_ip = session.query(Server).filter(Server.ip == ip).first()
                if exist_hostname:
                    session.query(Server).filter(Server.hostname == hostname).update(
                        {Server.ip: ip, Server.public_ip: ip, Server.private_ip: private_ip, Server.idc: 'AWS',
                         Server.region: region})

                else:
                    new_server = Server(ip=ip, public_ip=ip, private_ip=private_ip, hostname=hostname, port=22,
                                        idc=self.account,
                                        region=region,
                                        state=self.state, admin_user=self.default_admin_user)
                    session.add(new_server)

                exist_ip = session.query(ServerDetail).filter(ServerDetail.ip == ip).first()
                if exist_ip:
                    session.query(ServerDetail).filter(ServerDetail.ip == ip).update(
                        {ServerDetail.instance_id: instance_id, ServerDetail.instance_type: instance_type,
                         ServerDetail.instance_state: instance_state})
                else:
                    new_serve_detail = ServerDetail(ip=ip, instance_id=instance_id, instance_type=instance_type,
                                                    instance_state=instance_state, cpu=cpu, cpu_cores=cpu_cores,
                                                    memory=memory, disk=disk, os_type=os_type, os_kernel=os_kernel,
                                                    sn=sn)
                    session.add(new_serve_detail)
            session.commit()

    def test_auth(self):
        """
        测试接口权限等信息是否异常
        :return:
        """
        response = self.client.describe_instances()
        return response


def get_configs():
    """
    get id / key / region info
    :return:
    """

    aws_configs_list = []
    with DBContext('r') as session:
        aws_configs_info = session.query(AssetConfigs).filter(AssetConfigs.account == 'AWS',
                                                              AssetConfigs.state == 'true').all()
        for data in aws_configs_info:
            data_dict = model_to_dict(data)
            data_dict['create_time'] = str(data_dict['create_time'])
            data_dict['update_time'] = str(data_dict['update_time'])
            aws_configs_list.append(data_dict)
    return aws_configs_list


def main():
    """
    从接口获取已经启用的配置
    :return:
    """

    mc = MyCryptV2()
    aws_configs_list = get_configs()
    if not aws_configs_list:
        ins_log.read_log('error', '没有获取到AWS资产配置信息，跳过')
        return False
    for config in aws_configs_list:
        access_id = config.get('access_id')
        access_key = mc.my_decrypt(config.get('access_key'))  # 解密后使用
        region = config.get('region')
        default_admin_user = config.get('default_admin_user')

        obj = Ec2Api(access_id, access_key, region, default_admin_user)
        obj.sync_cmdb()


# def test():
#     obj = Ec2Api('','','us-east-1', '')
#     obj.sync_cmdb()


if __name__ == '__main__':
    fire.Fire(main)
