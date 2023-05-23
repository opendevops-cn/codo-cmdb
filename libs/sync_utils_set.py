#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/2/8 17:56
Desc    : 同步数据专用
"""

import json
import datetime
from concurrent.futures import ThreadPoolExecutor
from settings import settings
from websdk2.web_logs import ins_log
from websdk2.tools import RedisLock
from websdk2.configs import configs
from websdk2.cache_context import cache_conn
##
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.model_utils import insert_or_update
from websdk2.client import AcsClient
from models.business import BizModels
from models.asset import AssetServerModels

# from websdk2.api_set import api_set

if configs.can_import: configs.import_dict(**settings)

# 实例化client
client = AcsClient()


def deco(cls, release=False):
    def _deco(func):
        def __deco(*args, **kwargs):
            if not cls.get_lock(cls, key_timeout=300, func_timeout=90): return False
            try:
                return func(*args, **kwargs)
            finally:
                # 执行完就释放key，默认不释放
                if release: cls.release(cls)

        return __deco

    return _deco


def biz_sync():
    @deco(RedisLock("async_biz_to_cmdb_redis_lock_key"))
    def index():
        ins_log.read_log('info', f'sync biz to cmdb start  {datetime.datetime.now()}')
        get_mg_biz = dict(method='GET', url=f'/api/mg/v1/base/biz/', description='获取租户数据')
        try:
            response = client.do_action(**get_mg_biz)
            all_biz_list = json.loads(response).get('all_data')
            biz_info_map = {}
            for biz in all_biz_list:
                biz_id = str(biz.get('business_id'))
                biz_info_map[biz_id] = biz.get('business_zh', biz.get('business_en'))
                with DBContext('w', None, True) as session:
                    try:
                        session.add(insert_or_update(BizModels, f"biz_id='{biz_id}'",
                                                     biz_id=biz_id,
                                                     biz_en_name=biz.get('business_en'),
                                                     biz_cn_name=biz.get('business_zh'),
                                                     resource_group=biz.get('resource_group'),
                                                     sort=biz.get('sort'),
                                                     life_cycle=biz.get('life_cycle'),
                                                     corporate=biz.get('corporate')))

                    except Exception as err:
                        ins_log.read_log('info', f'async_biz_to_cmdb 1 {err}')

            biz_info_map = json.dumps(biz_info_map)
            redis_conn = cache_conn()
            redis_conn.set("BIZ_INFO_STR", biz_info_map)

        except Exception as err:
            ins_log.read_log('info', f'async_biz_to_cmdb 2  {err}')
        ins_log.read_log('info', f'sync biz to cmdb end {datetime.datetime.now()}')

    index()


def sync_agent_status():
    @deco(RedisLock("async_agent_status_redis_lock_key"))
    def index():
        ins_log.read_log('info', f'sync agent status start {datetime.datetime.now()}')
        get_agent_list = dict(method='GET', url=f'/api/agent/v1/codo/agent_list',
                              description='获取Agent List')
        res = client.do_action_v2(**get_agent_list)
        if res.status_code != 200: return
        data = res.json()
        agent_list = data.get('list')
        with DBContext('w', None, True) as session:
            __info = session.query(AssetServerModels.id, AssetServerModels.agent_id,
                                   AssetServerModels.agent_status).all()

        all_info = []
        for asset_id, agent_id, agent_status, in __info:
            if agent_status == '1' and agent_id not in agent_list:  # 如果状态在线  但是agent找不到
                # ins_log.read_log('info', f'{agent_id}改为离线')
                all_info.append(dict(id=asset_id, agent_status='2'))
            if agent_status == '2' and agent_id in agent_list:  # 如果状态离线  但是agent存在
                all_info.append(dict(id=asset_id, agent_status='1'))
            if not agent_status and agent_id in agent_list:
                all_info.append(dict(id=asset_id, agent_status='1'))
        session.bulk_update_mappings(AssetServerModels, all_info)
        ins_log.read_log('info', f'sync agent status end {datetime.datetime.now()}')

    try:
        index()
    except Exception as err:
        ins_log.read_log('error', f'sync agent status error {str(err)}')


def async_agent():
    executor = ThreadPoolExecutor(max_workers=1)
    executor.submit(sync_agent_status)


def async_biz_info():
    executor = ThreadPoolExecutor(max_workers=1)
    executor.submit(biz_sync)
