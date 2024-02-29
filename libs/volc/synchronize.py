#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/11/22 11:02
Desc    : 火山云资产同步入口
"""

import logging
import time
from typing import *
import concurrent
from websdk2.tools import RedisLock
from concurrent.futures import ThreadPoolExecutor
from models.models_utils import sync_log_task, get_cloud_config
from libs.volc import mapping, DEFAULT_CLOUD_NAME
from libs.mycrypt import mc
from libs import deco


def sync(data: Dict[str, Any]) -> None:
    """
    火山云统一资产入库，云厂商用for，产品用并发，地区用for
    """
    obj, cloud_type, account_id = data.get('obj'), data.get('type'), data.get('account_id')

    cloud_configs: List[Dict[str, str]] = get_cloud_config(cloud_name=DEFAULT_CLOUD_NAME, account_id=account_id)
    if not cloud_configs:
        return

    for conf in cloud_configs:
        sync_regions(conf, obj, cloud_type)


def sync_regions(conf: Dict[str, str], obj: Callable, cloud_type: str) -> None:
    region_list = conf['region'].split(',')
    for region in region_list:
        sync_region(conf, region, obj, cloud_type)


def sync_region(conf: Dict[str, str], region: str, obj: Callable, cloud_type: str) -> None:
    logging.info(f'同步开始, 信息：「{DEFAULT_CLOUD_NAME}」-「{cloud_type}」-「{region}」.')

    start_time = time.time()
    is_success, msg = obj(
        access_id=conf['access_id'], access_key=mc.my_decrypt(conf['access_key']),
        account_id=conf['account_id'], region=region
    ).sync_cmdb()
    end_time = time.time()

    sync_consum = '%.2f' % (end_time - start_time)
    sync_state = 'success' if is_success else 'failed'

    sync_log_task(
        dict(
            name=conf['name'], cloud_name=DEFAULT_CLOUD_NAME, sync_type=cloud_type,
            account_id=conf['account_id'], sync_region=region, sync_state=sync_state,
            sync_consum=sync_consum, loginfo=str(msg)
        )
    )

    logging.info(f'同步结束, 信息：「{DEFAULT_CLOUD_NAME}」-「{cloud_type}」-「{region}」.')


@deco(RedisLock("async_volc_to_cmdb_redis_lock_key"))
def main(account_id: Optional[str] = None, resources: List[str] = None):
    """
    这些类型都是为了前端点击的，定时都是自动同步全账号，全类型
    account_id：账号ID，CMDB自己的ID
    resources: ['ecs','rds','...']
    """
    # copy 后处理，不然会造成原本地址里面用的数据被删le
    sync_mapping = mapping.copy()
    # 如果用户给了accountID，加入account_id ,感觉做法有点小蠢，不想给map传2个参数了 -。-
    if account_id is not None:
        for _, v in sync_mapping.items():
            v['account_id'] = account_id
    # 如果用户给了资源列表，就只要用户的
    if resources is not None:
        pop_list = list(set(sync_mapping.keys()).difference(set(resources)))
        for i in pop_list:
            sync_mapping.pop(i)
    # 同步
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(sync_mapping.keys())) as executor:
        executor.map(
            sync, sync_mapping.values()
        )


if __name__ == '__main__':
    pass
