#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/5/13 14:02
# @Author  : Fred Yangxiaofei
# @File    : huawei_ecs.py
# @Role    : 获取Aliyun资产信息推送到CMDB


import json
import re
from aliyunsdkcore.client import AcsClient
from aliyunsdkecs.request.v20140526 import DescribeInstancesRequest
from libs.common import M2human
from libs.db_context import DBContext
from models.server import Server, ServerDetail, AssetConfigs, model_to_dict
from libs.web_logs import ins_log
from opssdk.operate import MyCryptV2
import fire


class EcsAPi():
    def __init__(self, access_id, access_key, region, default_admin_user):
        self.access_id = access_id
        self.access_key = access_key
        self.region = region
        self.default_admin_user = default_admin_user  # 若用户给了默认管理用户，就给绑定上，else 为null
        self.client = self.create_client()
        self.page_number = 1  # 实例状态列表的页码。起始值：1 默认值：1
        self.page_size = 100  # 分页查询时设置的每页行数。最大值：100 默认值：10
        self.account = '阿里云'
        self.state = 'auto'  # auto状态：标记为自动获取的机器

    def create_client(self):
        client = AcsClient(self.access_id, self.access_key, self.region)
        return client

    def set_request(self):
        request = DescribeInstancesRequest.DescribeInstancesRequest()
        request.set_PageNumber(self.page_number)
        request.set_PageSize(self.page_size)
        return request

    def get_response(self):
        """
        获取返回值
        :return:
        """

        response_data = {}
        err = None
        request = self.set_request()
        try:
            response = self.client.do_action_with_exception(request)
            response_data = json.loads(str(response, encoding="utf8"))
        except Exception as e:
            err = e
        return response_data, err

    def get_server_count(self):
        """
        获取机器总数
        :return:
        """
        response_data, err = self.get_response()
        if err != None:
            ins_log.read_log('error', err)
            return False
        count = response_data['TotalCount']
        return count

    def get_server_info(self):
        """
        获取服务器信息
        :return:
        """
        response_data, err = self.get_response()
        if err != None:
            ins_log.read_log('error', err)
            return False
        try:
            ret = response_data['Instances']['Instance']
        except (KeyError, TypeError):
            ins_log.read_log('error', '可能是因为SecretID/SecretKey配置错误，没法拿到配置，请检查下配置')
            return False
        server_list = []
        for i in ret:
            asset_data = dict()
            try:
                asset_data['hostname'] = i.get('InstanceName')
            except(KeyError, TypeError):
                asset_data['hostname'] = i.get('InstanceId')  # 取不到给instance_id
            asset_data['region'] = i.get('ZoneId')
            asset_data['instance_id'] = i.get('InstanceId')
            asset_data['instance_type'] = i.get('InstanceType')
            asset_data['instance_state'] = i.get('Status')
            asset_data['cpu_cores'] = i.get('Cpu')
            asset_data['memory'] = M2human(i.get('Memory'))
            # 内网IP
            try:
                #VPC里面内网IP
                asset_data['private_ip'] = i['VpcAttributes']['PrivateIpAddress']['IpAddress'][0]
            except (KeyError, IndexError):
                #非VPC里面获取内网IP
                asset_data['private_ip'] = i['InnerIpAddress']['IpAddress'][0]
            # 公网IP/弹性IP
            try:
                asset_data['public_ip'] = i['PublicIpAddress']['IpAddress'][0]
            except(KeyError, IndexError):
                asset_data['public_ip'] = i['EipAddress']['IpAddress']
            except Exception:
                asset_data['public_ip'] = asset_data['private_ip']
            if 'public_ip' not in asset_data or not asset_data['public_ip'].strip():
                asset_data['public_ip'] = asset_data['private_ip']
            asset_data['os_type'] = i.get('OSType')
            asset_data['os_name'] = i.get('OSName')
            server_list.append(asset_data)
            # print(asset_data)
            ins_log.read_log('info', '资产信息:{}'.format(asset_data))
        return server_list

    def sync_cmdb(self):
        """
        写入CMDB
        :return:
        """

        server_list = self.get_server_info()
        if not server_list:
            ins_log.read_log('info', 'Not fount server info')
            return False
        with DBContext('w') as session:
            for server in server_list:
                ip = server.get('public_ip')
                private_ip = server.get('private_ip')
                instance_id = server.get('instance_id', 'Null')
                hostname = server.get('hostname', instance_id)
                if hostname == '' or not hostname:
                    hostname = instance_id

                if re.search('syncserver', hostname):
                    hostname = '{}_{}'.format(hostname, private_ip)

                region = server.get('region', 'Null')
                instance_type = server.get('instance_type', 'Null')
                instance_state = server.get('instance_state', 'Null')
                cpu = server.get('cpu', 'Null')
                cpu_cores = server.get('cpu_cores', 'Null')
                memory = server.get('memory', 'Null')
                disk = server.get('disk', 'Null')  # 阿里云接口里面好像没有disk信息
                os_type = server.get('os_type', 'Null')
                os_name = server.get('os_name', 'Null')
                os_kernel = server.get('os_kernel', 'Null')
                sn = server.get('sn', 'Null')

                exist_ip_1 = session.query(Server).filter(Server.hostname == hostname).first()
                if exist_ip_1:
                    session.query(Server).filter(Server.ip == ip).update(
                        {Server.hostname: hostname, Server.public_ip: ip, Server.private_ip: private_ip,
                         Server.idc: self.account,
                         Server.region: region,
                         Server.admin_user: self.default_admin_user})

                else:
                    if os_type == 'windows':
                        # windows机器不绑定管理用户，资产信息只是平台拿到的一些基础信息
                        new_windows_server = Server(ip=ip, public_ip=ip, private_ip=private_ip, hostname=hostname,
                                                    port=3389, idc=self.account,
                                                    region=region,
                                                    state=self.state)
                        session.add(new_windows_server)

                    else:
                        # unix机器给默认绑定上管理用户，用于后续登陆机器拿详细资产使用的
                        new_server = Server(ip=ip, public_ip=ip,  private_ip=private_ip,hostname=hostname, port=54822, idc=self.account,
                                            region=region,
                                            state=self.state, admin_user=self.default_admin_user)
                        session.add(new_server)

                exist_ip = session.query(ServerDetail).filter(ServerDetail.ip == ip).first()
                if exist_ip:
                    session.query(ServerDetail).filter(ServerDetail.ip == ip).update(
                        {ServerDetail.instance_id: instance_id, ServerDetail.instance_type: instance_type,
                         ServerDetail.instance_state: instance_state})
                else:
                    if os_type == 'windows':

                        new_serve_detail = ServerDetail(ip=ip, instance_id=instance_id, instance_type=instance_type,
                                                        instance_state=instance_state, cpu=cpu, cpu_cores=cpu_cores,
                                                        memory=memory, os_type=os_name, disk=disk, os_kernel=os_kernel,
                                                        sn=sn)
                        session.add(new_serve_detail)

                    else:
                        new_serve_detail = ServerDetail(ip=ip, instance_id=instance_id, instance_type=instance_type,
                                                        instance_state=instance_state, cpu=cpu, cpu_cores=cpu_cores,
                                                        memory=memory, os_type=os_name, disk=disk, os_kernel=os_kernel,
                                                        sn=sn)
                        session.add(new_serve_detail)
            session.commit()

    def test_auth(self):
        """
        测试接口权限等信息是否异常
        :return:
        """
        self.page_number = '1'
        self.page_size = '1'
        request = self.set_request()
        response = self.client.do_action_with_exception(request)
        response_data = json.loads(str(response, encoding="utf8"))
        return response_data

    def index(self):
        """
        阿里云若机器超过100台需要进行通过PageSize+PageSize获取
        :return:
        """

        count = self.get_server_count()
        print('Tocal：{}'.format(count))


        self.page_size = 100
        mod = count % self.page_size
        if mod:
            total_page_number = int(count / self.page_size) + 1
        else:
            total_page_number = int(count / self.page_size)
        for cur_page_number in range(1, total_page_number + 1):
            self.page_number = cur_page_number
            ins_log.read_log('info', '开始同步阿里云第{}页的{}台机器'.format(self.page_number, self.page_size))
            self.sync_cmdb()


def get_configs():
    """
    get id / key / region info
    :return:
    """

    aliyun_configs_list = []
    with DBContext('r') as session:
        aliyun_configs_info = session.query(AssetConfigs).filter(AssetConfigs.account == '阿里云',
                                                                 AssetConfigs.state == 'true').all()
        for data in aliyun_configs_info:
            data_dict = model_to_dict(data)
            data_dict['create_time'] = str(data_dict['create_time'])
            data_dict['update_time'] = str(data_dict['update_time'])
            aliyun_configs_list.append(data_dict)
    return aliyun_configs_list


def main():
    """
    从接口获取已经启用的配置
    :return:
    """
    mc = MyCryptV2()
    aliyun_configs_list = get_configs()
    if not aliyun_configs_list:
        ins_log.read_log('error', '没有获取到阿里云资产配置信息，跳过')
        return False
    for config in aliyun_configs_list:
        access_id = config.get('access_id')
        access_key = mc.my_decrypt(config.get('access_key'))  # 解密后使用
        region = config.get('region')
        default_admin_user = config.get('default_admin_user')

        obj = EcsAPi(access_id, access_key, region, default_admin_user)
        obj.index()


# def test():
#     obj = EcsAPi('', '', 'cn-shanghai', '')
#     obj.index()


if __name__ == '__main__':
    fire.Fire(main)
