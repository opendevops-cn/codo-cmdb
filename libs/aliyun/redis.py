#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File  : redis.py
# @Author: Fred Yangxiaofei
# @Date  : 2019/9/4
# @Role  : 获取Aliyun Redis实例信息


import json
from aliyunsdkcore.client import AcsClient
from aliyunsdkr_kvstore.request.v20150101.DescribeInstancesRequest import DescribeInstancesRequest
from libs.db_context import DBContext
from libs.web_logs import ins_log
from models.db import DB
from models.server import AssetConfigs, model_to_dict
from opssdk.operate import MyCryptV2
import fire


class RedisApi():
    def __init__(self, access_id, access_key, region):
        self.idc = '阿里云'
        self.region = region
        self.access_id = access_id
        self.access_key = access_key

    def get_region_redis(self, page_number=1, page_size=50):
        try:
            clt = AcsClient(self.access_id, self.access_key, self.region)
            request = DescribeInstancesRequest()
            request.set_accept_format('json')
            request.set_PageNumber(page_number)
            request.set_PageSize(page_size)
            response = clt.do_action_with_exception(request)
            return json.loads(str(response, encoding="utf8"))
        except Exception as err:
            print(err)

        return {}

    def get_redis_all(self):
        page_num = 1
        while True:
            data = self.get_region_redis(page_num)
            if not data and 'Instances' not in data: break
            page_num += 1
            row = data['Instances']['KVStoreInstance']
            if not row: break
            # print的时候将yield去掉
            # print(list(map(self.format_redis, row)))
            res = list(map(self.format_redis, row))
            yield res

    def format_redis(self, redis_info):
        """
        处理下我们要入库的信息
        :return:
        """
        if not isinstance(redis_info, dict):
            raise TypeError

        asset_data = dict()

        asset_data['db_instance_id'] = redis_info.get('InstanceId')
        asset_data['db_code'] = redis_info.get('InstanceName')
        asset_data['db_region'] = redis_info.get('RegionId')
        asset_data['db_version'] = redis_info.get('EngineVersion')
        asset_data['db_port'] = redis_info.get('Port')
        asset_data['db_public_ip'] = redis_info.get('ConnectionDomain')
        asset_data['db_type'] = redis_info.get('InstanceType')
        asset_data['db_class'] = redis_info.get('ArchitectureType')
        asset_data['state'] = redis_info.get('InstanceStatus')
        asset_data['db_user'] = 'root'  # 没看到user的接口信息，但是我是必填项
        asset_data['db_host'] = redis_info.get('PrivateIp')
        if not asset_data['db_host']: asset_data['db_host'] = asset_data['db_public_ip']

        return asset_data

    def sync_cmdb(self):
        """
        入库
        :return:
        """
        redis_info_list = self.get_redis_all()
        if not redis_info_list: return False
        with DBContext('w') as session:
            for data in redis_info_list:
                for redis in data:
                    ins_log.read_log('info', 'redis信息：{}'.format(redis))
                    db_code = redis.get('db_code')

                    exist_redis = session.query(DB).filter(DB.db_code == db_code).first()

                    if exist_redis:
                        session.query(DB).filter(DB.db_code == db_code).update({
                            DB.idc: self.idc, DB.db_class: redis.get('db_class'), DB.db_host: redis.get('db_host'),
                            DB.db_port: redis.get('db_port'), DB.db_user: redis.get('db_user'),
                            DB.db_disk: redis.get('db_disk'), DB.db_region: redis.get('db_region'),
                            DB.db_type: redis.get('db_type'), DB.db_version: redis.get('db_version'),
                            DB.state: redis.get('state'), DB.db_mark: redis.get('db_mark'),
                            DB.db_public_ip: redis.get('db_public_ip'),
                            DB.db_instance_id: redis.get('db_instance_id')})
                    else:
                        new_db = DB(idc=self.idc, db_code=db_code, db_class=redis.get('db_class'),
                                    db_host=redis.get('db_host'), db_port=redis.get('db_port'),
                                    db_user=redis.get('db_user'), db_region=redis.get('db_region'),
                                    db_type=redis.get('db_type'),
                                    db_disk=redis.get('db_disk'), db_version=redis.get('db_version'),
                                    state=redis.get('state'), db_public_ip=redis.get('db_public_ip'),
                                    db_instance_id=redis.get('db_instance_id'))
                        session.add(new_db)
            session.commit()

    @staticmethod
    def permission_auth(access_id, access_key, region, page_number=1, page_size=1):
        """
        没有异常正常获取到1-1数据就是权限认证通过
        :param access_id: AccessID
        :param access_key:  AccessKey
        :param region:  RegionID
        :param page_number: 第几页
        :param page_size:  一页多少数量
        :return:
        """
        clt = AcsClient(access_id, access_key, region, timeout=5)
        request = DescribeInstancesRequest()
        request.set_accept_format('json')
        request.set_PageNumber(page_number)
        request.set_PageSize(page_size)
        response = clt.do_action_with_exception(request)
        # print('Permission_auth_res-->',response)
        return json.loads(str(response, encoding="utf8"))


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
        obj = RedisApi(access_id, access_key, region)
        obj.sync_cmdb()


if __name__ == '__main__':
    fire.Fire(main)
