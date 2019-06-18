#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/4/26 14:30
# @Author  : Fred Yangxiaofei
# @File    : auto_update_app.py
# @Role    : 资产自动更新Applicaction


import tornado
from websdk.application import Application as myApplication
from libs.server.asset_auto_update import new_tail_data, true_tail_data
from libs.server.sync_to_tagtree import main as tagtree_tail_data
from libs.aws.ec2 import main as aws_tail_data
from libs.aliyun.ecs import main as aliyun_tail_data
from libs.qcloud.cvm import main as qcloud_tail_data
from libs.huaweiyun.huawei_ecs import main as huaweicloud_tail_data


class Application(myApplication):
    def __init__(self, **settings):
        urls = []
        new_asset_callback = tornado.ioloop.PeriodicCallback(new_tail_data, 3600000)  # 新增的资产 1小时更新一次
        old_asset_callback = tornado.ioloop.PeriodicCallback(true_tail_data, 82800000)  # 已经为True的资产，23小时更新一次
        aws_asset_callback = tornado.ioloop.PeriodicCallback(aws_tail_data, 86400000)  # 更新AWS资产， 24小时更新一次
        aliyun_asset_callback = tornado.ioloop.PeriodicCallback(aliyun_tail_data, 88200000)  # 更新阿里云资产，24.5小时更新一次
        qcloud_asset_callback = tornado.ioloop.PeriodicCallback(qcloud_tail_data, 90000000)  # 更新腾讯云资产，25小时更新一次
        huaweicloud_asset_callback = tornado.ioloop.PeriodicCallback(huaweicloud_tail_data,
                                                                     93600000)  # 更新华为云资产，26小时更新一次
        tagtree_asset_callback = tornado.ioloop.PeriodicCallback(tagtree_tail_data, 21600000)  # 6小时执行一次
        new_asset_callback.start()
        old_asset_callback.start()
        aws_asset_callback.start()
        aliyun_asset_callback.start()
        qcloud_asset_callback.start()
        huaweicloud_asset_callback.start()
        tagtree_asset_callback.start()
        super(Application, self).__init__(urls, **settings)


if __name__ == '__main__':
    pass
