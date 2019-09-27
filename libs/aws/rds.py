#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019-08-15 23:19
# @Author  : Yangxiaofei
# @File    : rds.py
# @Role    : 获取RDS信息


import boto3
from libs.db_context import DBContext
from models.db import DB
from models.server import AssetConfigs, model_to_dict
from libs.web_logs import ins_log
from opssdk.operate import MyCryptV2
import fire


class RDSApi():
    def __init__(self, access_id, access_key, region):
        self.idc = 'AWS'
        self.access_id = access_id
        self.access_key = access_key
        self.region = region
        self.client = boto3.client('rds', region_name=self.region, aws_access_key_id=self.access_id,
                                   aws_secret_access_key=self.access_key)

    def get_response(self):
        """
        获取返回值
        :return:
        """
        response_data = {}
        err = None
        try:
            response_data = self.client.describe_db_instances()

        except Exception as e:
            err = e
        return response_data, err

    def get_rds_info(self):
        """
        获取RDS的信息
        :return:
        """

        response_data, err = self.get_response()

        if err:
            ins_log.read_log('error', '获取失败：{}'.format(err))
            return False

        ret = response_data['DBInstances']
        rds_list = []

        if ret:
            for i in ret:
                rds_data = dict()
                try:
                    rds_data['db_code'] = i.get('DBInstanceIdentifier')
                except (KeyError, TypeError):
                    rds_data['db_code'] = i.get('DBName', 'Null')  # 拿不到RDS标识名字给DBNAME
                rds_data['db_region'] = i.get('AvailabilityZone')
                rds_data['db_class'] = i.get('DBInstanceClass')
                rds_data['db_type'] = i.get('Engine')
                rds_data['state'] = i.get('DBInstanceStatus')
                rds_data['db_user'] = i.get('MasterUsername')
                rds_data['db_host'] = i.get('Endpoint').get('Address')
                rds_data['db_port'] = i.get('Endpoint').get('Port')
                rds_data['db_disk'] = i.get('AllocatedStorage')
                rds_data['db_version'] = i.get('EngineVersion')
                rds_data['db_instance_id'] = i.get('DbiResourceId')
                rds_list.append(rds_data)
        return rds_list

    def sync_cmdb(self):
        """
        将RDS信息入库
        :return:
        """
        rds_list = self.get_rds_info()

        if not rds_list:
            ins_log.read_log('error', 'Not Fount rds info...')
            return False

        with DBContext('w') as session:
            for rds in rds_list:
                ins_log.read_log('info', 'RDS信息：{}'.format(rds))
                db_code = rds.get('db_code')

                exist_rds = session.query(DB).filter(DB.db_code == db_code).first()

                if exist_rds:
                    session.query(DB).filter(DB.db_code == db_code).update({
                        DB.idc: self.idc, DB.db_class: rds.get('db_class'), DB.db_host: rds.get('db_host'),
                        DB.db_port: rds.get('db_port'),
                        DB.db_disk: rds.get('db_disk'), DB.db_region: rds.get('db_region'),
                        DB.db_type: rds.get('db_type'), DB.db_version: rds.get('db_version'),
                        DB.state: rds.get('state'), DB.db_env: 'Null', DB.db_instance_id: rds.get('db_instance_id')})
                else:
                    new_db = DB(idc=self.idc, db_code=db_code, db_class=rds.get('db_class'), db_host=rds.get('db_host'),
                                db_port=rds.get('db_port'), db_user=rds.get('db_user'), db_disk=rds.get('db_disk'),
                                db_region=rds.get('db_region'), db_type=rds.get('db_type'),
                                db_version=rds.get('db_version'), state=rds.get('state'), db_env='Null',
                                db_instance_id=rds.get('db_instance_id'))
                    session.add(new_db)
            session.commit()

    def test_auth(self):
        """
        测试接口权限等信息是否异常
        :return:
        """
        response = self.client.describe_db_instances()
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
    从接口获取配置
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
        obj = RDSApi(access_id, access_key, region)
        obj.sync_cmdb()


if __name__ == '__main__':
    fire.Fire(main)
