#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/5/14 10:30
# @Author  : Fred Yangxiaofei
# @File    : asset_configs_handler.py
# @Role    : 资产配置，主要用来实现AWS/aliyun/qcloud 多账户云机器自动录入CMDB

import json
import time
import openstack
import keystoneauth1
import tornado.web
from tornado import gen
from concurrent.futures import ThreadPoolExecutor
from tornado.concurrent import run_on_executor

from models.server import AssetConfigs, model_to_dict
from websdk.db_context import DBContext
from websdk.web_logs import ins_log
from opssdk.operate import MyCryptV2
from libs.base_handler import BaseHandler
from libs.aws.ec2 import Ec2Api
from libs.aws.rds import RDSApi as AwsRdsApi
from libs.aws.ec2 import main as aws_ec2_update
from libs.aws.rds import main as aws_rds_update
from libs.aws.elasticache import main as aws_cache_update
from libs.aws.elasticache import CacheApi as AwsCacheApi
from libs.aliyun.ecs import EcsAPi
from libs.aliyun.rds import RdsApi as AliyunRdsApi
from libs.aliyun.redis import RedisApi as AliyunRedisApi
from libs.aliyun.ecs import main as aliyun_ecs_update
from libs.aliyun.rds import main as aliyun_rds_update
from libs.aliyun.redis import main as aliyun_redis_update
from libs.qcloud.cvm import CVMApi
from libs.qcloud.cdb import CDBApi as QcloudCdbApi
from libs.qcloud.redis import RedisApi
from libs.qcloud.cvm import main as qcloud_cvm_update
from libs.qcloud.cdb import main as qcloud_cdb_update
from libs.qcloud.redis import main as qcloud_redis_update
from libs.huaweiyun.huawei_ecs import HuaweiEcsApi
from libs.huaweiyun.huawei_ecs import main as huawei_ecs_update
from ucloud.core import exc
from libs.ucloud.uhost import UHostAPI
from libs.ucloud.uhost import main as ucloud_uhost_update
from libs.ucloud.udb import UdbAPI
from libs.ucloud.udb import main as ucloud_udb_update
from libs.ucloud.uredis import UredisAPI
from libs.ucloud.uredis import main as ucloud_uredis_update

mc = MyCryptV2()  # 实例化


class AssetConfigsHandler(BaseHandler):
    def get(self, *args, **kwargs):
        key = self.get_argument('key', default=None, strip=True)
        value = self.get_argument('value', default=None, strip=True)
        asset_configs_list = []
        with DBContext('r') as session:
            if key and value:
                asset_configs_data = session.query(AssetConfigs).filter_by(**{key: value}).all()
            else:
                asset_configs_data = session.query(AssetConfigs).all()

        for data in asset_configs_data:
            data_dict = model_to_dict(data)
            data_dict['create_time'] = str(data_dict['create_time'])
            data_dict['update_time'] = str(data_dict['update_time'])
            # 解密AccessKey
            if data_dict.get('access_key'):
                data_dict['access_key'] = mc.my_decrypt(data_dict.get('access_key'))
            asset_configs_list.append(data_dict)

        return self.write(dict(code=0, msg='获取成功', data=asset_configs_list))

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        name = data.get('name', None)
        account = data.get('account', None)
        region = data.get('region', None).strip()
        access_id = data.get('access_id', None).strip()
        access_key = data.get('access_key', None).strip()
        default_admin_user = data.get('default_admin_user', None)
        state = data.get('state', None)
        remarks = data.get('remarks', None)
        # 华为云需要额外三个数据
        project_id = data.get('project_id', 'Null')
        huawei_cloud = data.get('huawei_cloud', 'Null')
        huawei_instance_id = data.get('huawei_instance_id', 'Null')

        if not name or not account or not region or not access_id or not access_key or not state:
            return self.write(dict(code=-2, msg='关键参数不能为空'))

        with DBContext('r', None, True) as session:
            exist_id = session.query(AssetConfigs.id).filter(AssetConfigs.name == name).first()

        if exist_id:
            return self.write(dict(code=-2, msg='不要重复记录'))

        # 对密钥进行加密再写数据库
        _access_key = mc.my_encrypt(access_key)

        with DBContext('w', None, True) as session:
            new_asset_config = AssetConfigs(name=name, account=account, region=region, access_id=access_id,
                                            access_key=_access_key, default_admin_user=default_admin_user, state=state,
                                            remarks=remarks, project_id=project_id, huawei_cloud=huawei_cloud,
                                            huawei_instance_id=huawei_instance_id)
            session.add(new_asset_config)

        return self.write(dict(code=0, msg='添加成功'))

    def put(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        id = data.get('id', None)
        name = data.get('name', None)
        account = data.get('account', None)
        region = data.get('region', None)
        access_id = data.get('access_id', None)
        access_key = data.get('access_key', None)
        default_admin_user = data.get('default_admin_user', None)
        state = data.get('state', None)
        remarks = data.get('remarks', None)
        # 华为云需要额外三个数据
        project_id = data.get('project_id', None)
        huawei_cloud = data.get('huawei_cloud', None)
        huawei_instance_id = data.get('huawei_instance_id', None)

        if not name or not account or not region or not access_id or not access_key or not state:
            return self.write(dict(code=-2, msg='关键参数不能为空'))

        # 对密钥进行加密再写数据库
        _access_key = mc.my_encrypt(access_key)
        with DBContext('w', None, True) as session:
            session.query(AssetConfigs).filter(AssetConfigs.id == id).update(
                {AssetConfigs.account: account, AssetConfigs.access_id: access_id, AssetConfigs.access_key: _access_key,
                 AssetConfigs.default_admin_user: default_admin_user, AssetConfigs.state: state,
                 AssetConfigs.remarks: remarks, AssetConfigs.project_id: project_id,
                 AssetConfigs.huawei_cloud: huawei_cloud, AssetConfigs.huawei_instance_id: huawei_instance_id})
        return self.write(dict(code=0, msg='编辑成功'))

    def patch(self, *args, **kwargs):
        '''开关控制，开启/禁用'''
        data = json.loads(self.request.body.decode("utf-8"))
        id = data.get('id')

        msg = 'Not Fount!'

        if not id:
            return self.write(dict(code=-2, msg='关键参数不能为空'))

        with DBContext('r') as session:
            config_state = session.query(AssetConfigs.state).filter(AssetConfigs.id == id).first()

            if not config_state:
                return self.write(dict(code=0, msg=msg))

        if config_state[0] == 'false':
            msg = '启用成功'
            new_state = 'true'

        elif config_state[0] == 'true':
            msg = '禁用成功'
            new_state = 'false'

        with DBContext('w', None, True) as session:
            # print(new_state)
            session.query(AssetConfigs).filter(AssetConfigs.id == id).update({AssetConfigs.state: new_state})

        return self.write(dict(code=0, msg=msg))

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        id = data.get('id')
        if not id:
            return self.write(dict(code=-2, msg='关键参数不能为空'))

        with DBContext('w', None, True) as session:
            session.query(AssetConfigs).filter(AssetConfigs.id == id).delete(synchronize_session=False)

        self.write(dict(code=0, msg='删除成功'))


class ApiPermissionHandler(BaseHandler):
    '''测试用户填写的信息及认证是否正确,防止主进程卡死，使用异步方法测试'''
    _thread_pool = ThreadPoolExecutor(3)

    @run_on_executor(executor='_thread_pool')
    def server_api(self, account, region, access_id, access_key, project_id, huawei_cloud, huawei_instance_id):
        """
        测试各厂商server API的权限
        :return:
        """
        # 收集测试错误日志
        err_msg = ''
        # 测试接口的时候默认管理用户不需要
        default_admin_user = ''
        if account == 'AWS':
            ins_log.read_log('info', 'AWS EC2 API TEST')
            obj = Ec2Api(access_id, access_key, region, default_admin_user)
            try:
                obj.test_auth()
            except Exception as e:
                err_msg = 'Error：{}'.format(e)
        elif account == '阿里云':
            ins_log.read_log('info', 'Aliyun  ECS API TEST')
            obj = EcsAPi(access_id, access_key, region, default_admin_user)
            try:
                obj.test_auth()
            except Exception as e:
                err_msg = 'Error：{}'.format(e)

        elif account == '腾讯云':
            ins_log.read_log('info', 'Qcloud  CVM API TEST')
            obj = CVMApi(access_id, access_key, region, default_admin_user)
            try:
                result_data = obj.test_auth()
                if result_data['Response'].get('Error'):
                    err_msg = 'Error：{}'.format(result_data['Response'])
            except Exception as e:
                ins_log.read_log('error', e)

        elif account == '华为云':
            ins_log.read_log('info', 'HuaweiCloud  ECS API TEST')
            obj = HuaweiEcsApi(access_id=access_id, access_key=access_key, region=region, cloud=huawei_cloud,
                               project_id=project_id,
                               default_admin_user=default_admin_user)
            try:
                obj.test_auth(huawei_instance_id)
            except keystoneauth1.exceptions.http.Unauthorized:
                err_msg = '请检查AccessID和AccessKey权限是否正确'
            except openstack.exceptions.HttpException as err:
                err_msg = 'openstack error {}'.format(err)
            except Exception as e:
                err_msg = 'error: {}'.format(e)
        elif account == 'UCloud':
            ins_log.read_log('info', 'UCloud  Uhost API TEST')
            try:
                UHostAPI.permission_auth(access_id=access_id, access_key=access_key, region=region,
                                         project_id=project_id)
            except exc.UCloudException as uerr:
                err_msg = 'ucloud error: {ucloud_error}'.format(ucloud_error=uerr)
            except Exception as e:
                err_msg = 'error: {}'.format(e)
        else:
            err_msg = 'In Development.'
        return err_msg

    @run_on_executor(executor='_thread_pool')
    def rds_api(self, account, region, access_id, access_key, project_id):
        """
        测试DB API权限
        :return:
        """
        # 错误收集
        err_msg = ''
        if account == 'AWS':
            ins_log.read_log('info', 'AWS RDS API TEST')
            obj = AwsRdsApi(access_id, access_key, region, )
            try:
                obj.test_auth()
            except Exception as e:
                err_msg = 'Error：{}'.format(e)
        elif account == '阿里云':
            ins_log.read_log('info', 'Aliyun  RDS API TEST')
            obj = AliyunRdsApi(access_id, access_key, region)
            try:
                obj.test_auth()
            except Exception as e:
                err_msg = 'Error：{}'.format(e)

        elif account == '腾讯云':
            ins_log.read_log('info', 'Qcloud  CDB API TEST')
            obj = QcloudCdbApi(access_id, access_key, region)
            try:
                result_data = obj.test_auth()
                if result_data['Response'].get('Error'):
                    err_msg = 'Error：{}'.format(result_data['Response'])
            except Exception as e:
                ins_log.read_log('error', e)
        elif account == 'UCloud':
            ins_log.read_log('info', 'UCloud UDB API TEST')
            try:
                UdbAPI.permission_auth(access_id=access_id, access_key=access_key, region=region,
                                       project_id=project_id)
            except exc.UCloudException as uerr:
                err_msg = 'ucloud error: {ucloud_error}'.format(ucloud_error=uerr)
            except Exception as e:
                err_msg = 'error: {}'.format(e)

        else:
            err_msg = 'In Development.'

        return err_msg

    @run_on_executor(executor='_thread_pool')
    def redis_api(self, account, region, access_id, access_key, project_id):
        """
        测试redis API权限
        :return:
        """
        # 错误收集
        err_msg = ''

        if account == 'AWS':
            ins_log.read_log('info', 'AWS redis API TEST')
            # err_msg = 'In Development'
            try:
                AwsCacheApi.permission_auth(access_id, access_key, region)
            except Exception as e:
                err_msg = 'Error:{}'.format(e)

        elif account == '阿里云':
            ins_log.read_log('info', 'Aliyun Redis API TEST')
            try:
                AliyunRedisApi.permission_auth(access_id, access_key, region)
            except Exception as e:
                err_msg = 'Error:{}'.format(e)

        elif account == '腾讯云':
            ins_log.read_log('info', 'QCloud Redis API TEST')
            try:
                obj = RedisApi(access_id, access_key, region)
                result_data = obj.test_auth()
                if result_data['Response'].get('Error'):
                    err_msg = 'Error：{}'.format(result_data['Response'])
            except Exception as e:
                ins_log.read_log('Error', e)
        elif account == 'UCloud':
            ins_log.read_log('info', 'UCloud Uredis API TEST')
            try:
                UredisAPI.permission_auth(access_id=access_id, access_key=access_key, region=region,
                                          project_id=project_id)
            except exc.UCloudException as uerr:
                err_msg = 'ucloud error: {ucloud_error}'.format(ucloud_error=uerr)
            except Exception as e:
                err_msg = 'error: {}'.format(e)
        else:
            # 其余厂商
            err_msg = 'In Development'
        return err_msg

    @gen.coroutine
    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        api_type = data.get('api_type', None)
        account = data.get('account', None)
        region = data.get('region', None)
        access_id = data.get('access_id', None)
        access_key = data.get('access_key', None)
        project_id = data.get('project_id', None)
        huawei_cloud = data.get('huawei_cloud', None)
        huawei_instance_id = data.get('huawei_instance_id', None)

        if not account or not region or not access_id or not access_key:
            return self.write(dict(code=-2, msg="测试必须要包含：厂商、Region、 Access_id 、Access_key"))

        if account == '华为云':
            if not project_id or not huawei_cloud or not huawei_instance_id:
                return self.write(dict(code=-2, msg="华为云测试必须包含：Cloud地址、区域项目ID、一个实例ID"))
        elif account == 'UCloud':
            if not project_id:
                return self.write(dict(code=-2, msg="UCloud测试必须包含：项目ID"))

        if api_type == 'server':
            error_msg = yield self.server_api(account, region, access_id, access_key, project_id, huawei_cloud,
                                              huawei_instance_id)
            if error_msg: return self.write(dict(code=-1, msg=error_msg))
            return self.write(dict(code=0, msg='Successful'))
        elif api_type == 'rds':
            error_msg = yield self.rds_api(account, region, access_id, access_key, project_id)
            if error_msg: return self.write(dict(code=-1, msg=error_msg))
            return self.write(dict(code=0, msg='Successful'))
        elif api_type == 'redis':
            error_msg = yield self.redis_api(account, region, access_id, access_key, project_id)
            if error_msg: return self.write(dict(code=-1, msg=error_msg))
            return self.write(dict(code=0, msg='Successful'))
        else:
            return self.write(dict(code=-1, msg='In Development'))


class HanderUpdateOSServer(tornado.web.RequestHandler):
    '''前端手动触发从云厂商更新资产,使用异步方法'''
    _thread_pool = ThreadPoolExecutor(3)

    @run_on_executor(executor='_thread_pool')
    def handler_update_task(self):
        aliyun_ecs_update()
        time.sleep(2)
        aws_ec2_update()
        time.sleep(2)
        qcloud_cvm_update()
        time.sleep(2)
        huawei_ecs_update()
        time.sleep(2)
        ucloud_uhost_update()

    @gen.coroutine
    def get(self, *args, **kwargs):
        yield self.handler_update_task()
        return self.write(dict(code=0, msg='服务器信息拉取完成'))


class HanderUpdateOSRds(tornado.web.RequestHandler):
    '''前端手动触发从云厂商更新资产,使用异步方法'''
    _thread_pool = ThreadPoolExecutor(3)

    @run_on_executor(executor='_thread_pool')
    def handler_update_task(self):
        aws_rds_update()
        time.sleep(1)
        qcloud_cdb_update()
        time.sleep(1)
        aliyun_rds_update()
        time.sleep(1)
        ucloud_udb_update()

    @gen.coroutine
    def get(self, *args, **kwargs):
        yield self.handler_update_task()
        return self.write(dict(code=0, msg='数据库信息拉取完成'))


class HanderUpdateOSRedis(tornado.web.RequestHandler):
    '''前端手动触发从云厂商更新资产,使用异步方法'''
    _thread_pool = ThreadPoolExecutor(3)

    @run_on_executor(executor='_thread_pool')
    def handler_update_task(self):
        qcloud_redis_update()
        time.sleep(1)
        aliyun_redis_update()
        time.sleep(1)
        aws_cache_update()
        time.sleep(1)
        ucloud_uredis_update()

    @gen.coroutine
    def get(self, *args, **kwargs):
        yield self.handler_update_task()
        return self.write(dict(code=0, msg='Redis信息拉取完成'))


asset_configs_urls = [
    (r"/v1/cmdb/asset_configs/", AssetConfigsHandler),
    (r"/v1/cmdb/asset_configs/handler_update_server/", HanderUpdateOSServer),
    (r"/v1/cmdb/asset_configs/handler_update_rds/", HanderUpdateOSRds),
    (r"/v1/cmdb/asset_configs/handler_update_redis/", HanderUpdateOSRedis),
    (r"/v1/cmdb/asset_configs/api_permission/", ApiPermissionHandler),
]
