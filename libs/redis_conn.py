#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File  : redis_conn.py
# @Author: Fred Yangxiaofei
# @Date  : 2019/8/23
# @Role  :  Redis连接信息


import redis
from settings import settings
from websdk.consts import const


def create_redis_pool():
    redis_configs = settings[const.REDIS_CONFIG_ITEM][const.DEFAULT_RD_KEY]
    pool = redis.ConnectionPool(host=redis_configs['host'], port=redis_configs['port'],
                                password=redis_configs['password'], db=redis_configs[const.RD_DB_KEY],
                                decode_responses=True)
    return pool


redis_pool = create_redis_pool()


def create_redis_connection():
    redis_con = redis.Redis(connection_pool=redis_pool)
    return redis_con


redis_conn = create_redis_connection()

if __name__ == '__main__':
    pass
