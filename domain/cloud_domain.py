#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2019年5月7日
Desc    : 云解析DNS记录
"""

import time
import datetime
import logging
from typing import *
from shortuuid import uuid
from concurrent.futures import ThreadPoolExecutor
from websdk2.configs import configs
from websdk2.model_utils import queryset_to_list, insert_or_update
from websdk2.db_context import DBContext
from sqlalchemy import event

from models.domain import DomainOptLog
from models.domain import DomainName, DomainRecords, DomainSyncLog
from models.cloud import CloudSettingModels
from websdk2.tools import RedisLock
from libs.domain.qcloud_domain import QCloud
# from libs.domain.dnspod_domain import DNSPod
from libs.domain.godaddy_domain import GoDaddy
from libs.domain.aliyun_domain import AliYun
from libs.kafka_utils import KafkaProducer

from settings import settings

if configs.can_import: configs.import_dict(**settings)
from libs.mycrypt import mc


def deco(cls, release=False):
    def _deco(func):
        def __deco(*args, **kwargs):
            if not cls.get_lock(cls, key_timeout=120, func_timeout=30): return False
            try:
                return func(*args, **kwargs)
            finally:
                # 执行完就释放key，默认不释放
                if release: cls.release(cls)

        return __deco

    return _deco


def domain_factory(cloud, **kwargs):
    if cloud in ['阿里云', 'aliyun', 'AliYun']:
        return AliYun(**kwargs)

    elif cloud in ['腾讯云', 'qcloud', 'QCloud', 'DNSPod', 'dnspod']:
        return QCloud(**kwargs)

    # elif cloud in ['DNSPod', 'dnspod']:
    #     return DNSPod(**kwargs)

    elif cloud in ['GoDaddy', 'godaddy']:
        return GoDaddy(**kwargs)
    else:
        return None


def all_domain_sync_index():
    @deco(RedisLock("all_domain_sync_redis_lock_key"))
    def index():
        logging.info(f'开始同步域名信息')
        domain_main('aliyun')
        domain_main('qcloud')
        domain_main('dnspod')
        domain_main('godaddy')

    index()


def domain_main(cloud_name):
    with DBContext('r') as session:
        config_info = session.query(CloudSettingModels).filter(CloudSettingModels.cloud_name == cloud_name,
                                                               CloudSettingModels.is_enable == True).all()
        the_configs = queryset_to_list(config_info)

    if not the_configs:
        logging.warning(f'{cloud_name} 云配置未开启')
        return

    for config in the_configs:
        name, account_id = config.get('name'), config.get('account_id')
        config['access_key'] = mc.my_decrypt(config['access_key'])
        # 十天没有更新则改状态为过期 过期十天则删除
        old_date = datetime.datetime.now() - datetime.timedelta(days=10)
        old_date1 = datetime.datetime.now() - datetime.timedelta(hours=2)
        start_time = time.time()
        with DBContext('w', None, True) as session:
            if cloud_name in ['GoDaddy', 'godaddy']:
                session.query(DomainName).filter(DomainName.account == account_id, DomainName.domain_state != 'disable',
                                                 DomainName.update_time < old_date).update(
                    {DomainName.domain_state: "过期"})
                session.query(DomainName).filter(DomainName.account == account_id, DomainName.domain_state != 'disable',
                                                 DomainName.update_time < old_date1).update(
                    {DomainName.domain_state: "未知"})
            else:
                session.query(DomainName).filter(DomainName.account == account_id,
                                                 DomainName.update_time < old_date).update(
                    {DomainName.domain_state: "过期"})
                session.query(DomainName).filter(DomainName.account == account_id,
                                                 DomainName.update_time < old_date1).update(
                    {DomainName.domain_state: "未知"})

            session.query(DomainName).filter(DomainName.account == account_id, DomainName.domain_state == "过期",
                                             DomainName.update_time < old_date).delete(synchronize_session=False)
            ###
            session.add(DomainSyncLog(present='{} DNS'.format(cloud_name), alias_name=name,
                                      access_id=account_id, state="正常", record='开始同步'))

        obj = domain_factory(cloud_name, **config)
        try:
            domain_list = obj.describe_domains()
            if not domain_list: return
            for domain in domain_list:
                # print(domain, cloud_name, account_id, domain)
                data_sync_domain(cloud_name, account_id, domain)
                if isinstance(domain, dict):
                    record_list = obj.record_generator(**domain)
                else:
                    record_list = obj.record_generator(domain)
                data_sync_record(cloud_name, account_id, record_list)

        except Exception as err:
            with DBContext('w', None, True) as session:
                session.add(DomainSyncLog(present=f'{cloud_name} DNS', alias_name=name,
                                          access_id=account_id, state="错误", record=str(err)))

        with DBContext('w', None, True) as session:
            duration = time.time() - start_time
            session.add(DomainSyncLog(present=f'{cloud_name} DNS', alias_name=name,
                                      access_id=account_id, state="正常", record='同步结束，耗时： %.3f s' % duration))


def data_sync_domain(cloud_name, account_id, domain):
    with DBContext('w', None, True) as session:
        if cloud_name in ['阿里云', 'aliyun', 'AliYun']:
            domain_name = domain.get('DomainName')
            domain_id = domain.get('DomainId')
            is_exist = session.query(DomainName).filter(DomainName.domain_name == domain_name).first()
            state = '过期' if domain.get('InstanceExpired', False) else '正常'
            if is_exist:
                session.query(DomainName).filter(DomainName.domain_name == domain_name).update(
                    {DomainName.domain_id: domain_id, DomainName.record_count: domain.get('RecordCount'),
                     DomainName.domain_state: state, DomainName.account: account_id,
                     DomainName.cloud_name: cloud_name})
            else:
                new_domain = DomainName(domain_name=domain_name, domain_id=domain_id,
                                        record_count=int(domain.get('RecordCount')), domain_state=state,
                                        account=account_id, cloud_name=cloud_name, version=domain.get('VersionName'))
                session.add(new_domain)
        elif cloud_name in ['腾讯云', 'qcloud', 'QCloud', 'dnspod', 'DNSPod']:
            # 腾讯云  DNSPod 合并
            domain_name, domain_id, record_count = domain.Name, domain.DomainId, domain.RecordCount
            state = '正常' if domain.Status == 'ENABLE' else '未知'

            try:
                session.add(insert_or_update(DomainName, f"domain_name='{domain_name}'",
                                             domain_name=domain_name, domain_id=domain_id,
                                             record_count=int(record_count), domain_state=state,
                                             account=account_id, cloud_name=cloud_name,
                                             version=domain.GradeTitle
                                             ))

            except Exception as err:
                logging.error(f'{cloud_name} 更新域名出错 {err}')
            # insert_or_update
            # if session.query(DomainName).filter(DomainName.domain_name == domain_name).first():
            #     session.query(DomainName).filter(DomainName.domain_name == domain_name).update(
            #         {DomainName.domain_id: domain_id, DomainName.record_count: record_count,
            #          DomainName.domain_state: state, DomainName.account: account_id,
            #          DomainName.cloud_name: cloud_name})
            # else:
            #     session.add(DomainName(domain_name=domain_name, domain_id=domain_id,
            #                            record_count=record_count, domain_state=state,
            #                            account=account_id, cloud_name=cloud_name))

        # elif cloud_name in ['dnspod', 'DNSPod']:
        #     domain_id, domain_name = domain.get('id'), domain.get('name')
        #
        #     if domain.get('ext_status') == 'notexist':
        #         state = '未注册'
        #     elif domain.get('ext_status') == 'dnserror':
        #         state = '错误'
        #     elif domain.get('ext_status') == '':
        #         state = '正常'
        #     else:
        #         state = '未知'
        #
        #     if session.query(DomainName).filter(DomainName.domain_name == domain_name).first():
        #         session.query(DomainName).filter(DomainName.domain_name == domain_name).update(
        #             {DomainName.domain_id: domain_id, DomainName.record_count: domain.get('records'),
        #              DomainName.domain_state: state, DomainName.account: account_id,
        #              DomainName.cloud_name: cloud_name})
        #     else:
        #         new_domain = DomainName(domain_name=domain_name, domain_id=domain_id,
        #                                 record_count=domain.get('records'), domain_state=state,
        #                                 account=account_id, cloud_name=cloud_name)
        #         session.add(new_domain)

        elif cloud_name == "GoDaddy":
            domain_name = domain.get('domain')
            domain_id = domain.get('domainId')
            record_count = int(domain.get('records', 0))

            state = '正常' if domain.get('status') in ['ACTIVE', 'OK'] else '错误'

            if session.query(DomainName).filter(DomainName.domain_name == domain_name).first():
                session.query(DomainName).filter(DomainName.domain_name == domain_name).update(
                    {DomainName.domain_id: domain_id, DomainName.record_count: record_count,
                     DomainName.domain_state: state, DomainName.account: account_id,
                     DomainName.cloud_name: cloud_name})
            else:
                new_domain = DomainName(domain_name=domain_name, domain_id=domain_id,
                                        record_count=record_count, domain_state=state,
                                        account=account_id, cloud_name=cloud_name)
                session.add(new_domain)
        else:
            pass


def data_sync_record(cloud_name, account_id, record_list):
    with DBContext('w', None, True) as session:
        for record_info in record_list:
            domain_name = record_info.get('domain_name')
            record = record_info.get('data_dict')
            if cloud_name in ['阿里云', 'aliyun', 'AliYun']:
                try:
                    record_id = record.get('RecordId')
                    session.add(
                        insert_or_update(DomainRecords, f"domain_name='{domain_name}' and record_id='{record_id}'",
                                         domain_name=domain_name,
                                         record_id=record_id,
                                         domain_rr=record.get('RR', ''),
                                         domain_type=record.get('Type', ''),
                                         domain_value=record.get('Value', ''),
                                         domain_ttl=int(record.get('TTL', 600)),
                                         domain_mx=int(record.get('Weight', 0)),
                                         line=record.get('Line', 'unknown'),
                                         state=record.get('Status', 'unknown'),
                                         remark=record.get('Remark', 'unknown'),
                                         account=account_id))
                    # session.commit()
                except Exception as err:
                    logging.info(f'{cloud_name} 更新域名记录出错 {err}')

            elif cloud_name in ['腾讯云', 'qcloud', 'QCloud', 'dnspod', 'DNSPod']:
                record_id = str(record.RecordId)
                state = 'DISABLE' if record.Status == 'DISABLE' else 'ENABLE'
                try:
                    session.add(
                        insert_or_update(DomainRecords, f"domain_name='{domain_name}' and record_id='{record_id}'",
                                         domain_name=domain_name, record_id=record_id,
                                         domain_rr=record.Name,
                                         domain_type=record.Type,
                                         domain_value=record.Value,
                                         domain_ttl=record.TTL,
                                         domain_mx=record.MX,
                                         line=record.Line,
                                         weight=record.Weight,
                                         state=state,
                                         remark=record.Remark,
                                         account=account_id
                                         ))
                    # session.commit()
                except Exception as err:
                    logging.error(f'{cloud_name} 更新域名记录出错 {err}')

            elif cloud_name == 'GoDaddy':
                record_ex = session.query(DomainRecords).filter(DomainRecords.domain_rr == record.get('name'),
                                                                DomainRecords.domain_type == record.get('type'),
                                                                DomainRecords.domain_value == record.get('data'),
                                                                DomainRecords.account == account_id,
                                                                DomainRecords.domain_name == domain_name).first()

                if record_ex:
                    session.query(DomainRecords).filter(DomainRecords.domain_rr == record.get('name'),
                                                        DomainRecords.domain_type == record.get('type'),
                                                        DomainRecords.domain_value == record.get('data'),
                                                        DomainRecords.account == account_id,
                                                        DomainRecords.domain_name == domain_name).update(
                        {
                            DomainRecords.domain_rr: record.get('name', ''),
                            DomainRecords.domain_type: record.get('type', ''),
                            DomainRecords.domain_value: record.get('data', ''),
                            DomainRecords.domain_ttl: int(record.get('ttl', 600)),
                            DomainRecords.domain_mx: record.get('mx', 0),
                            DomainRecords.line: record.get('line', 'default'),
                            DomainRecords.state: record.get('status', 'ENABLE'),
                            DomainRecords.account: account_id})
                else:
                    new_record = DomainRecords(domain_name=domain_name,
                                               record_id=str(uuid()),
                                               domain_rr=record.get('name', ''),
                                               domain_type=record.get('type', ''),
                                               domain_value=record.get('data', ''),
                                               domain_ttl=int(record.get('ttl', 600)),
                                               domain_mx=int(record.get('mx', 0)),
                                               line=record.get('line', 'default'),
                                               state=record.get('status', 'ENABLE'),
                                               account=account_id)
                    session.add(new_record)
            ##
            mark_expired(DomainRecords, domain_name=domain_name, record_id=record_id)


def mark_expired(resource_model, domain_name: Optional[str], record_id: Optional[str]):
    """
    根据时间标记过期的数据
    """
    with DBContext('w', None, True, **settings) as session:
        # 2小时
        _hours_ago = datetime.datetime.now() - datetime.timedelta(hours=2)
        # 过期
        session.query(resource_model).filter(
            resource_model.domain_name == domain_name, record_id == record_id, resource_model.state != '过期',
            resource_model.update_time <= _hours_ago).update({resource_model.state: '过期'})

        records_to_delete = session.query(resource_model).filter(
            resource_model.domain_name == domain_name, record_id == record_id,
            resource_model.state == '过期', resource_model.update_time <= _hours_ago).all()

        for r in records_to_delete:
            logging.warning(
                f'删除{domain_name} 记录ID：{record_id} 记录：{r.domain_rr}，值：{r.domain_value}，类型：{r.domain_type}')
            session.delete(r)
        # session.query(resource_model).filter(resource_model.domain_name == domain_name, record_id == record_id,
        #                                      resource_model.state == '过期',
        #                                      resource_model.update_time <= _hours_ago).delete(
        #     synchronize_session=False)


def async_domain_info():
    executor = ThreadPoolExecutor(max_workers=1)
    executor.submit(all_domain_sync_index)


@event.listens_for(DomainOptLog, "after_insert")
def after_opt_log_insert(mapper, connection, target):
    """发送操作日志到安全soc"""
    try:
        message = {
            "domain_name": target.domain_name,
            "username": target.username,
            "action": target.action,
            "record": target.record,
            "state": target.state,
            "update_time": target.update_time.strftime("%Y-%m-%d %H:%M:%S"),
            "id": target.id
        }
        producer = KafkaProducer()
        producer.send(message)
        logging.info(f"发送操作日志到Kafka成功: {message}")
    except Exception as e:
        logging.error(f"发送操作日志到Kafka失败: {e}")


if __name__ == '__main__':
    pass