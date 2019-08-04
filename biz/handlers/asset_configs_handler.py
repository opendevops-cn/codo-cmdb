#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/5/14 10:30
# @Author  : Fred Yangxiaofei
# @File    : asset_configs_handler.py
# @Role    : 资产配置，主要用来实现AWS/aliyun/qcloud 多账户云机器自动录入CMDB


import json
import tornado.web
from tornado import gen
from concurrent.futures import ThreadPoolExecutor
from tornado.concurrent import run_on_executor
from libs.base_handler import BaseHandler
from models.server import AssetConfigs, model_to_dict
from websdk.db_context import DBContext
from libs.aliyun.ecs import EcsAPi
from libs.qcloud.cvm import CVMApi
from libs.aws.ec2 import Ec2Api
from libs.huaweiyun.huawei_ecs import HuaweiEcsApi
from libs.aliyun.ecs import main as aliyun_update_main
from libs.qcloud.cvm import main as qcloud_update_main
from libs.aws.ec2 import main as aws_update_main
from libs.huaweiyun.huawei_ecs import main as huaweiyun_update_main
from websdk.web_logs import ins_log
from opssdk.operate import MyCryptV2
import openstack
import keystoneauth1

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
        region = data.get('region', None)
        access_id = data.get('access_id', None)
        access_key = data.get('access_key', None)
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
            # exist_region = session.query(AssetConfigs.id).filter(AssetConfigs.region == region).first()
        if exist_id:
            return self.write(dict(code=-2, msg='不要重复记录'))
        #
        # if exist_region:
        #     return self.write(dict(code=-2, msg='Region：{}已经存在'.format(region)))

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


class TestAuthHandler(BaseHandler):
    '''测试用户填写的信息及认证是否正确,防止主进程卡死，使用异步方法测试'''
    _thread_pool = ThreadPoolExecutor(1)

    @run_on_executor(executor='_thread_pool')
    def test_auth(self, account, region, access_id, access_key, project_id, huawei_cloud, huawei_instance_id):
        """
        测试接口权限
        :return:
        """
        # 测试结果
        msg = ''
        default_admin_user = ''  # 测试接口的时候默认管理用户不需要

        if account == 'AWS':
            ins_log.read_log('info', 'AWS API TEST')
            obj = Ec2Api(access_id, access_key, region, default_admin_user)
            try:
                obj.test_auth()
                # print(response)
                # msg = '测试成功'
            except Exception as e:
                msg = '测试失败， 错误信息：{}'.format(e)
                # return self.write(dict(code=-1, msg=msg))
        elif account == '阿里云':
            ins_log.read_log('info', '阿里云 API TEST')
            obj = EcsAPi(access_id, access_key, region, default_admin_user)
            try:
                obj.test_auth()
                # msg = '测试成功'
            except Exception as e:
                msg = '测试失败，错误信息：{}'.format(e)
                # return self.write(dict(code=-1, msg=msg))

        elif account == '腾讯云':
            ins_log.read_log('info', '腾讯云 API TEST')
            obj = CVMApi(access_id, access_key, region, default_admin_user)
            try:
                result_data = obj.test_auth()
                if result_data['Response'].get('Error'):
                    msg = '测试失败，错误信息：{}'.format(result_data['Response'])
                    # return self.write(dict(code=-1, msg=msg))
                # else:
                #     msg = '测试成功'
            except Exception as e:
                ins_log.read_log('error', e)

        elif account == '华为云':
            ins_log.read_log('info', '华为云 API TEST')
            obj = HuaweiEcsApi(access_id=access_id, access_key=access_key, region=region, cloud=huawei_cloud,
                               project_id=project_id,
                               default_admin_user=default_admin_user)
            try:
                obj.test_auth(huawei_instance_id)
            except keystoneauth1.exceptions.http.Unauthorized:
                msg = '请检查AccessID和AccessKey权限是否正确'
            except openstack.exceptions.HttpException as err:
                msg = 'openstack error for {}'.format(err)
            except Exception as e:
                print(e)
                msg = 'error: {}'.format(e)

        return msg

    @gen.coroutine
    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
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

        # 超过120s 返回Timeout
        msg = yield self.test_auth(account, region, access_id, access_key, project_id, huawei_cloud, huawei_instance_id)
        if msg:
            # 失败
            return self.write(dict(code=-1, msg=msg))
        else:
            return self.write(dict(code=0, msg='测试成功'))


class HanderUpdateOSServer(tornado.web.RequestHandler):
    '''前端手动触发从云厂商更新资产,使用异步方法'''
    _thread_pool = ThreadPoolExecutor(3)

    @run_on_executor(executor='_thread_pool')
    def handler_update_task(self):
        aliyun_update_main()
        aws_update_main()
        qcloud_update_main()
        huaweiyun_update_main()

    @gen.coroutine
    def get(self, *args, **kwargs):
        yield self.handler_update_task()
        return self.write(dict(code=0, msg='拉取完成'))


asset_configs_urls = [
    (r"/v1/cmdb/asset_configs/", AssetConfigsHandler),
    (r"/v1/cmdb/asset_configs/handler_update_server/", HanderUpdateOSServer),
    (r"/v1/cmdb/asset_configs/test_auth/", TestAuthHandler)

]
