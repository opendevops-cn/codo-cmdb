#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# @File    :   synchronize.py
# @Time    :   2024/11/11 17:27:38
# @Author  :   DongdongLiu
# @Version :   1.0
# @Desc    :   PVE同步入口

import logging
import time
from typing import *
import concurrent
from concurrent.futures import ThreadPoolExecutor

from websdk2.tools import RedisLock

from models.models_utils import sync_log_task, get_cloud_config
from libs.pve.pve_vm import PveVM
from libs.mycrypt import MyCrypt
from libs import deco

mc = MyCrypt()

# 用来标记这是vmware的作业
DEFAULT_CLOUD_NAME = 'pve'

# 同步的资产对应关系
mapping: Dict[str, dict] = {
    '服务器': {
        "type": "server",
        "obj": PveVM
    }
}


def sync(data: Dict[str, Any]):
    """
    pve统一资产入库，云厂商用for，产品用并发，地区用for
    """
    # 参数
    obj, cloud_type, account_id = data.get('obj'), data.get('type'), data.get('account_id')

    # 获取AK SK配置信息
    cloud_configs: List[Dict[str, str]] = get_cloud_config(cloud_name=DEFAULT_CLOUD_NAME, account_id=account_id)
    if not cloud_configs: return

    # vmware不用考虑多region
    for conf in cloud_configs:
        region = conf.get('region')
        logging.info(f'同步开始, 信息：「{DEFAULT_CLOUD_NAME}」-「{cloud_type}」-「{region}」.')
        # 开始时间
        the_start_time = time.time()
        # region 参数用来代替 server_addr
        is_succ, msg = obj(access_id=conf['access_id'], access_key=mc.my_decrypt(conf['access_key']),
                           account_id=conf['account_id'], server_addr=region).sync_cmdb()
        # 结束时间
        the_end_time = time.time() - the_start_time
        sync_consum = '%.2f' % the_end_time
        sync_state = 'success' if is_succ else 'failed'
        # 记录同步信息入库
        try:
            sync_log_task(
                dict(
                    name=conf['name'], cloud_name=DEFAULT_CLOUD_NAME, sync_type=cloud_type,
                    account_id=conf['account_id'], sync_region=region, sync_state=sync_state,
                    sync_consum=sync_consum, loginfo=str(msg)
                )
            )
            logging.info(f'同步结束, 信息：「{DEFAULT_CLOUD_NAME}」-「{cloud_type}」-「{region}」.')
        except Exception as err:
            logging.error(f'同步结束, 出错：「{DEFAULT_CLOUD_NAME}」-「{cloud_type}」-「{region}」 -「{err}」.')
        continue


@deco(RedisLock("async_pve_to_cmdb_redis_lock_key"))
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
        for _, v in sync_mapping.items():  v['account_id'] = account_id
    # 如果用户给了资源列表，就只要用户的
    if resources is not None:
        pop_list = list(set(sync_mapping.keys()).difference(set(resources)))
        for i in pop_list:   sync_mapping.pop(i)
    # 同步
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(sync_mapping.keys())) as executor:
        executor.map(sync, sync_mapping.values())


if __name__ == '__main__':
    pass
