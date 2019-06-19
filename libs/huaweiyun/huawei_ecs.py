#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/6/18 9:31
# @Author  : Fred Yangxiaofei
# @File    : huawei_ecs.py
# @Role    : Huawei Cloud Ecs


from openstack import connection
from libs.web_logs import ins_log
from libs.db_context import DBContext
from models.server import Server, ServerDetail, AssetConfigs, model_to_dict
from opssdk.operate import MyCryptV2
import fire


class HuaweiEcsApi():
    def __init__(self, access_id, access_key, region, cloud, project_id, default_admin_user):
        """

        :param access_id: AccessID
        :param access_key: Accesskey
        :param region:  区域，如：cn-east-2
        :param cloud:  默认：myhuaweicloud.com # cdn use: cloud = "myhwclouds.com"
        :param project_id: 这个字面是项目ID，其实就是华为云，我的凭证--项目ID，这是对应区域的，每个区域都有一个
        """
        self.default_admin_user = default_admin_user
        self.account = '华为云'  # 标记华为云机器
        self.state = 'auto'  # auto状态：标记为自动获取的机器
        self.access_id = access_id
        self.access_key = access_key
        self.region = region
        self.cloud = cloud
        self.project_id = project_id
        self.conn = self.connect()

    def connect(self):
        try:
            conn = connection.Connection(
                project_id=self.project_id,
                cloud=self.cloud,
                region=self.region,
                ak=self.access_id,
                sk=self.access_key)
            return conn
        except Exception as e:
            print(e)
            return False

    def get_server_info(self):
        """
        这里吐槽一下，华为云请求返回过来给我一个class 数据居然没处理///  也可能是因为我用法不对，But 官方提供就这么用的, 所以我这里自己处理了
        :return:
        """

        servers = self.conn.compute.servers(limit=10)  # 一次取10台,迭代取
        server_list = []
        for server in servers:
            asset_data = dict()
            asset_data['hostname'] = server.name
            ip_info = server.addresses
            for k, v in ip_info.items():
                for i in v:
                    # 这是弹性IP
                    if 'floating' in i.values():
                        asset_data['public_ip'] = i.get('addr')
                    else:
                        asset_data['public_ip'] = i.get('addr')
            asset_data['instance_type'] = server.flavor.get('id')
            asset_data['instance_id'] = server.id
            asset_data['instance_status'] = server.status
            asset_data['region'] = server.availability_zone
            server_list.append(asset_data)
        return server_list

    def sync_cmdb(self):
        """
        数据写CMDB，华为的信息比较少
        :return:
        """
        server_list = self.get_server_info()
        if not server_list:
            ins_log.read_log('info', 'Not fount server info...')
            return False
        with DBContext('w') as session:
            for server in server_list:
                print(server)
                ip = server.get('public_ip')
                instance_id = server.get('instance_id', 'Null')
                hostname = server.get('hostname', instance_id)
                if not hostname.strip():
                    hostname = instance_id
                region = server.get('region', 'Null')
                instance_type = server.get('instance_type', 'Null')
                instance_status = server.get('instance_status')
                # 华为云接口没看到CPU这类信息
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
                        {Server.ip: ip, Server.public_ip: ip, Server.idc: self.account, Server.region: region})

                else:
                    new_server = Server(ip=ip, public_ip=ip, hostname=hostname, port=22, idc=self.account,
                                        region=region,
                                        state=self.state, admin_user=self.default_admin_user)
                    session.add(new_server)

                exist_ip = session.query(ServerDetail).filter(ServerDetail.ip == ip).first()
                if exist_ip:
                    session.query(ServerDetail).filter(ServerDetail.ip == ip).update(
                        {ServerDetail.instance_id: instance_id, ServerDetail.instance_type: instance_type,
                         ServerDetail.instance_state: instance_status})
                else:
                    new_serve_detail = ServerDetail(ip=ip, instance_id=instance_id, instance_type=instance_type,
                                                    instance_state=instance_status, cpu=cpu, cpu_cores=cpu_cores,
                                                    memory=memory, disk=disk, os_type=os_type, os_kernel=os_kernel,
                                                    sn=sn)
                    session.add(new_serve_detail)
            session.commit()

    def test_auth(self, huawei_instance_id):
        """
        实在无能为力，华为API文档太少，没有深入研究，测试查询一台实例ID的信息测试
        :return:
        """
        server_msg = self.conn.compute.get_server(huawei_instance_id)
        return server_msg
        # try:
        #     self.conn.compute.get_server(huawei_instance_id)
        #     msg = '成功'
        # except keystoneauth1.exceptions.http.Unauthorized:
        #     print('请检查AccessID和AccessKey权限是否正确')
        #     msg = '请检查AccessID和AccessKey权限是否正确'
        # except openstack.exceptions.HttpException as err:
        #     msg = 'openstack error for {}'.format(err)
        #     print('openstack error')
        #     print(err)
        # except Exception as e:
        #     print(e)
        #     msg = 'error: {}'.format(e)
        # return msg


def get_configs():
    """
    get id / key / region info
    :return:
    """

    huawei_configs_list = []
    with DBContext('r') as session:
        huawei_configs_info = session.query(AssetConfigs).filter(AssetConfigs.account == '华为云',
                                                                 AssetConfigs.state == 'true').all()
        for data in huawei_configs_info:
            data_dict = model_to_dict(data)
            data_dict['create_time'] = str(data_dict['create_time'])
            data_dict['update_time'] = str(data_dict['update_time'])
            huawei_configs_list.append(data_dict)
    return huawei_configs_list


def main():
    """
    从接口获取已经启用的配置
    :return:
    """

    mc = MyCryptV2()
    huawei_configs_list = get_configs()
    if not huawei_configs_list:
        ins_log.read_log('error', '没有获取到华为云资产配置信息，跳过')
        return False
    for config in huawei_configs_list:
        access_id = config.get('access_id')
        access_key = mc.my_decrypt(config.get('access_key'))  # 解密后使用
        region = config.get('region')
        huawei_cloud = config.get('huawei_cloud')
        project_id = config.get('project_id')

        default_admin_user = config.get('default_admin_user')
        obj = HuaweiEcsApi(access_id=access_id, access_key=access_key, region=region, cloud=huawei_cloud,
                           project_id=project_id,
                           default_admin_user=default_admin_user)
        obj.sync_cmdb()


if __name__ == '__main__':
    fire.Fire(main)
