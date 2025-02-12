#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/11/22 11:02
Desc    : 谷歌云资产同步入口
"""

import logging
import time
from typing import *
import concurrent
from concurrent.futures import ThreadPoolExecutor
from models.models_utils import sync_log_task, get_cloud_config
from websdk2.tools import RedisLock
from libs import deco
from libs.gcp import mapping, DEFAULT_CLOUD_NAME
from libs.mycrypt import mc


def sync(data: Dict[str, Any]) -> None:
    """
    谷歌云统一资产入库
    """
    obj, cloud_type, account_id = data.get('obj'), data.get('type'), data.get('account_id')

    cloud_configs: List[Dict[str, str]] = get_cloud_config(cloud_name=DEFAULT_CLOUD_NAME, account_id=account_id)
    if not cloud_configs:
        return

    for conf in cloud_configs:
        sync_regions(conf, obj, cloud_type)


def sync_regions(conf: Dict[str, str], obj: Callable, cloud_type: str) -> None:
    region = ""
    logging.info(f'同步开始, 信息：「{DEFAULT_CLOUD_NAME}」-「{cloud_type}」-「{region}」.')
    start_time = time.time()
    account_file = mc.my_decrypt(conf['account_file'])
    project_id = conf['project_id']
    account_path = f"/tmp/{project_id}_account_file.json"
    with open(account_path, 'w', encoding='utf-8') as file:
        file.write(account_file)  # 写入字符串
    is_success, msg = obj(
        project_id=project_id, account_path=account_path,
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

    with open(account_path, 'w', encoding='utf-8') as file:
        pass
    logging.info(f'同步结束, 信息：「{DEFAULT_CLOUD_NAME}」-「{cloud_type}」-「{region}」.')


# @deco(RedisLock("async_gcp_to_cmdb_redis_lock_key"))
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

        @deco(RedisLock(f"async_gcp_to_cmdb_{account_id}_redis_lock_key"))
        def index():
            # 如果用户给了资源列表，就只要用户的
            if resources:
                pop_list = list(set(sync_mapping.keys()).difference(set(resources)))
                for i in pop_list:
                    sync_mapping.pop(i)
            # 同步
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(sync_mapping.keys())) as executor:
                executor.map(
                    sync, sync_mapping.values()
                )
        index()


if __name__ == '__main__':
    pass
