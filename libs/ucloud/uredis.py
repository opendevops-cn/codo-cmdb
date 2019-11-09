#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File  : uredis.py
# @Author: Fred Yangxiaofei
# @Date  : 2019/10/31
# @Role  :  获取Ucloud redis信息


"""
	Homepage: https://github.com/ucloud/ucloud-sdk-python3
	Examples: https://github.com/ucloud/ucloud-sdk-python3/tree/master/examples
	Documentation: https://ucloud.github.io/ucloud-sdk-python3/
"""

from ucloud.core import exc
from ucloud.client import Client
from libs.db_context import DBContext
from libs.web_logs import ins_log
from models.db import DB
from models.server import AssetConfigs, model_to_dict
from opssdk.operate import MyCryptV2
import fire


class UredisAPI:
    def __init__(self, access_id, access_key, region, project_id):
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

    def get_uredis_count(self, offset=0, limit=1):
        try:
            client = Client({
                "region": self.region,
                "project_id": self.project_id,
                "public_key": self.access_id,
                "private_key": self.access_key
            })

            response = client.umem().describe_uredis_group({
                "Offset": offset,
                "Limit": limit
            })
            return response['TotalCount']

        except exc.UCloudException as uerr:
            ins_log.read_log('error', 'request ucloud api error:{0}'.format(uerr))
            return False
        except Exception as err:
            ins_log.read_log('error', err)
            return False

    def get_region_uredis(self, offset=0, limit=50):
        try:
            client = Client({
                "region": self.region,
                "project_id": self.project_id,
                "public_key": self.access_id,
                "private_key": self.access_key
            })
            response = client.umem().describe_uredis_group({
                "Offset": offset,
                "Limit": limit
            })
            return response
        except exc.UCloudException as uerr:
            ins_log.read_log('error', 'request ucloud api error:{0}'.format(uerr))
            return False
        except Exception as err:
            ins_log.read_log('error', err)
            return False

    def get_uredis_all(self):
        """
        递归获取所有Uredis
        :return:
        """
        offset = 0
        limit = 50
        tocal = self.get_uredis_count()
        while True:
            data = self.get_region_uredis(offset=offset)
            if not data or 'DataSet' not in data: break
            if not data['DataSet']: break
            # 吐槽：实在搞不懂Ucloud的这个offset limit分页逻辑
            # 这里好坑啊。Ucloud的分页居然不能递归区，超过总数居然还会报错
            offset += limit
            if int(offset) > int(tocal): offset = tocal
            row = data['DataSet']
            if not row: break
            res = list(map(self.format_uredis, row))
            yield res

    def format_uredis(self, uredis_info):
        if not isinstance(uredis_info, dict):
            raise TypeError

        asset_data = dict()
        asset_data['db_name'] = uredis_info.get('Name')
        asset_data['db_region'] = uredis_info.get('Zone')
        asset_data['db_host'] = uredis_info.get('VirtualIP')
        # 没看到Ucloud接口的user
        asset_data['db_user'] = uredis_info.get('AdminUser')
        asset_data['db_port'] = uredis_info.get('Port')
        asset_data['db_type'] = uredis_info.get('Protocol')
        asset_data['db_version'] = uredis_info.get('Version')
        asset_data['db_instance_id'] = uredis_info.get('GroupId')
        asset_data['instance_state'] = uredis_info.get('State')
        return asset_data

    def sync_cmdb(self):
        """
        写入CMDB
        :return:
        """

        reids_list = self.get_uredis_all()
        if not reids_list:
            ins_log.read_log('error', 'Not fount reids info...')
            return False
        with DBContext('w') as session:
            for data in reids_list:
                for redis in data:
                    ins_log.read_log('info', '资产信息:{}'.format(redis))
                    try:
                        db_user = redis['user']
                    except KeyError:
                        db_user = 'root'

                    db_name = redis.get('db_name')
                    exist_redis = session.query(DB).filter(DB.db_code == db_name).first()

                    if exist_redis:
                        session.query(DB).filter(DB.db_code == db_name).update({
                            DB.idc: self.idc, DB.db_host: redis.get('db_host'),
                            DB.db_port: redis.get('db_port'), DB.db_user: db_user, DB.db_region: redis.get('db_region'),
                            DB.db_type: redis.get('db_type'), DB.db_version: redis.get('db_version'),
                            DB.state: redis.get('instance_state'),
                            DB.db_instance_id: redis.get('db_instance_id')})
                    else:
                        new_db = DB(idc=self.idc, db_code=db_name, db_host=redis.get('db_host'),
                                    db_port=redis.get('db_port'), db_user=db_user, db_region=redis.get('db_region'),
                                    db_type=redis.get('db_type'), db_version=redis.get('db_version'),
                                    state=redis.get('instance_state'), db_instance_id=redis.get('db_instance_id'))
                        session.add(new_db)
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
        response = client.umem().describe_uredis_group({
            "Offset": offset,
            "Limit": limit
        })
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
        project_id = config.get('project_id')
        obj = UredisAPI(access_id=access_id, access_key=access_key, region=region,
                        project_id=project_id)
        obj.sync_cmdb()


if __name__ == '__main__':
    fire.Fire(main)
