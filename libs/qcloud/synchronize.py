#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/1/27 11:02
Desc    : 腾讯云资产同步入口
"""

import logging
import time
from typing import *
import concurrent
from concurrent.futures import ThreadPoolExecutor
from models.models_utils import get_cloud_config, sync_log_task
from libs.qcloud import mapping, DEFAULT_CLOUD_NAME
from libs.mycrypt import MyCrypt

mc = MyCrypt()


def sync(data: Dict[str, Any]):
    """
    腾讯统一资产入库，云厂商用for，产品用并发，地区用for
    """
    # 参数
    obj, cloud_type, account_id = data.get('obj'), data.get('type'), data.get('account_id')

    # 获取AK SK配置信息
    cloud_configs: List[Dict[str, str]] = get_cloud_config(cloud_name=DEFAULT_CLOUD_NAME, account_id=account_id)
    if not cloud_configs: return

    # 考虑到多个region的情况
    for conf in cloud_configs:
        region_list = conf['region'].split(',')
        for region in region_list:
            logging.info(f'同步开始, 信息：「{DEFAULT_CLOUD_NAME}」-「{cloud_type}」-「{region}」.')
            # 开始时间
            the_start_time = time.time()
            # Ps:这里有个小坑： 编辑器识别不出来obj是那个Class,所以就算是参数传错了也不会有提示，可以自己用AliyunEventClient替换测试下
            is_succ, msg = obj(
                access_id=conf['access_id'], access_key=mc.my_decrypt(conf['access_key']),
                account_id=conf['account_id'], region=region
            ).sync_cmdb()
            # 结束时间
            the_end_time = time.time() - the_start_time
            sync_consum = '%.2f' % the_end_time
            sync_state = 'success' if is_succ else 'failed'
            # 记录同步信息入库
            sync_log_task(
                dict(
                    name=conf['name'], cloud_name=DEFAULT_CLOUD_NAME, sync_type=cloud_type,
                    account_id=conf['account_id'], sync_region=region, sync_state=sync_state,
                    sync_consum=sync_consum, loginfo=str(msg)
                )
            )
            logging.info(f'同步结束, 信息：「{DEFAULT_CLOUD_NAME}」-「{cloud_type}」-「{region}」.')
            continue


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
    main()
