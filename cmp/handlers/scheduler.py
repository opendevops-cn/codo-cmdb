#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Contact : 1084430062@qq.com
Author  : 娄文军
Date    : 2023/7/31 20:52
Desc    :
"""
# TODO  此类同步 无需使用 scheduler

import logging
from libs.flow import FlowAPI
from websdk2.db_context import DBContextV2 as DBContext
from models.order_model import OrderInfoModel
from settings import settings
from cmdb.handlers.cloud_handler import scheduler


class OrderStatusHandler(object):

    def __init__(self):
        pass

    def check_status(self, flow_id):
        """
        state: 0:表示进行中，1:表示任务完成，2:表示执行失败
        """
        state = "0"
        codo_api = FlowAPI()
        # 先查历史订单状态，存在则认为任务完成
        res = codo_api.get_flow_history_status(flow_id=flow_id).json()
        if res["count"] == 1:
            state = "1"
            return state
        # 查当前订单状态，可能有 进行中，执行失败的状态
        res = codo_api.get_flow_create_status(flow_id=flow_id).json()
        if res["count"] == 1 and res["data"][0]["order_state"] == "4":
            state = "2"
            return state
        return state

    def watch_flow_status(self):
        """监听任务状态"""
        with DBContext('w', None, True, **settings) as session:
            order_obj = session.query(OrderInfoModel).filter(OrderInfoModel.status == "0").all()
            for item in order_obj:
                state = self.check_status(flow_id=item.flow_id)
                if state != "0":
                    item.status = state
                    session.add(item)
            session.commit()
        return

    def run(self):
        logging.info("开始执行 同步订单状态任务")
        self.watch_flow_status()
        return


def run_sysnc_order_status():
    order_status = OrderStatusHandler()
    order_status.run()
    return


def order_tasks():
    logging.info("添加订单定时任务")
    scheduler.add_job(run_sysnc_order_status, 'interval', seconds=20, replace_existing=True)
    return
