#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/4/8 17:56
Desc    : consul 注册
"""

import datetime
import json
import logging
import consul
import requests
from settings import settings
from concurrent.futures import ThreadPoolExecutor
from websdk2.consts import const
from websdk2.tools import RedisLock, convert
from websdk2.configs import configs
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.model_utils import model_to_dict
from websdk2.cache_context import cache_conn
from models.tree import TreeAssetModels
from models import asset_mapping

if configs.can_import: configs.import_dict(**settings)


def deco(cls, release=False):
    def _deco(func):
        def __deco(*args, **kwargs):
            if not cls.get_lock(cls, key_timeout=120, func_timeout=90): return False
            try:
                return func(*args, **kwargs)
            finally:
                # 执行完就释放key，默认不释放
                if release: cls.release(cls)

        return __deco

    return _deco


def sync_consul():
    @deco(RedisLock("async_asset_to_consul_lock_key"))
    def index():
        logging.info(f'同步数据到consul开始 ！！！')
        c = ConsulOpt()
        server_info = c.get_services()
        if server_info.get('code') != 0:
            logging.error(f'访问consul失败 ！！！ {server_info.get("msg")}')
            return
        for asset_type in ['server', 'mysql', 'redis', 'domain']:
            try:
                cmdb_ins = []
                for server in consul_sync_factory(asset_type):
                    cmdb_ins.append(server[1])
                    c.register_service(*server)

                for ins in c.get_instances(f'{asset_type}-exporter').get('data'):
                    if ins.get('ServiceID') not in cmdb_ins:
                        c.deregister_service(ins.get('ServiceID'))
            except Exception as err:
                logging.error(f'sync to consul {asset_type} error,{err} {datetime.datetime.now()}')

        logging.info(f'同步数据到consul结束 ！！！')

    index()


def consul_sync_factory(asset_type):
    if asset_type == 'server':
        return get_registry_server_info()

    elif asset_type == 'mysql':
        return get_registry_mysql_info()

    elif asset_type == 'redis':
        return get_registry_redis_info()

    elif asset_type == 'domain':
        return get_registry_domain_info()
    else:
        return None


class ConsulOpt(object):
    def __init__(self, consul_host=None, consul_port=None, token=None, scheme="http"):
        """初始化，连接consul服务器"""
        if not consul_host:
            consul_info = configs.get(const.CONSUL_CONFIG_ITEM).get(const.DEFAULT_CS_KEY)
            consul_host = consul_info.get(const.CONSUL_HOST_KEY)
            consul_port = consul_info.get(const.CONSUL_PORT_KEY)
            token = consul_info.get(const.CONSUL_TOKEN_KEY)
            scheme = consul_info.get(const.CONSUL_SCHEME_KEY)

        self.consul_api_url = f"{scheme}://{consul_host}:{consul_port}"
        self.headers = {'X-Consul-Token': token}

        self._consul = consul.Consul(host=consul_host, port=consul_port, token=token, scheme=scheme, timeout=15)

    def register_service(self, name, service_id, host, port, tags, meta, check=None):
        tags = tags or []
        # 注册服务
        self._consul.agent.service.register(
            name,
            service_id=service_id,
            address=host,
            port=port,
            tags=tags,
            meta=meta,
            check=check
        )
        # 健康检查ip端口，检查时间：5,超时时间：30，注销时间：300s
        # check = consul.Check().tcp(host, port, "5s", "30s", "300s")

    def deregister_service(self, service_id):
        self._consul.agent.service.deregister(service_id=service_id)

    def deregister_service_batch(self, id_list: list) -> dict:
        try:
            for service_id in id_list:
                self._consul.agent.service.deregister(service_id=service_id)
            return dict(code=0, msg=f'删除完成')
        except Exception as err:
            return dict(code=-1, msg=f'删除失败 {err}')

    def get_services(self) -> dict:
        url = f'{self.consul_api_url}/v1/internal/ui/services'
        res = requests.get(url, headers=self.headers, timeout=5)
        if res.status_code == 200:
            info = res.json()
            services_list = [
                {'name': i['Name'], 'data_center': i.get('Datacenter'), 'count': i['InstanceCount'],
                 'checks_critical': i['ChecksCritical'], 'checks_passing': i['ChecksPassing'], 'tags': i['Tags'],
                 'nodes': list(set(i['Nodes']))} for i in info if i['Name'] != 'consul']
            return {'code': 0, 'msg': '成功', 'data': services_list}
        else:
            return {'code': -1, 'msg': f'{res.status_code}:{res.text}'}

    def get_service(self, service_id) -> dict:

        services = self._consul.agent.services()
        service = services.get(service_id)

        if not service:
            return dict()

        return service

    def get_instances(self, service) -> dict:
        instances = self._consul.catalog.service(service)[1]
        if not instances:
            return dict(code=0, msg='当前实例为空', data=[], count=0)
        return {'code': 0, 'msg': '成功', 'data': instances, 'count': len(instances)}


def get_registry_server_info():
    redis_conn = cache_conn()
    asset_type = 'server'
    port = 9100
    __model = asset_mapping[asset_type]
    with DBContext('r') as session:
        __info = session.query(TreeAssetModels, __model.instance_id, __model.name,
                               __model.inner_ip).outerjoin(__model, __model.id == TreeAssetModels.asset_id).filter(
            TreeAssetModels.asset_type == asset_type).all()

    biz_info_str = redis_conn.get("BIZ_INFO_STR")
    biz_info_map = convert(biz_info_str) if biz_info_str else {}
    if isinstance(biz_info_map, str): biz_info_map = json.loads(biz_info_map)
    for i in __info:
        data = model_to_dict(i[0])
        if not i[3]:
            continue
        inner_ip = i[3]
        biz_id = data['biz_id']
        node_meta = dict(biz_id=biz_id, biz_cn_name=biz_info_map.get(biz_id, biz_id), env_name=data['env_name'],
                         region_name=data['region_name'], module_name=data['module_name'])
        server_name = f"{asset_type}-exporter"
        register_data = (server_name, f"{server_name}-{biz_id}-{inner_ip}-{port}", inner_ip, port,
                         [data['biz_id']], node_meta)
        yield register_data


def get_items_ip(db_address, port) -> tuple:
    addr_list = db_address['items']
    inner_ip, port = '', port
    for addr in addr_list:
        if addr.get('type') == 'private':
            return addr.get('ip'), addr.get('port')
        inner_ip, port = addr.get('ip'), addr.get('port')

    return inner_ip, port


def get_registry_mysql_info():
    redis_conn = cache_conn()
    asset_type = 'mysql'
    __model = asset_mapping[asset_type]
    with DBContext('r') as session:
        __info = session.query(TreeAssetModels, __model.instance_id, __model.name,
                               __model.db_address).outerjoin(__model, __model.id == TreeAssetModels.asset_id).filter(
            TreeAssetModels.asset_type == asset_type).all()

    biz_info_str = redis_conn.get("BIZ_INFO_STR")
    biz_info_map = convert(biz_info_str) if biz_info_str else {}
    if isinstance(biz_info_map, str): biz_info_map = json.loads(biz_info_map)

    for i in __info:
        data = model_to_dict(i[0])
        biz_id = data['biz_id']
        if not i[3]:
            continue
        inner_ip, port = get_items_ip(i[3], 3306)

        node_meta = dict(biz_id=biz_id, biz_cn_name=biz_info_map.get(biz_id, biz_id), env_name=data['env_name'],
                         region_name=data['region_name'], module_name=data['module_name'])
        server_name = f"{asset_type}-exporter"
        register_data = (server_name, f"{server_name}-{biz_id}-{inner_ip}-{port}", inner_ip, port, [biz_id], node_meta)
        yield register_data


def get_registry_redis_info():
    redis_conn = cache_conn()
    asset_type = 'redis'
    __model = asset_mapping[asset_type]
    with DBContext('r') as session:
        __info = session.query(TreeAssetModels, __model.instance_id, __model.name,
                               __model.instance_address).outerjoin(__model,
                                                                   __model.id == TreeAssetModels.asset_id).filter(
            TreeAssetModels.asset_type == asset_type).all()

    biz_info_str = redis_conn.get("BIZ_INFO_STR")
    biz_info_map = convert(biz_info_str) if biz_info_str else {}
    if isinstance(biz_info_map, str): biz_info_map = json.loads(biz_info_map)

    for i in __info:
        data = model_to_dict(i[0])
        biz_id = data['biz_id']
        if not i[3]:
            logging.error(f"{asset_type} {data} {i[1]} {i[2]} err")
            continue
        inner_ip, port = get_items_ip(i[3], 6379)
        node_meta = dict(biz_id=biz_id, biz_cn_name=biz_info_map.get(biz_id, biz_id), env_name=data['env_name'],
                         region_name=data['region_name'], module_name=data['module_name'])
        server_name = f"{asset_type}-exporter"
        register_data = (server_name, f"{server_name}-{biz_id}-{inner_ip}-{port}", inner_ip, port, [biz_id], node_meta)
        yield register_data


def get_registry_domain_info():
    # 暂时没有和服务树关联
    redis_conn = cache_conn()
    asset_type = 'domain'
    __model = asset_mapping[asset_type]
    with DBContext('r') as session:
        __info = session.query(__model).all()

    biz_info_str = redis_conn.get("BIZ_INFO_STR")
    biz_info_map = convert(biz_info_str) if biz_info_str else {}
    if isinstance(biz_info_map, str):
        biz_info_map = json.loads(biz_info_map)

    for i in __info:
        data = model_to_dict(i)
        biz_id = "504"
        inner_ip, port = f"{data.get('domain_rr')}.{data.get('domain_name')}", 443
        node_meta = dict(biz_id=biz_id, biz_cn_name=biz_info_map.get(biz_id, biz_id), env_name='prod',
                         domain_type=data.get('domain_type'))
        server_name = f"{asset_type}-exporter"
        register_data = (
            server_name, f"{server_name}-{biz_id}-{data.get('record_id')}-{inner_ip}", inner_ip, port, [biz_id],
            node_meta)
        yield register_data


def async_consul_info():
    executor = ThreadPoolExecutor(max_workers=1)
    executor.submit(sync_consul)


if __name__ == '__main__':
    pass
