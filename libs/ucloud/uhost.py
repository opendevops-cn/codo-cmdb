#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File  : uhost.py
# @Author: Fred Yangxiaofei
# @Date  : 2019/10/11
# @Role  : 获取Uhost主机详情

"""
	Homepage: https://github.com/ucloud/ucloud-sdk-python3
	Examples: https://github.com/ucloud/ucloud-sdk-python3/tree/master/examples
	Documentation: https://ucloud.github.io/ucloud-sdk-python3/
"""

from ucloud.core import exc
from ucloud.client import Client
from libs.db_context import DBContext
from libs.web_logs import ins_log
from models.server import Server, ServerDetail
from models.server import AssetConfigs, model_to_dict
from opssdk.operate import MyCryptV2
import fire


class UHostAPI:
    def __init__(self, access_id, access_key, region, project_id, default_admin_user):
        """
        :param access_id: AccessId
        :param access_key:  AccessKey
        :param region:  region
        :param project_id:  项目ID
        """
        self.idc = 'UCloud'
        self.state = 'auto'
        self.region = region
        self.access_id = access_id
        self.access_key = access_key
        self.project_id = project_id
        self.default_admin_user = default_admin_user

    def get_uhost_count(self):
        try:
            client = Client({
                "region": self.region,
                "project_id": self.project_id,
                "public_key": self.access_id,
                "private_key": self.access_key
            })
            response = client.uhost().describe_uhost_instance({})
            return response['TotalCount']

        except exc.UCloudException as uerr:
            ins_log.read_log('error', '请求Ucloud接口出错:{0}'.format(uerr))
            return False
        except Exception as err:
            ins_log.read_log('error', err)
            return False

    def get_region_uhosts(self, offset=0, limit=50):
        try:
            client = Client({
                "region": self.region,
                "project_id": self.project_id,
                "public_key": self.access_id,
                "private_key": self.access_key
            })
            response = client.uhost().describe_uhost_instance({
                "Offset": offset,
                "Limit": limit
            })
            return response
        except exc.UCloudException as uerr:
            ins_log.read_log('error', '请求Ucloud接口出错:{0}'.format(uerr))
            return False
        except Exception as err:
            ins_log.read_log('error', err)
            return False

    def get_uhost_all(self):
        """
        递归获取所有Uhost主机
        :return:
        """
        offset = 0
        limit = 50
        tocal = self.get_uhost_count()
        while True:
            data = self.get_region_uhosts(offset)
            if not data: break
            if not data and 'UHostSet' not in data: break
            if not data['UHostSet']: break
            # 这里好坑啊。Ucloud的分页居然不能递归区，超过总数居然还会报错
            offset += limit
            if int(offset) > int(tocal): offset = tocal

            row = data['UHostSet']
            if not row: break
            res = list(map(self.format_uhost, row))
            yield res

    def format_uhost(self, uhost_info):
        if not isinstance(uhost_info, dict):
            raise TypeError

        asset_data = dict()
        asset_data['hostname'] = uhost_info.get('Name')
        asset_data['region'] = uhost_info.get('Zone')
        asset_data['instance_id'] = uhost_info.get('UHostId')
        asset_data['instance_type'] = uhost_info.get('HostType')
        asset_data['instance_state'] = uhost_info.get('State')
        asset_data['os_type'] = uhost_info.get('OsType')
        asset_data['os_name'] = uhost_info.get('OsName')
        asset_data['cpu'] = uhost_info.get('CPU')
        asset_data['memory'] = uhost_info.get('Memory')
        asset_data['disk'] = uhost_info.get('TotalDiskSpace')
        try:
            asset_data['private_ip'] = uhost_info.get('IPSet')[0]['IP']
        except (KeyError, IndexError):
            asset_data['private_ip'] = 'Null'
        try:
            asset_data['public_ip'] = uhost_info.get('IPSet')[1]['IP']
        except (KeyError, IndexError):
            asset_data['public_ip'] = 'Null'

        return asset_data

    def sync_cmdb(self):
        """
        写入CMDB
        :return:
        """

        server_list = self.get_uhost_all()
        if not server_list:
            ins_log.read_log('info', 'Not fount server info...')
            return False
        with DBContext('w') as session:
            for data in server_list:
                for server in data:
                    ins_log.read_log('info', '资产信息:{}'.format(server))
                    ip = server.get('public_ip')
                    private_ip = server.get('private_ip')
                    instance_id = server.get('instance_id', 'Null')
                    hostname = server.get('hostname', instance_id)
                    if not hostname.strip():
                        hostname = instance_id
                    region = server.get('region', 'Null')
                    instance_type = server.get('instance_type', 'Null')
                    instance_state = server.get('instance_state', 'Null')
                    cpu = server.get('cpu', 'Null')  # CPU型号
                    memory = server.get('memory', 'Null')
                    disk = server.get('disk', 'Null')
                    os_type = server.get('os_type', 'Null')
                    os_kernel = server.get('os_name', 'Null')

                    exist_hostname = session.query(Server).filter(Server.hostname == hostname).first()
                    # exist_ip = session.query(Server).filter(Server.ip == ip).first()
                    if exist_hostname:
                        session.query(Server).filter(Server.hostname == hostname).update(
                            {Server.ip: ip, Server.public_ip: ip, Server.private_ip: private_ip, Server.idc: self.idc,
                             Server.region: region})

                    else:
                        new_server = Server(ip=ip, public_ip=ip, private_ip=private_ip, hostname=hostname, port=22,
                                            idc=self.idc,
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
                                                        instance_state=instance_state, cpu_cores=cpu,
                                                        memory=memory, disk=disk, os_type=os_type, os_kernel=os_kernel)
                        session.add(new_serve_detail)
            session.commit()

    @staticmethod
    def permission_auth(access_id, access_key, region, project_id, offset=1, limit=1):
        """
        请求一台机器做权限测试
        :param access_id:
        :param access_key:
        :param region:
        :param project_id:
        :param offset:
        :param limit:
        :return:
        """

        client = Client(
            {"region": region, "project_id": project_id, "public_key": access_id, "private_key": access_key})
        response = client.uhost().describe_uhost_instance({"Offset": offset, "Limit": limit})
        return response


def get_configs():
    """
    get id / key / region info
    :return:
    """

    ucloud_configs_list = []
    with DBContext('r') as session:
        ucloud_configs_info = session.query(AssetConfigs).filter(AssetConfigs.account == 'UCloud',
                                                                 AssetConfigs.state == 'true').all()
        for data in ucloud_configs_info:
            data_dict = model_to_dict(data)
            data_dict['create_time'] = str(data_dict['create_time'])
            data_dict['update_time'] = str(data_dict['update_time'])
            ucloud_configs_list.append(data_dict)
    return ucloud_configs_list



def main():
    """
    从接口获取已经启用的配置
    :return:
    """
    mc = MyCryptV2()
    ucloud_configs_list = get_configs()
    if not ucloud_configs_list:
        ins_log.read_log('error', '没有获取到UCloud资产配置信息，跳过')
        return False
    for config in ucloud_configs_list:
        access_id = config.get('access_id')
        access_key = mc.my_decrypt(config.get('access_key'))  # 解密后使用
        region = config.get('region')
        default_admin_user = config.get('default_admin_user')
        project_id = config.get('project_id')
        obj = UHostAPI(access_id=access_id, access_key=access_key, region=region, default_admin_user=default_admin_user,
                       project_id=project_id)
        obj.sync_cmdb()


if __name__ == '__main__':
    fire.Fire(main)
