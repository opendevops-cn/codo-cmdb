#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/5/15 13:57
# @Author  : Fred Yangxiaofei
# @File    : hand_app.py
# @Role    : 手动更新资产，前端点击更新，
# 备注：这里单独起一个进程，防止由于每个人习惯不同，可能引起未知的异常Bug导致主程序卡死的问题， 测试用的。 现在使用异步



from websdk.application import Application as myApplication
from biz.handlers.hand_update_asset_handler import asset_hand_server_urls

class Application(myApplication):
    def __init__(self, **settings):
        urls = []
        urls.extend(asset_hand_server_urls)
        super(Application, self).__init__(urls, **settings)

if __name__ == '__main__':
    pass
