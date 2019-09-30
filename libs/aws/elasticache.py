#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File  : elasticache.py
# @Author: Fred Yangxiaofei
# @Date  : 2019/9/5
# @Role  : 获取AWS Redis集群信息


import boto3
from libs.db_context import DBContext
from libs.web_logs import ins_log
from models.db import DB
from models.server import AssetConfigs, model_to_dict
from opssdk.operate import MyCryptV2
import fire


class CacheApi():
    def __init__(self, access_id, access_key, region):
        self.idc = 'AWS'
        self.access_id = access_id
        self.access_key = access_key
        self.region = region
        self.client = self.conn()

    def conn(self):
        try:
            client = boto3.client('elasticache', region_name=self.region, aws_access_key_id=self.access_id,
                                  aws_secret_access_key=self.access_key)
            return client
        except Exception as err:
            ins_log.read_log('error', 'Error:{err}'.format(err=err))
            return False

    def get_region_memcached(self):
        """
        获取memcached缓存信息
        Boto3 Docs: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/elasticache.html#ElastiCache.Client.describe_cache_clusters
        :return:
        """
        try:
            response = self.client.describe_cache_clusters(
                MaxRecords=100,
                ShowCacheNodeInfo=True,
                ShowCacheClustersNotInReplicationGroups=True
            )
            memcached_clusters = response.get('CacheClusters')
            if not memcached_clusters: return []
            res = list(map(self.format_region_memcached, memcached_clusters))
            return res
        except Exception as err:
            ins_log.read_log('error', 'Error:{err}'.format(err=err))
            return []

    def format_region_memcached(self, memcached_data):
        """
        format memcached
        :return:
        """
        if not isinstance(memcached_data, dict):
            raise TypeError

        asset_data = dict()
        asset_data['db_user'] = 'root'  # 标记下，没有用户入不了库
        asset_data['db_code'] = memcached_data.get('CacheClusterId')  # 实例名称
        asset_data['db_class'] = memcached_data.get('CacheNodeType')  # 实例类型
        asset_data['db_host'] = memcached_data.get('ConfigurationEndpoint').get('Address')
        asset_data['db_port'] = memcached_data.get('ConfigurationEndpoint').get('Port')
        asset_data['db_region'] = memcached_data.get('PreferredAvailabilityZone')  # 区域、可用区
        asset_data['db_version'] = memcached_data.get('EngineVersion')  # 名称
        asset_data['db_type'] = memcached_data.get('Engine')  # 类型,memcached
        asset_data['state'] = memcached_data.get('CacheClusterStatus')  # 状态

        return asset_data

    def get_region_redis(self):
        """
        Docs:https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/elasticache.html#ElastiCache.Client.describe_replication_groups
        :return:
        """
        try:
            response = self.client.describe_replication_groups(MaxRecords=100)
            redis_clusters = response.get('ReplicationGroups')
            if not redis_clusters: return False
            res = list(map(self.format_region_redis, redis_clusters))
            return res

        except Exception as err:
            ins_log.read_log('error', 'Error:{err}'.format(err=err))
            return False

    def format_region_redis(self, redis_data):
        """
        format redis data
        :param redis_data: dict
        :return:
        """
        if not isinstance(redis_data, dict):
            raise TypeError

        # print(redis_data)
        asset_data = dict()
        node_groups = redis_data.get('NodeGroups')

        filter_result = filter(lambda x: "PrimaryEndpoint" in x.keys(), node_groups)
        map_result = map(lambda x: x.get("PrimaryEndpoint"), filter_result)
        # node_groups列表里面有很多节点信息，PrimaryEndpoint\ReaderEndpoint\子节点信息等，我们只要一个主的信息
        # for i in node_groups:
        #     if 'PrimaryEndpoint' in i.keys():
        #         asset_data['db_host'] = i.get('PrimaryEndpoint').get('Address')
        #         asset_data['db_port'] = i.get('PrimaryEndpoint').get('Port')
        primary_endpoint = list(map_result)
        asset_data['db_host'] = primary_endpoint[0]['Address']
        asset_data['db_port'] = primary_endpoint[0]['Port']
        asset_data['db_mark'] = 'Primary'
        asset_data['db_user'] = 'root'
        asset_data['db_code'] = redis_data.get('ReplicationGroupId')  # 实例名称
        asset_data['db_class'] = redis_data.get('CacheNodeType')  # 实例类型
        asset_data['db_region'] = self.region  # 区域、可用区
        asset_data['db_type'] = 'redis'  # 类型,memcached
        asset_data['state'] = redis_data.get('Status')  # 状态
        asset_data['db_detail'] = ','.join(redis_data.get('MemberClusters'))  # 把子节点机器名字写到备注里面吧

        return asset_data

    def sync_cmdb(self):
        """
        入库
        :return:
        """
        redis_info_list = self.get_region_redis()
        memcached_info_list = self.get_region_memcached()
        if not redis_info_list and not memcached_info_list:
            return False

        cache_list = []
        cache_list.extend(redis_info_list)
        cache_list.extend(memcached_info_list)

        if not cache_list: return False
        with DBContext('w') as session:
            for i in cache_list:
                ins_log.read_log('info', 'Cache info：{}'.format(i))
                db_code = i.get('db_code')

                exist_redis = session.query(DB).filter(DB.db_code == db_code).first()

                if exist_redis:
                    session.query(DB).filter(DB.db_code == db_code).update({
                        DB.idc: self.idc, DB.db_class: i.get('db_class'), DB.db_host: i.get('db_host'),
                        DB.db_port: i.get('db_port'), DB.db_region: i.get('db_region'),
                        DB.db_type: i.get('db_type'), DB.db_version: i.get('db_version'),
                        DB.db_mark: i.get('db_mark'), DB.state: i.get('state')})
                else:
                    new_db = DB(idc=self.idc, db_code=db_code, db_class=i.get('db_class'),
                                db_host=i.get('db_host'), db_port=i.get('db_port'), db_mark=i.get('db_mark'),
                                db_user=i.get('db_user'), db_region=i.get('db_region'),
                                db_type=i.get('db_type'), db_version=i.get('db_version'),
                                state=i.get('state'), db_detail=i.get('db_detail'))
                    session.add(new_db)
            session.commit()

    @staticmethod
    def permission_auth(access_id, access_key, region):
        """
        没有异常正常获取到1-1数据就是权限认证通过
        :param access_id: AccessID
        :param access_key:  AccessKey
        :param region:  RegionID
        :return:
        """

        client = boto3.client('elasticache', region_name=region, aws_access_key_id=access_id,
                              aws_secret_access_key=access_key)
        response = client.describe_replication_groups(MaxRecords=20)
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

        obj = CacheApi(access_id, access_key, region)
        obj.sync_cmdb()

if __name__ == '__main__':
     fire.Fire(main)