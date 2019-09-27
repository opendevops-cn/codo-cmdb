#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019-08-22 17:09
# @Author  : Yangxiaofei
# @File    : rds.py
# @Role    : 获取阿里云RDS信息入库


import json
from aliyunsdkcore.client import AcsClient
from aliyunsdkrds.request.v20140815.DescribeDBInstancesRequest import DescribeDBInstancesRequest
from aliyunsdkrds.request.v20140815.DescribeDBInstanceAttributeRequest import DescribeDBInstanceAttributeRequest
from libs.db_context import DBContext
from models.db import DB
from models.server import AssetConfigs, model_to_dict
from libs.web_logs import ins_log
from opssdk.operate import MyCryptV2
import fire


class RdsApi():
    def __init__(self, access_id, access_key, region):
        self.idc = '阿里云'
        self.region = region
        self.access_id = access_id
        self.access_key = access_key
        self.page_number = 1  # 实例状态列表的页码。起始值：1 默认值：1
        self.page_size = 5  # 分页查询时设置的每页行数。最大值：100 默认值：30
        self.client = self.create_client()

    def create_client(self):
        client = AcsClient(self.access_id, self.access_key, self.region)
        return client

    def set_desc_request(self):
        request = DescribeDBInstancesRequest()
        request.set_accept_format('json')
        request.set_PageNumber(self.page_number)
        request.set_PageSize(self.page_size)
        return request

    def get_desc_response(self):
        """
        获取返回值
        :return:
        """

        response_data = {}
        err = None
        request = self.set_desc_request()
        try:
            response = self.client.do_action_with_exception(request)
            response_data = json.loads(str(response, encoding="utf8"))
        except Exception as e:
            err = e

        # print('Reponse:{}'.format(response_data))
        return response_data, err

    def get_tocal_rds_instanceid_list(self):
        pass
        """
        获取所有RDS实例ID列表
        :return:
        """
        # i = 1
        # while True:
        #     response_data, err = self.get_desc_response()
        #     if err != None: break
        #     if 'Items' not in response_data:break
        #     if 'DBInstance' not in response_data:break
        #     i += 1
        #     rds_data = response_data['Items']['DBInstance']
        #
        #
        #     if rds_data:
        #         ins_log.read_log('info', 'Region:{region} - PageNumber:{page}'.format(region=self.region, page=self.page_size))
        #         print(rds_data)
        #         yield rds_data
        #         res = list(map(self.get_attribute_rds, rds_data))
        #     else:
        #         break

    def get_rds_count(self):
        """
        获取机器总数
        :return:
        """
        response_data, err = self.get_desc_response()
        if err != None:
            ins_log.read_log('error', err)
            return False
        count = response_data['TotalRecordCount']
        # print('RdsCount: {count}'.format(count=count))
        return count

    def get_db_instance_id(self):
        """
        获取数据库实例ID
        :return:
        """
        response_data, err = self.get_desc_response()
        if err != None: return False
        rds_data = response_data['Items']['DBInstance']
        if not rds_data: return False
        db_instanceid_list = []
        for i in rds_data:
            db_instanceid_list.append(i.get('DBInstanceId'))

        # print('InstanceIDList: {}'.format(db_instanceid_list))
        return db_instanceid_list

    def get_attribute_response(self):
        """
        获取实例详细信息
        :return:
        """

        instance_id_list = self.get_db_instance_id()
        if not isinstance(instance_id_list, list):
            raise TypeError

        rds_attribute_data_list = []
        try:
            request = DescribeDBInstanceAttributeRequest()
            request.set_accept_format('json')
            for instance_id in instance_id_list:
                request.set_DBInstanceId(instance_id)
                response = self.client.do_action_with_exception(request)
                response_data = json.loads(str(response, encoding="utf8"))
                rds_attribute_data = response_data['Items']['DBInstanceAttribute'][0]
                rds_attribute_data_list.append(rds_attribute_data)

            return rds_attribute_data_list
        except Exception as e:
            print(e)
            return False

    def get_rds_info(self):
        """
        只获取到想要的信息
        :return:
        """
        rds_attribute_data_list = self.get_attribute_response()

        if not rds_attribute_data_list:
            ins_log.read_log('error', 'Not fount rds attribute info...')
            return False

        rds_list = []
        for i in rds_attribute_data_list:
            asset_data = dict()
            asset_data['db_instance_id'] = i.get('DBInstanceId')
            asset_data['db_code'] = i.get('DBInstanceDescription')
            asset_data['db_class'] = i.get('DBInstanceClass')
            asset_data['db_host'] = i.get('ConnectionString')
            asset_data['db_port'] = i.get('Port')
            asset_data['db_disk'] = i.get('DBInstanceStorage')
            asset_data['db_type'] = i.get('Engine')
            asset_data['db_version'] = i.get('EngineVersion')
            asset_data['state'] = i.get('DBInstanceStatus')
            asset_data['db_mark'] = i.get('DBInstanceType')
            asset_data['db_region'] = i.get('ZoneId')
            asset_data['db_detail'] = i.get('DBInstanceDescription')
            rds_list.append(asset_data)

        return rds_list

    def sync_cmdb(self):
        """
        将我们拿到的数据入库
        :return:
        """
        rds_info_list = self.get_rds_info()
        if not rds_info_list:
            ins_log.read_log('error', '[Error]: Not get redis info...')
            return False

        with DBContext('w') as session:
            for rds in rds_info_list:
                ins_log.read_log('info', 'RDS信息：{}'.format(rds))
                db_code = rds.get('db_code')

                try:
                    db_user = rds['user']
                except KeyError:
                    # 没有从接口看到阿里云的User
                    db_user = 'root'
                exist_rds = session.query(DB).filter(DB.db_code == db_code).first()

                if exist_rds:
                    session.query(DB).filter(DB.db_code == db_code).update({
                        DB.idc: self.idc, DB.db_class: rds.get('db_class'), DB.db_host: rds.get('db_host'),
                        DB.db_port: rds.get('db_port'), DB.db_user: db_user,
                        DB.db_disk: rds.get('db_disk'), DB.db_region: rds.get('db_region'),
                        DB.db_type: rds.get('db_type'), DB.db_version: rds.get('db_version'),
                        DB.state: rds.get('state'), DB.db_mark: rds.get('db_mark'),
                        DB.db_instance_id: rds.get('db_instance_id'), DB.db_detail: rds.get('db_detail')})
                else:
                    new_db = DB(idc=self.idc, db_code=db_code, db_class=rds.get('db_class'), db_host=rds.get('db_host'),
                                db_port=rds.get('db_port'), db_user=db_user, db_disk=rds.get('db_disk'),
                                db_region=rds.get('db_region'), db_type=rds.get('db_type'), db_mark=rds.get('db_mark'),
                                db_version=rds.get('db_version'), state=rds.get('state'),
                                db_instance_id=rds.get('db_instance_id'), db_detail=rds.get('db_detail'))
                    session.add(new_db)
            session.commit()

    def test_auth(self):
        self.page_number = '1'
        self.page_size = '1'
        request = self.set_desc_request()
        response = self.client.do_action_with_exception(request)
        response_data = json.loads(str(response, encoding="utf8"))
        return response_data

    def index(self):
        """
        阿里云若机器超过100台需要进行通过PageSize+PageSize获取
        :return:
        """

        count = self.get_rds_count()
        print('Tocal：{}'.format(count))

        self.page_size = 100
        mod = count % self.page_size
        if mod:
            total_page_number = int(count / self.page_size) + 1
        else:
            total_page_number = int(count / self.page_size)
        for cur_page_number in range(1, total_page_number + 1):
            self.page_number = cur_page_number
            ins_log.read_log('info', '开始同步阿里云区域：{}第{}页的{}台数据库'.format(self.region, self.page_number, self.page_size))
            self.sync_cmdb()

    # def index(self):
    #     """
    #     若机器超过100台需要进行通过offset+limit获取
    #     :return:
    #     """
    #     count = self.get_rds_count()
    #     # print('Tocal：{}'.format(count))
    #     for c in range(0, count, 100):
    #         self.page_number = str(c)
    #         if (c + 100) > count:
    #             self.page_size = str(count)
    #         else:
    #             self.page_size = str(c + 100)
    #         ins_log.read_log('info',
    #                          '开始同步阿里云区域:{}的第{}--{}台RDS数据库'.format(self.region, self.page_number, self.page_size))
    #         self.sync_cmdb()


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

        obj = RdsApi(access_id, access_key, region)
        obj.index()


if __name__ == '__main__':
    fire.Fire(main)
