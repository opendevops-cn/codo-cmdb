#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Contact : 1084430062@qq.com
Author  : 娄文军
Date    : 2023/7/31 20:52
Desc    : 定时任务
"""


import logging
import traceback

from concurrent.futures import ThreadPoolExecutor
from settings import settings
from websdk2.tools import RedisLock
from websdk2.db_context import DBContextV2 as DBContext
from libs.flow import FlowAPI
from models.order_model import OrderInfoModel
from libs.sync_utils_set import deco


class OrderStatusHandler(object):

    def __init__(self):
        pass

    def check_status(self, flow_id):
        """
        state: 0:表示进行中，1:表示任务完成，2:表示执行失败
        """
        state = "0"
        # 先查历史订单状态，存在则认为任务完成
        res = FlowAPI.get_flow_history_status(flow_id=flow_id)
        if res["count"] == 1:
            state = "1"
            return state
        # 查当前订单状态，可能有 进行中，执行失败的状态
        res = FlowAPI.get_flow_create_status(flow_id=flow_id)
        if res["count"] == 1 and res["data"][0]["order_state"] == "4":
            state = "2"
            return state
        return state

    def watch_flow_status(self):
        """监听任务状态"""
        try:
            with DBContext('w', None, True, **settings) as session:
                order_obj = session.query(OrderInfoModel).filter(OrderInfoModel.status == "0").all()
                for item in order_obj:
                    state = self.check_status(flow_id=item.flow_id)
                    if state != "0":
                        item.status = state
                        session.add(item)
                session.commit()
        except:
            logging.error(f"===同步订单状态任务失败: {traceback.format_exc()}")
        return

    def run(self):
        logging.info("===开始执行 同步订单状态任务===")
        self.watch_flow_status()
        logging.info("===执行完成 同步订单状态任务===")
        return


@deco(RedisLock("async_order_status_redis_lock_key"), key_timeout=20, func_timeout=18)
def run_sysnc_order_status():
    order_status = OrderStatusHandler()
    order_status.run()
    return


def async_order_status():
    executor = ThreadPoolExecutor(max_workers=1)
    executor.submit(run_sysnc_order_status)

