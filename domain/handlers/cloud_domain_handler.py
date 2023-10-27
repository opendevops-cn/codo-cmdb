#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2019/5/6
"""

import json
import datetime
from abc import ABC
from tornado.concurrent import run_on_executor
from concurrent.futures import ThreadPoolExecutor
from tornado import gen
from sqlalchemy import or_
from libs.base_handler import BaseHandler
from domain.cloud_domain import domain_factory, domain_main
from websdk2.model_utils import queryset_to_list, model_to_dict
from websdk2.db_context import DBContext
from models.domain import DomainName, DomainRecords, DomainOptLog
from models.cloud import CloudSettingModels
from services.domain_service import get_cloud_domain, get_domain_opt_log, add_domain_name, up_domain_name, \
    del_domain_name, get_cloud_record
from libs.mycrypt import MyCrypt

mc = MyCrypt()


class CloudDomainHandler(BaseHandler, ABC):
    def get(self, *args, **kwargs):
        res = get_cloud_domain(**self.params)
        self.write(res)

    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        record_end_time = data.get('record_end_time')
        end_time = datetime.datetime.strptime(record_end_time, "%Y-%m-%dT%H:%M:%S.%fZ") + datetime.timedelta(hours=8)
        data['record_end_time'] = end_time
        res = add_domain_name(**data)
        self.write(res)

    def put(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        res = up_domain_name(data)
        self.write(res)

    def patch(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        res = up_domain_name(data)
        self.write(res)

    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        data['user'] = self.request_fullname()
        res = del_domain_name(data)
        self.write(res)


def add_log(log_data):
    with DBContext('w', None, True) as session:
        session.add(DomainOptLog(**log_data))


class CloudRecordHandler(BaseHandler, ABC):
    _thread_pool = ThreadPoolExecutor(8)

    def get(self, *args, **kwargs):

        if not self.params.get('domain_name'):
            return self.write(dict(code=-1, msg='关键参数域名不能为空'))

        res = get_cloud_record(**self.params)
        self.write(res)

    @run_on_executor(executor='_thread_pool')
    def domain_post(self, domain, **base_new_dict):
        return domain.add_record(**base_new_dict)

    @gen.coroutine
    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        domain_name = data.get('domain_name')
        domain_rr = data.get('domain_rr')
        with DBContext('r') as session:
            domain_obj = session.query(DomainName).filter(DomainName.domain_name == domain_name).first()
            account_obj = session.query(CloudSettingModels).filter(
                CloudSettingModels.account_id == domain_obj.account).first()

        base_new_dict = dict(domain_name=domain_name, domain_rr=domain_rr,
                             domain_type=data.get('domain_type'),
                             domain_value=data.get('domain_value'),
                             domain_ttl=int(data.get('domain_ttl')),
                             domain_mx=int(data.get('domain_mx', 0)),
                             weight=int(data.get('weight', 10)),
                             line=data.get('line'),
                             )
        try:
            domain = domain_factory(account_obj.cloud_name, domain_name=domain_name, domain_id=domain_obj.domain_id,
                                    access_id=account_obj.access_id, access_key=mc.my_decrypt(account_obj.access_key))
            result_data = yield self.domain_post(domain, **base_new_dict)

        except Exception as err:
            log_data = dict(
                domain_name=domain_name, username=self.request_username, action="API",
                record=f'账号别名：{account_obj.name}， 错误信息：{err}',
                state="失败"
            )
            add_log(log_data)
            return self.write(dict(code=-1, msg='添加失败，详情请看日志'))

        if result_data:
            log_state = "成功"
            new_dict = {**base_new_dict, **dict(account=account_obj.account_id, record_id=result_data)}
            with DBContext('w', None, True) as session:
                session.add(DomainRecords(**new_dict))

        else:
            log_state = "失败"

        log_data = dict(domain_name=domain_name, username=self.request_username, action="添加",
                        record=f"类型：{data.get('domain_type')}， {domain_rr}， 线路：{data.get('line')}， 记录：{data.get('domain_value')}， (TTL：{data.get('domain_ttl')}) (weight：{data.get('weight')})",
                        state=log_state)
        add_log(log_data)
        # with DBContext('w', None, True) as session:
        #     session.add(DomainOptLog(**log_data))

        if not result_data:  return self.write(dict(code=-1, msg='添加失败，详情请看日志'))
        return self.write(dict(code=0, msg='添加成功，详细变更信息请看日志'))

    @run_on_executor(executor='_thread_pool')
    def domain_put(self, domain, **base_new_dict):
        return domain.update_record(**base_new_dict)

    @gen.coroutine
    def put(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        the_id = data.get('id')
        if not the_id: return self.write(dict(code=1, msg='关键参数不能为空'))

        with DBContext('r') as session:
            record_obj = session.query(DomainRecords).filter(DomainRecords.id == int(the_id)).first()
            domain_name = record_obj.domain_name
            account_obj = session.query(CloudSettingModels).filter(
                CloudSettingModels.account_id == record_obj.account).first()
            domain_obj = session.query(DomainName).filter(DomainName.domain_name == domain_name).first()

        if account_obj.cloud_name in ['GoDaddy', 'godaddy']:
            return self.write(dict(code=3, msg='GoDaddy 接口有BUG，暂时不支持修改'))
        base_new_dict = dict(record_id=record_obj.record_id, domain_name=domain_name,
                             domain_rr=data.get('domain_rr'),
                             domain_type=data.get('domain_type'),
                             domain_value=data.get('domain_value'),
                             domain_ttl=int(data.get('domain_ttl')),
                             domain_mx=int(data.get('domain_mx', 0) or 0),
                             weight=int(data.get('weight', 10) or 10),
                             line=data.get('line'))
        log_data = dict(
            domain_name=domain_name,
            username=self.request_nickname,
            action="修改前",
            # record='类型：{}， {}， 线路：{}， 记录：{}， (TTL：{})'.format(record_obj.domain_type, record_obj.domain_rr,
            #                                                         record_obj.line, record_obj.domain_value,
            #                                                         record_obj.domain_ttl),
            record=f"类型：{record_obj.domain_type}， {record_obj.domain_rr}， 线路：{record_obj.line}， 记录：{record_obj.domain_value}，"
                   f" (TTL：{record_obj.domain_ttl}) (weight：{record_obj.weight})",
            state="成功"
        )
        with DBContext('w', None, True) as session:
            session.add(DomainOptLog(**log_data))

            try:
                domain = domain_factory(account_obj.cloud_name, domain_id=domain_obj.domain_id,
                                        access_id=account_obj.access_id,
                                        access_key=mc.my_decrypt(account_obj.access_key), domain_name=domain_name)
                result_data = yield self.domain_put(domain, **base_new_dict)

            except Exception as err:
                log_data = dict(domain_name=domain_name, username=self.request_nickname, action="API",
                                record=f'账号别名：{account_obj.name}， 错误信息：{err}', state="失败")
                session.add(DomainOptLog(**log_data))
                return self.write(dict(code=-1, msg='修改失败，详情请看日志'))

            if result_data:
                log_state = "成功"
                session.query(DomainRecords).filter(DomainRecords.id == int(the_id)).update(
                    {'record_id': record_obj.record_id, 'domain_rr': data.get('domain_rr'), 'line': data.get('line'),
                     'domain_type': data.get('domain_type'), 'domain_value': data.get('domain_value'),
                     'domain_ttl': data.get('domain_ttl'), 'weight': data.get('weight'),
                     'domain_mx': int(data.get('domain_mx', 0))})
            else:
                log_state = "失败"
                ### 记录变更日志
            log_data = dict(
                domain_name=record_obj.domain_name,
                username=self.request_nickname,
                action="修改后",
                record=f"类型：{data.get('domain_type')}， {record_obj.domain_rr}， 线路：{data.get('line')}， 记录：{data.get('domain_value')}， (TTL：{data.get('domain_ttl')}) (weight：{data.get('weight')})",
                state=log_state
            )
            session.add(DomainOptLog(**log_data))
            if not result_data: return self.write(dict(code=-2, msg='修改失败，详情请看日志'))

        return self.write(dict(code=0, msg='修改完成'))

    @run_on_executor(executor='_thread_pool')
    def domain_patch(self, domain, **base_new_dict):
        return domain.set_record_status(**base_new_dict)

    @gen.coroutine
    def patch(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        if data.get('action') == 'disable':
            action = "禁用"
        elif data.get('action') == 'enable':
            action = "启用"
        else:
            action = "参数有误"
        select_list = data.get('id_list')

        with DBContext('r') as session:
            select_record = session.query(DomainRecords).filter(DomainRecords.id.in_(select_list)).all()
            if select_record and len(select_record) > 0:
                record_obj = select_record[0]
                domain_name = record_obj.domain_name
                account_obj = session.query(CloudSettingModels).filter(
                    CloudSettingModels.account_id == record_obj.account).first()
                domain_obj = session.query(DomainName).filter(DomainName.domain_name == domain_name).first()
            else:
                return self.write(dict(code=-1, msg='参数有误'))

        if account_obj.cloud_name in ['GoDaddy', 'godaddy']:
            return self.write(dict(code=3, msg='GoDaddy 接口有BUG，暂时不支持禁用/启用'))

        domain_name = record_obj.domain_name
        domain = domain_factory(account_obj.cloud_name, domain_name=domain_name, domain_id=domain_obj.domain_id,
                                access_id=account_obj.access_id, access_key=mc.my_decrypt(account_obj.access_key))
        with DBContext('w', None, True) as session:
            for r in select_record:
                ###
                base_new_dict = dict(
                    domain_name=domain_name,
                    record_id=r.record_id,
                    status=action,
                    ###
                    domain_rr=r.domain_rr,
                    domain_type=r.domain_type,
                    domain_value=r.domain_value,
                    domain_ttl=int(r.domain_ttl),
                    domain_mx=int(r.domain_mx),
                    line=r.line,
                )
                try:
                    result_data = yield self.domain_patch(domain, **base_new_dict)

                except Exception as err:
                    log_data = dict(
                        domain_name=domain_name,
                        username=self.request_username,
                        action="API",
                        record=f'账号别名：{account_obj.name}， 错误信息：{err}',
                        state="失败"
                    )
                    session.add(DomainOptLog(**log_data))
                    return self.write(dict(code=-1, msg='{}，详情请看日志'.format(action)))
                ###

                ### 记录修改
                if result_data:
                    log_state = "成功"
                    session.query(DomainRecords).filter(DomainRecords.id == int(r.id)).update(
                        {DomainRecords.state: data.get('action')})
                else:
                    log_state = "失败"

                log_data = dict(
                    domain_name=domain_name,
                    username=self.request_username,
                    action=action,
                    record='记录：{}，值：{}，线路：{}，{}'.format(r.domain_rr, r.domain_value, r.line, action),
                    state=log_state
                )
                session.add(DomainOptLog(**log_data))

                if not result_data: return self.write(dict(code=-2, msg='{}，详情请看日志'.format(action)))
        return self.write(dict(code=0, msg=f'{action}完成'))

    @run_on_executor(executor='_thread_pool')
    def domain_delete(self, domain, **base_new_dict):
        return domain.del_record(**base_new_dict)

    @gen.coroutine
    def delete(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        select_list = data.get('id_list')
        if not select_list: return self.write(dict(code=1, msg='关键参数不能为空'))

        with DBContext('r') as session:
            select_record = session.query(DomainRecords).filter(DomainRecords.id.in_(select_list)).all()
            if select_record and len(select_record) > 0:
                record_obj = select_record[0]
                domain_name = record_obj.domain_name
                account_obj = session.query(CloudSettingModels).filter(
                    CloudSettingModels.account_id == record_obj.account).first()
                domain_obj = session.query(DomainName).filter(DomainName.domain_name == domain_name).first()
            else:
                return self.write(dict(code=-1, msg='参数有误'))

        if account_obj.cloud_name in ['GoDaddy', 'godaddy']:
            return self.write(dict(code=3, msg='GoDaddy 接口有BUG，暂时不支持删除'))

        domain = domain_factory(account_obj.cloud_name, domain_id=domain_obj.domain_id, domain_name=domain_name,
                                access_id=account_obj.access_id, access_key=mc.my_decrypt(account_obj.access_key))

        with DBContext('w', None, True) as session:
            for r in select_record:
                try:
                    del_dict = dict(domain_name=domain_name, record_id=r.record_id, domain_rr=r.domain_rr,
                                    domain_type=r.domain_type)
                    result_data = yield self.domain_delete(domain, **del_dict)
                except Exception as err:
                    log_data = dict(domain_name=domain_name, username=self.request_username,
                                    action="API", record=f'账号别名：{account_obj.name}，错误信息：{err}', state="失败")
                    session.add(DomainOptLog(**log_data))
                    return self.write(dict(code=-1, msg=f'删除失败，详情请看日志 {err}'))

                if result_data:
                    session.query(DomainRecords).filter(DomainRecords.id == int(r.id)).delete(synchronize_session=False)

                log_data = dict(domain_name=domain_name, username=self.request_username, action='删除',
                                record='记录：{}，值：{}，线路：{}'.format(r.domain_rr, r.domain_value, r.line),
                                state='成功')
                session.add(DomainOptLog(**log_data))
                if not result_data: return self.write(dict(code=-2, msg='删除失败，详情请看日志'))

        self.write(dict(code=0, msg='删除成功'))


class DomainOptLogHandler(BaseHandler, ABC):
    def get(self, *args, **kwargs):
        res = get_domain_opt_log(**self.params)
        self.write(res)


class RecordRemarkHandler(BaseHandler, ABC):
    _thread_pool = ThreadPoolExecutor(5)

    @run_on_executor(executor='_thread_pool')
    def record_remark_post(self, domain, **base_new_dict):
        return domain.remark(**base_new_dict)

    @gen.coroutine
    def post(self, *args, **kwargs):
        data = json.loads(self.request.body.decode("utf-8"))
        the_id = data.get('id')
        remark = data.get('remark')
        if not the_id or not remark:  self.write(dict(code=0, msg='关键参数域名不能为空'))

        with DBContext('w', None, True) as session:

            record_obj = session.query(DomainRecords).filter(DomainRecords.id == int(the_id)).first()
            account_obj = session.query(CloudSettingModels).filter(
                CloudSettingModels.account_id == record_obj.account).first()
            session.query(DomainRecords).filter(DomainRecords.id == int(the_id)).update({'remark': remark})
            domain_name = record_obj.domain_name
            # 开始调用api
            if account_obj.cloud_name in ['阿里云', 'aliyun', 'qcloud', 'dnspod']:
                domain_obj = session.query(DomainName).filter(DomainName.domain_name == domain_name).first()
                try:
                    domain = domain_factory(account_obj.cloud_name, domain_name=domain_name,
                                            domain_id=domain_obj.domain_id, access_id=account_obj.access_id,
                                            access_key=mc.my_decrypt(account_obj.access_key))

                    base_new_dict = dict(domain_name=domain_name, record_id=record_obj.record_id, remark=remark)
                    result_data = yield self.record_remark_post(domain, **base_new_dict)

                except Exception as err:
                    log_data = dict(domain_name=domain_name, username=self.request_nickname, action="API",
                                    record=f'账号别名：{account_obj.name}， 错误信息：{err}', state="失败")
                    session.add(DomainOptLog(**log_data))
                    return self.write(dict(code=-1, msg='删除失败，详情请看日志'))
            # 录入日志
            log_data = dict(domain_name=domain_name, username=self.request_nickname, action='变更备注', state="成功",
                            record=f'类型：{record_obj.domain_type}，{record_obj.domain_rr}：，记录：{record_obj.domain_value}，线路：{record_obj.line}，备注变更：{record_obj.remark} > {remark}')

            session.add(DomainOptLog(**log_data))

        self.write(dict(code=0, msg='修改成功'))


class DomainInfoSync(BaseHandler, ABC):
    _thread_pool = ThreadPoolExecutor(5)

    @run_on_executor(executor='_thread_pool')
    def domain_sync(self):
        domain_main('aliyun')
        # domain_main('qcloud')
        domain_main('dnspod')
        domain_main('GoDaddy')
        return dict(code=0, msg='更新完毕')

    async def post(self, *args, **kwargs):
        res = await self.domain_sync()
        return self.write(res)


cloud_domain_urls = [
    (r"/api/v2/cmdb/dns/domain/", CloudDomainHandler),
    (r"/api/v2/cmdb/dns/record/", CloudRecordHandler),
    (r"/api/v2/cmdb/dns/logs/", DomainOptLogHandler),
    (r"/api/v2/cmdb/dns/sync/", DomainInfoSync),
    (r"/api/v2/cmdb/dns/remark/", RecordRemarkHandler)
]
