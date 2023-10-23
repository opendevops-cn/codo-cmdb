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
import logging
from concurrent.futures import ThreadPoolExecutor
from settings import settings
from loguru import logger
from websdk2.tools import RedisLock
from websdk2.configs import configs
from websdk2.cache_context import cache_conn
##
from websdk2.db_context import DBContextV2 as DBContext
from websdk2.model_utils import insert_or_update
from websdk2.client import AcsClient
from models.business import BizModels
from models.asset import AssetServerModels

if configs.can_import: configs.import_dict(**settings)

# 实例化client
client = AcsClient()


def deco(cls, release=False, **kw):
    def _deco(func):
        def __deco(*args, **kwargs):
            key_timeout, func_timeout = kw.get("key_timeout", 300), kw.get("func_timeout", 90)
            if not cls.get_lock(cls, key_timeout=key_timeout, func_timeout=func_timeout): return False
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
        logging.info(f'开始从权限中心同步业务信息到配置平台')
        get_mg_biz = dict(method='GET', url=f'/api/p/v4/biz/', description='获取租户数据')
        try:
            response = client.do_action(**get_mg_biz)
            all_biz_list = json.loads(response).get('data')
            biz_info_map = {}
            for biz in all_biz_list:
                biz_id = str(biz.get('biz_id'))
                biz_info_map[biz_id] = biz.get('biz_cn_name', biz.get('biz_en_name'))
                with DBContext('w', None, True) as session:
                    try:
                        session.add(insert_or_update(BizModels, f"biz_id='{biz_id}'",
                                                     biz_id=biz_id,
                                                     biz_en_name=biz.get('biz_en_name'),
                                                     biz_cn_name=biz.get('biz_cn_name'),
                                                     resource_group=biz.get('biz_cn_name'),
                                                     sort=biz.get('sort'),
                                                     life_cycle=biz.get('life_cycle'),
                                                     corporate=biz.get('corporate')))

                    except Exception as err:
                        logging.error(f'同步业务信息到配置平台出错 1 {err}')

            biz_info_map = json.dumps(biz_info_map)
            redis_conn = cache_conn()
            redis_conn.set("BIZ_INFO_STR", biz_info_map)

        except Exception as err:
            logging.error(f'同步业务信息到配置平台出错 2 {err}')
        logging.info(f'从权限中心同步业务信息到配置平台结束 {datetime.datetime.now()}')

    index()


def sync_agent_status():
    @deco(RedisLock("async_agent_status_redis_lock_key"))
    def index():
        logging.info(f'开始同步agent状态到配置平台')
        get_agent_list = dict(method='GET', url=f'/api/agent/v1/agent/info', description='获取Agent List')
        res = client.do_action_v2(**get_agent_list)
        if res.status_code != 200:
            return
        data = res.json()
        agent_list = data.keys()
        the_model = AssetServerModels
        with DBContext('w', None, True) as session:
            __info = session.query(the_model.id, the_model.agent_id, the_model.agent_status).all()
            all_info = [
                dict(id=asset_id, agent_status='2') if agent_status == '1' and agent_id not in agent_list else
                dict(id=asset_id, agent_status='1') if (
                                                               agent_status == '2' or not agent_status) and agent_id in agent_list else
                None for asset_id, agent_id, agent_status in __info
            ]

            all_info = list(filter(None, all_info))

            for info in all_info:
                logging.info(f"{info['id']} 改为{'在线' if info['agent_status'] == '1' else '离线'} ")

            # all_info = []
            # for asset_id, agent_id, agent_status, in __info:
            #     if agent_status == '1' and agent_id not in agent_list:  # 如果状态在线  但是agent找不到
            #         ins_log.read_log('info', f'{agent_id}改为离线  {asset_id}')
            #         all_info.append(dict(id=asset_id, agent_status='2'))
            #         # session.query(model).filter(model.id == asset_id).update(**dict(agent_status='2'))
            #     elif (agent_status == '2' or not agent_status) and agent_id in agent_list:  # 如果状态离线  但是agent存在
            #         all_info.append(dict(id=asset_id, agent_status='1'))
            #         ins_log.read_log('info', f'{agent_id}改为在线  { {asset_id} }')
            #         # session.query(model).filter(model.id == asset_id).update(**dict(agent_status='1'))
            session.bulk_update_mappings(the_model, all_info)
        logging.info(f'同步agent状态到配置平台 结束 {datetime.datetime.now()}')

    try:
        index()
    except Exception as err:
        logging.error(f'同步agent状态到配置平台出错 {str(err)}')


def async_agent():
    executor = ThreadPoolExecutor(max_workers=1)
    executor.submit(sync_agent_status)


def async_biz_info():
    executor = ThreadPoolExecutor(max_workers=1)
    executor.submit(biz_sync)
