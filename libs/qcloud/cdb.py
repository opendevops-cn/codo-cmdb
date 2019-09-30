#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File  : cdb.py
# @Author: Fred Yangxiaofei
# @Date  : 2019/8/30
# @Role  : 获取腾讯云CDB


import time
import random
import requests
import json
import re
from libs.qcloud.qcloud_api import ApiOper
from libs.db_context import DBContext
from libs.web_logs import ins_log
from opssdk.operate import MyCryptV2
from models.server import AssetConfigs, model_to_dict
from models.db import DB
import fire


class CDBApi():
    def __init__(self, access_id, access_key, region):
        self.offset = '0'  # 偏移量,这里拼接的时候必须是字符串
        self.limit = '100'  # 官方默认是20，大于100需要设置偏移量再次请求：offset=100,offset={机器总数}
        self.access_id = access_id
        self.access_key = access_key
        self.region = region
        self.account = '腾讯云'  # 标记机器为腾讯云
        self.state = 'auto'  # 标记自动获取状态

    def get_db_url(self):
        """
        获取腾讯云机器的API拼接结果，get请求
        :return:
        """
        api_url = 'cdb.tencentcloudapi.com/?'
        keydict = {
            # 公共参数部分
            'Timestamp': str(int(time.time())),
            'Nonce': str(int(random.random() * 1000)),
            'Region': self.region,
            'SecretId': self.access_id,
            'Version': '2017-03-20',
            # 'SignatureMethod': SignatureMethod,
            # 接口参数部分
            'Action': 'DescribeDBInstances',
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
        result_url = self.get_db_url()
        response = requests.get(result_url)
        result_data = json.loads(response.text)
        if result_data['Response'].get('Error'):
            ins_log.read_log('error', '{}'.format(result_data['Response']))
            return False
        else:
            ret = result_data['Response']

        return ret

    def get_db_count(self):
        """
        获取主机总数量。如果机器数量大于limit限制就要用到offset偏移查询
        :return:  int
        """

        ret = self.get_result_data()
        if not ret:
            return False

        db_count = ret['TotalCount']
        # print('TotalCount:{count}'.format(count=db_count))
        return db_count

    def get_db_info(self):
        """
        获取Qcloud DB信息
        :return:
        """
        ret = self.get_result_data()

        if not ret:
            ins_log.read_log('error', 'Not fount db info')
            return False

        db_list = []

        cdb_list = ret['Items']
        for i in cdb_list:
            asset_data = dict()
            asset_data['idc'] = self.account
            asset_data['db_instance_id'] = i.get('InstanceId')
            asset_data['db_code'] = i.get('InstanceName')
            asset_data['db_host'] = i.get('Vip')
            asset_data['db_public_ip'] = i.get('WanDomain')
            asset_data['db_port'] = i.get('Vport')
            asset_data['db_region'] = i.get('Zone')
            asset_data['db_version'] = i.get('EngineVersion')
            asset_data['db_type'] = 'mysql'  # qcloud cdb好像只有mysql
            if i.get('InstanceType') == 1:
                asset_data['db_mark'] = '写'
            elif i.get('InstanceType') == 2:
                asset_data['db_mark'] = '备'
            elif i.get('InstanceType') == 3:
                asset_data['db_mark'] = '读'
            if i.get('Status') == 0:
                asset_data['state'] = '创建中'
            elif i.get('Status') == 1:
                asset_data['state'] = '运行中'
            elif i.get('Status') == 5:
                asset_data['state'] = '隔离中'
            db_list.append(asset_data)

        return db_list

    def sync_cmdb(self):
        """
        返回结果写入CMDB
        :return:
        """
        db_list = self.get_db_info()

        if not db_list:
            ins_log.read_log('error', 'Not fount db info')
            return False

        with DBContext('w') as session:
            for db in db_list:
                idc = db.get('idc')
                db_instance_id = db.get('db_instance_id', 'Null')
                db_code = db.get('db_code', 'Null')
                db_host = db.get('db_host', 'Null')
                db_public_ip = db.get('db_public_ip', 'Null')
                db_port = db.get('db_port', 'Null')
                db_region = db.get('db_region', 'Null')
                db_version = db.get('db_version', 'Null')
                db_mark = db.get('db_mark', 'Null')
                state = db.get('state', 'Null')
                db_type = db.get('db_type', 'Null')

                exist_rds = session.query(DB).filter(DB.db_code == db_code).first()

                if exist_rds:
                    session.query(DB).filter(DB.db_code == db_code).update({
                        DB.idc: idc, DB.db_host: db_host, DB.db_type: db_type,
                        DB.db_port: db_port, DB.db_region: db_region, DB.db_version: db_version,
                        DB.state: state, DB.db_mark: db_mark, DB.db_instance_id: db_instance_id,
                        DB.db_public_ip: db_public_ip})
                else:
                    new_db = DB(idc=idc, db_code=db_code, db_host=db_host, db_public_ip=db_public_ip, db_port=db_port,
                                db_region=db_region, db_version=db_version, db_mark=db_mark, state=state,
                                db_type=db_type)
                    session.add(new_db)
            session.commit()

    def test_auth(self):
        """
        测试下用户给的信息是否正确
        :return:
        """
        self.offset = '0'
        self.limit = '1'  # 测试的时候只请求一个机器就可以了，不然机器多了就卡好长时间
        result_url = self.get_db_url()
        response = requests.get(result_url)
        result_data = json.loads(response.text)
        return result_data

    def index(self):
        """
        腾讯云若CDB超过100台需要进行通过offset+limit获取
        :return:
        """
        count = self.get_db_count()
        # print('Tocal：{}'.format(count))
        for c in range(0, count, 100):
            self.offset = str(c)
            if (c + 100) > count:
                self.limit = str(count)
            else:
                self.limit = str(c + 100)
            ins_log.read_log('info', '开始同步腾讯云的第{}--{}台CDB'.format(self.offset, self.limit))
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
        obj = CDBApi(access_id, access_key, region)
        obj.index()


if __name__ == '__main__':
    fire.Fire(main)
