#!/usr/bin/env python
# -*-coding:utf-8-*-
"""
Contact : 191715030@qq.com
Author  : shenshuo
Date   :  2023/1/27 11:02
Desc   : 定时器
"""

import logging
from cmdb.handlers.cloud_handler import add_cloud_jobs, scheduler

"""
1.Redis加锁，多进程部署情况下谁申请到lock谁作为定时器
2.如果要多进程部署需要打开Redis锁，默认False不依赖Redis
"""

USE_REDIS_LOCK = False

if USE_REDIS_LOCK:
    import atexit
    import redis_lock
    import redis
    from websdk2.consts import const
    from settings import settings

    redis_conn = redis.StrictRedis(**settings['redises'][const.DEFAULT_RD_KEY])
    # redis lock
    SCHEDULER_LOCK = redis_lock.Lock(redis_conn, "cmdb-scheduler-of-the-lock")


    # 释放锁
    def release_lock():
        logging.info("[Scheduler Init] Lock released.")
        SCHEDULER_LOCK.release()


    # 初始化定时器
    def init_scheduler():
        if SCHEDULER_LOCK.acquire(blocking=False):
            add_cloud_jobs()  # 目前只有资产定时
            scheduler.start()
            logging.info("[Scheduler Init] APScheduler has been started")
            atexit.register(release_lock)
        else:
            logging.info("[Scheduler Init] Another instance is running.")
else:

    def init_scheduler():
        add_cloud_jobs()
        scheduler.start()
        logging.info("[Scheduler Init] APScheduler has been started")

if __name__ == "__main__":
    pass
